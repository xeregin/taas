import json
import logging
import os
import paramiko
import subprocess

from taas.utils import access
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


class NetSiege(Framework):

    def __init__(self, config, framework, test):
        super(NetSiege, self).__init__(config, framework, test)

    def create_network(self, network_name, router_external=False, shared=True):
        """
        Creates a neutron network
        """
        new_net = {"network": {"name": network_name,
                               "router:external": router_external,
                               "shared": shared}}
        net = self.neutron.create_network(new_net)
        network_id = net['network']['id']
        return network_id

    def create_subnet(self, subnet_name, network_id, subnet_cidr, pnet=False):
        """
        Creates a neutron subnet
        """
        if pnet:
            new_subnet = {"subnet": {
                "name": subnet_name, "network_id": network_id,
                "cidr": subnet_cidr, "ip_version": "4", "gateway_ip": None,
                "allocation_pools": [{'end': '192.168.4.128',
                                      'start': '192.168.4.64'}],
                "host_routes": [{'destination': '0.0.0.0/0',
                                 'nexthop': '192.168.4.54'}]}}
        else:
            new_subnet = {"subnet": {
                "name": subnet_name, "network_id": network_id,
                "cidr": subnet_cidr, "ip_version": "4"}}

        subnet = self.neutron.create_subnet(new_subnet)
        subnet_id = subnet['subnet']['id']
        return subnet_id

    def test_from(self):

        # Create run-server file
        f = open("run-server", "w")
        f.write("#!/bin/bash")
        f.write('if [[ `pgrep -fl iperf` ]]; then')
        f.write('  echo "iperf server is already running on $i";')
        f.write('  sudo killall iperf')
        f.write('  echo "iperf server is restarting";')
        f.write('else')
        f.write('  echo "iperf was not running - Starting iperf...";')
        f.write('fi')
        f.write('')
        f.write("#!/bin/bash\n\nsudo iperf -s -p 51 &\nsudo iperf -s -u -p 51 &")
        f.close()


        # Create GRE Tenant Network, Subnet, and Router
        gre_tenant_net_id = self.create_network("ENV01-GRE-NETWORK")
        gre_tenant_sub_id = self.create_subnet("ENV01-GRE-SUBNET", gre_tenant_net_id, cidr)
        router_id = self.create_router(router_name)

        # Add router interface and gateway
        iface_port = self.add_router_interface(router_id, subnet_id)
        self.neutron.add_gateway_router(router_id,
                                        body={"network_id": provider_net_id})


        # Boot VMs on GRE Tenant Network
        networks = [{"net-id": network_id}]

        i = 0
        num_vms = 10
        vms = []
        while i < num_vms:
            server = self.nova.servers.create(server_name,
                                              server_image,
                                              server_flavor,
                                              nics=networks,
                                              availability_zone=zone)
            vms.append(server)


        # Get provider network ID
        provider_net_id = ""
        for net in self.neutron.list_networks()['networks']:
            if net['name'] == "ENV01-VLAN" or net['name'] == "PROVIDER_NET":
                provider_net_id = net['id']
                break


        # Create floatingip on VLAN (provider network)
        i = 0
        num_fips = 10
        fips = []
        while i < num_fips:
            floating_ip = self.neutron.create_floatingip({"floatingip":
                                                         {"floating_network_id":
                                                          provider_net_id,
                                                          "port_id": port_id}})
            fips.append(floating_ip)


        # Associate floatingips to VMs


        # config-ssh
        #f = open("~/.ssh/config", "w")
        #for fip in fips:
        #    f.write("Host {0}".format(fip['floating_ip_address']))
        #    f.write("  IdentityFile ~/.ssh/novakey")
        #f.close()


        # Copy run-server file to VMs via floatingips


        # Install iperf on VMs


        # Execute run-server on VMs


        # Delete local copy of run-server


        # Create client-command file based on protocol


        # Copy client-command file to VMs via floatingips


        # Delete local copy of client-command






        checkout = 'git clone -b {0} {1} {2}'.format(branch, repo,
                                                     tempest_dir)
        subprocess.check_call(checkout, shell=True)


class Tempest(Framework):

    def __init__(self, config, framework, test):
        super(Tempest, self).__init__(config, framework, test)

    def test_from(self):
        repo = 'https://github.com/openstack/tempest.git'
        tempest_dir = '/opt/tempest'

        if not exists(tempest_dir):
            checkout = 'git clone {0} {1}'.format(repo, tempest_dir)
            subprocess.check_call(checkout, shell=True)

        tests_file = abspath('results.json')
        tests_dir = join(tempest_dir, 'tempest/api/%s' % self.test)

        self.populate_settings()

        flags = '--with-json --json-file={0}'.format(tests_file)
        tempest_cmd = 'nosetests --where={0} {1}'.format(tests_dir, flags)

        LOG.info('Running Tempest tests for: {0}'.format(self.test))

        try:
            subprocess.check_output(tempest_cmd, shell=True,
                                    stderr=subprocess.STDOUT)
        except Exception as exc:
            LOG.error(exc.output)

        with open(tests_file, 'r') as fp:
            return json.dumps(json.load(fp), sort_keys=True, indent=4,
                              separators=(',', ': '))
