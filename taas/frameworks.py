import json
import logging
import os
import subprocess

from jinja2 import Template
from os.path import abspath, dirname, exists, join

LOG = logging.getLogger(__name__)


class Framework(object):

    def __init__(self, config, framework, test):
        self.config = config
        self.fwrk = framework
        self.test = test

    def populate_settings(self):
        LOG.info('Building configuration file')

        template_dir = join(abspath(dirname(__file__)), 'files/')
        example = '{0}.conf.example'.format(self.fwrk)

        with open(join(template_dir, example), 'r') as stream:
            template = Template(stream.read())

        self.settings = template.render(catalog=self.config['catalog'],
                                        images=self.config['images'],
                                        network=self.config['network'],
                                        router=self.config['router'],
                                        users=self.config['users'])

        with open('/opt/tempest/etc/tempest.conf', 'w') as stream:
            stream.write(self.settings)

    def test_from(self):
        raise NotImplementedError


class CloudCafe(Framework):

    def __init__(self, config, framework, test):
        super(CloudCafe, self).__init__(config, framework, test)


class NetSiege(Framework):

    def __init__(self, config, framework, test):
        super(NetSiege, self).__init__(config, framework, test)

    def test_from(self):

        # Create run-server file
        f = open("run-server", "w")
        f.write("#!/bin/bash\n\nsudo iperf -s -p 51 &\nsudo iperf -s -u -p 51 &")
        f.close()

        # Boot VMs on GRE

        # Get provider network ID

        # Create floatingip on VLAN
        floating_ip = self.neutron.create_floatingip({"floatingip":
                                                     {"floating_network_id":
                                                      provider_net_id,
                                                      "port_id": port_id}})

        self.nova.boot
        checkout = 'git clone -b {0} {1} {2}'.format(branch, repo,
                                                     tempest_dir)
        subprocess.check_call(checkout, shell=True)


class Tempest(Framework):

    def __init__(self, config, framework, test):
        super(Tempest, self).__init__(config, framework, test)

    def test_from(self):
        LOG.info('Running Tempest tests for: {0}'.format(self.test))

        self.populate_settings()

        repo = 'https://github.com/openstack/tempest.git'
        branch = 'stable/havana'
        tempest_dir = '/opt/tempest'

        if not exists(tempest_dir):
            os.mkdir(tempest_dir)

        try:
            os.rmdir(tempest_dir)
        except OSError as exc:
            if exc.errno == os.errno.ENOTEMPTY:
                LOG.warning('Directory not empty: {0}'.format(tempest_dir))
        else:
            checkout = 'git clone -b {0} {1} {2}'.format(branch, repo,
                                                         tempest_dir)
            subprocess.check_call(checkout, shell=True)

        json_file = 'taas_results.json'
        json_flag = '--with-json --json-file={0}'.format(json_file)

        tempest_cmd = (
            'python -u `which nosetests` --where='
            '{0}/tempest/api/{1} {2}'.format(tempest_dir, self.test,
                                             json_flag)
        )

        LOG.debug('Tempest command: {0}'.format(tempest_cmd))

        try:
            subprocess.check_output(
                tempest_cmd,
                shell=True,
                stderr=subprocess.STDOUT
            )
        except Exception as exc:
            LOG.error(exc.output)

        with open(json_file, 'r') as fp:
            return json.dumps(json.load(fp), sort_keys=True, indent=4,
                              separators=(',', ': '))
