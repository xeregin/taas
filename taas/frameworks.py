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

        conf_dir = '/opt/tempest/etc/'
        if not exists(conf_dir):
            os.makedirs(conf_dir)

        with open(join(conf_dir, 'tempest.conf'), 'w') as stream:
            stream.write(self.settings)

    def test_from(self):
        raise NotImplementedError


class CloudCafe(Framework):

    def __init__(self, config, framework, test):
        super(CloudCafe, self).__init__(config, framework, test)


class Tempest(Framework):

    def __init__(self, config, framework, test):
        super(Tempest, self).__init__(config, framework, test)

    def test_from(self):
        repo = 'https://github.com/openstack/tempest.git'
        tempest_dir = '/opt/tempest'

        if not exists(tempest_dir):
            checkout = 'git clone {0} {1}'.format(repo, tempest_dir)
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
