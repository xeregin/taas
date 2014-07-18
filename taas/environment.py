import logging
import re

from keystoneclient.v2_0.client import Client as keystone_client
from neutronclient.v2_0.client import Client as neutron_client
from novaclient.v1_1 import client as nova_client
from uuid import uuid4 as uuid

from .utils import retrieve

LOG = logging.getLogger(__name__)


class Environment(object):

    def __init__(self, username, password, auth_url):
        self.username = username
        self.password = password
        self.auth_url = auth_url

        self.config = {}
        self.users = []
        self.tenant = None
        self.network = None
        self.router = None

        self.keystone = keystone_client(
            username=username,
            password=password,
            tenant_name=username,
            auth_url=auth_url
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

    def create_tenant(self, name=None):
        LOG.info('Creating tenant')
        if not name:
            name = str(uuid())
        self.tenant = retrieve(self.keystone, 'tenant', name=name)

    def create_users(self, names=None, password='secrete'):
        LOG.info('Creating users')
        self.config['users'] = {}
        self.config['users']['guest'] = []

        if not names:
            names = [str(uuid()) for each in range(2)]
        for name in names:
            user = retrieve(self.keystone, 'user', name=name,
                            password=password)
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
            LOG.info('Provisioning user role')
            self.provision_role(user)

        self.config['users']['admin'] = {
            'user': self.username,
            'password': self.password,
            'tenant': self.username
        }

    def provision_role(self, user):
        roles = self.keystone.roles.list()
        role = next(role for role in roles if '_member_' in role.name)
        try:
            self.keystone.roles.add_user_role(user, role, tenant=self.tenant)
        except Exception as exc:
            LOG.warning('User {0} has correct role'.format(user.name, exc))

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

    def create_network(self, name=None):
        LOG.info('Creating network')
        if not name:
            name = str(uuid())

        payload = {
            "network": {
                "name": name,
                "shared": True
            }}

        self.network = self.neutron.create_network(payload)['network']
        self.config['network'] = self.network

    def create_router(self, name=None):
        LOG.info('Creating router')
        if not name:
            name = str(uuid())

        payload = {
            "router": {
                "name": name,
                "admin_state_up": True
            }}

        self.router = self.neutron.create_router(payload)['router']
        self.config['router'] = self.router

    def build(self):
        LOG.info('Building testing environment')

        self.get_catalog()
        self.get_images()

        self.create_tenant()
        self.create_users()

        self.create_network()
        self.create_router()

    def destroy(self):
        LOG.info('Destroying testing environment')

        if self.tenant:
            self.keystone.tenants.delete(self.tenant)

        [self.keystone.users.delete(user) for user in self.users if self.users]

        if self.network:
            self.neutron.delete_network(self.network['id'])

        if self.router:
            self.neutron.delete_router(self.router['id'])

        LOG.info('Done!')
