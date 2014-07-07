import argh

from contextlib import contextmanager

from .environment import Environment
from .frameworks import CloudCafe, NetSiege, Tempest
from .utils.report import Reporter

LOG = Reporter(__name__).setup()


def main(endpoint, username='admin', password='secrete', framework='tempest',
         test=''):
    environment = Environment(username, password, endpoint)

    with cleanup(environment):
        environment.build()

        if 'tempest' in framework:
            framework = Tempest(environment.config, framework, test)
        elif 'cloudcafe' in framework:
            framework = CloudCafe(environment.config, framework, test)
        elif 'netsiege' in framework:
            framework = NetSiege(environment.config, framework, test)

        results = framework.test_from()

        return results


@contextmanager
def cleanup(stage):
    try:
        yield
    except (Exception, KeyboardInterrupt) as exc:
        LOG.error('Run failed: {1}'.format(stage, exc))
    finally:
        stage.destroy()


if __name__ == '__main__':
    argh.dispatch_command(main)
