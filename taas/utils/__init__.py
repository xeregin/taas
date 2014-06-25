import logging
import sys

LOG = logging.getLogger(__name__)


def retrieve(client, resource, name, **kwargs):
    director = getattr(client, '%ss' % resource)
    try:
        return director._get(
            '/{0}s/?name={1}'.format(resource, name),
            resource
        )
    except Exception:
        LOG.warning('{0} not found'.format(resource.title()))
        try:
            LOG.info('Creating...')
            return director.create(name, **kwargs)
        except Exception:
            LOG.exception('Creation failed')
            sys.exit(1)
