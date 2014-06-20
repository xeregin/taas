import logging
import re

from keystoneclient.v2_0.client import Client as keystone_client
from neutronclient.v2_0.client import Client as neutron_client
from novaclient.v1_1 import client as nova_client

LOG = logging.getLogger(__name__)


class Environment(object):

    def __init__(self, username, password, auth_url):
        self.username = username
        self.password = password
        self.auth_url = auth_url

        self.config = {}

        self.keystone = keystone_client(
            username=username,
            auth_url=auth_url,
            password=password,
            tenant_name=username
        )
        self.neutron = neutron_client(
            username=username,
            password=password,
            tenant_name=username,
            auth_url=auth_url
        )
        self.nova = nova_client.Client(
            username=username,
            api_key=password,
            project_id=username,
            auth_url=auth_url
        )

    def create_tenant(self, name, enabled=True):
        LOG.info('Creating tenant: {0}'.format(name))
        try:
            self.tenant = self.keystone.tenants.create(name, enabled)
        except Exception as exc:
            LOG.warning('Tenant already exists: {0} - {1}'.format(name, exc))

        self.tenant = self.keystone.tenants._get(
            "/tenants/?name=%s" % name,
            "tenant"
        )

    def create_users(self, users, password='secrete', enabled=True):
        LOG.info('Creating users: {0}'.format(', '.join(users)))
        self.users = []
        self.config['users'] = {}
        self.config['users']['admin'] = {
            'user': self.username,
            'password': self.password,
            'tenant': self.username
        }
        self.config['users']['guest'] = []
        for name in users:
            try:
                self.keystone.users.create(name, password, enabled)
            except Exception as exc:
                LOG.warning('User already exists: {0} - {1}'.format(name, exc))
            user = self.keystone.users._get(
                "/users/?name=%s" % name,
                "user"
            )
            self.users.append(user)
            self.config['users']['guest'].append({
                'name': name,
                'email': user.email,
                'enabled': user.enabled,
                'password': password,
                'tenant': self.tenant.name,
                'ids': {
                    'user': user.id,
                    'tenant': self.tenant.id
                }})
            self.create_role(user)

    def create_role(self, user):
        LOG.info('Creating appropriate role')
        for role in self.keystone.roles.list():
            if 'Member' in role.name:
                self.role = role
        try:
            self.keystone.roles.add_user_role(user, role, tenant=self.tenant)
        except Exception as exc:
            LOG.warning('User {0} has appropriate role: {1}'.format(user.name,
                                                                    exc))

    def get_catalog(self):
        LOG.info('Gathering service catalog')
        endpoints = self.keystone.endpoints.list()
        services = self.keystone.services.list()

        self.config['catalog'] = {}
        for endpoint in endpoints:
            for service in services:
                if endpoint.service_id in service.id:
                    self.config['catalog'][service.name] = {
                        'service_id': service.id,
                        'description': service.description,
                        'ip_address': re.search(
                            r'[0-9]+(?:\.[0-9]+){3}',
                            endpoint.adminurl
                        ).group(0),
                        'endpoints': {
                            'admin': endpoint.adminurl,
                            'internal': endpoint.internalurl,
                            'public': endpoint.publicurl
                        }}

    def get_images(self):
        LOG.info('Gathering image metadata')
        images = (image.to_dict() for image in self.nova.images.list())

        try:
            image = next(images)
        except StopIteration as exc:
            LOG.error('No images found: {0}'.format(exc))
            exit(1)

        try:
            image2 = next(images)
        except StopIteration as exc:
            LOG.warning('Only one image found: {0}'.format(exc))
            image2 = image

        self.config['images'] = [image, image2]

    def create_network(self, name):
        LOG.info('Creating network')
        networks = self.neutron.list_networks()['networks']
        for network in networks:
            if name in network['name']:
                self.network = self.neutron.show_network(
                    network['id'])['network']
                self.config['network'] = self.network
                return

        payload = {
            "network": {
                "name": name,
                "shared": True
            }}

        self.network = self.neutron.create_network(payload)['network']
        self.config['network'] = self.network

    def create_router(self, name):
        LOG.info('Creating router')
        routers = self.neutron.list_routers()['routers']
        for router in routers:
            if name in router['name']:
                self.router = self.neutron.show_router(router['id'])['router']
                self.config['router'] = self.router
                return

        payload = {
            "router": {
                "name": name,
                "admin_state_up": True
            }}

        self.router = self.neutron.create_router(payload)['router']
        self.config['router'] = self.router

    def build(self):
        LOG.info('Building testing environment')
        self.create_tenant('taas')
        self.create_users(['taas_demo', 'taas_demo2'])

        self.get_catalog()
        self.get_images()

        self.create_network('taas_network')
        self.create_router('taas_router')

    def destroy(self):
        LOG.info('Destroying testing environment')
        self.keystone.tenants.delete(self.tenant)

        for user in self.users:
            self.keystone.users.delete(user)

        self.neutron.delete_network(self.network['id'])
        self.neutron.delete_router(self.router['id'])
