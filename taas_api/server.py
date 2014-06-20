from paste.httpserver import serve
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config

import sys
import os.path

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import taas.runner
# import xml.etree as xml
import json


def get_not_defined(request):
    return Response("GET is not defined at this time.")


def test_tempest(request):
    request_dict = json.loads(request.body)
    results = taas.runner.main(framework="tempest", **request_dict)
    return Response(results)


def test_cloudcafe(request):
    request_dict = json.loads(request.body)
    results = taas.runner.main(framework="cloudcafe", **request_dict)
    return Response(results)


if __name__ == '__main__':
    config = Configurator()

    config.add_route('tempest', '/test/tempest')
    config.add_route('cloudcafe', '/test/cloudcafe')

    config.add_view(test_tempest,
                    route_name='tempest', request_method='POST')

    config.add_view(get_not_defined,
                    route_name='tempest', request_method='GET')

    config.add_view(test_cloudcafe,
                    route_name='cloudcafe', request_method='POST')

    config.add_view(get_not_defined,
                    route_name='cloudcafe', request_method='GET')

    app = config.make_wsgi_app()
    serve(app, host='0.0.0.0')
