from .environment import Environment
from .frameworks import CloudCafe, Tempest
from .utils import cleanup, Reporter

LOG = Reporter(__name__).setup()


def main(endpoint, framework, username='admin', password='secrete', test=''):
    environment = Environment(username, password, endpoint)

    with cleanup(environment):
        environment.build()

        if 'tempest' in framework:
            framework = Tempest(environment.config, framework, test)
        else:
            framework = CloudCafe(environment.config, framework, test)

        results = framework.test_from()

        return results


if __name__ == '__main__':
    main()
