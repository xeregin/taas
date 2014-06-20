import argh

from contextlib import contextmanager

from .environment import Environment
from .frameworks import CloudCafe, Tempest
from .utils.report import Reporter

LOG = Reporter(__name__).setup()


def main(endpoint, username='admin', password='secrete', framework='tempest',
         test=''):

    environment = Environment(username, password, endpoint)
    environment.build()

    if 'tempest' in framework:
        framework = Tempest(environment.config, framework, test)
    else:
        framework = CloudCafe(environment.config, framework, test)

    with cleanup(environment):
        framework.test_from()


@contextmanager
def cleanup(environment):
    try:
        yield
    except (Exception, KeyboardInterrupt) as exc:
        LOG.error('Destroying environment: {0}'.format(exc))
    finally:
        environment.destroy()


if __name__ == '__main__':
    argh.dispatch_command(main)