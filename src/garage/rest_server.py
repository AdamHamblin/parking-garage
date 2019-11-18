import configparser
import errno
import importlib
import logging.config
import os
import re
from enum import Enum
from pprint import pformat
from wsgiref import simple_server


import falcon
import yaml
from packaging.version import Version

logger = logging.getLogger(__name__)


# MicroRestServer will be instance of WSGI server serving Falcon API app
class MicroRestServer(object):
    http_verb_map = {
        'GET': 'http_get',
        'POST': 'http_post',
        'PUT': 'http_put',
        'DELETE': 'http_delete',
        'HEAD': 'http_head'
    }

    def __init__(self):
        self._route_maps = None
        self._context_root = None
        self._app_context = None

    @property
    def route_maps(self):
        return self._route_maps

    @property
    def context_root(self):
        return self._context_root

    # Setup falcon.API instance as callable WSGI app
    def setup_app(self, route_maps=None):

        logger.debug('Setting up app...')
        logger.debug('Processing environment variables...')
        # Setup environment
        self.setup_env()

        # Set context Root
        logger.debug('Setting up context root')
        self._context_root = self.set_context_root()
        logger.info('Context root is [[ {} ]]'.format(self._context_root))

        # Process route maps from yaml
        logger.debug('Processing route maps')
        self._route_maps = route_maps
        if route_maps is None:
            route_maps_path = os.path.join(self.get_current_app_home(), 'route_maps.yaml')
            with open(route_maps_path, 'r') as f:
                try:
                    route_map_config = yaml.load(f)
                except yaml.YAMLError as ye:
                    logger.error('Error reading route map: {}'.format(ye))
                    raise
                except Exception as e:
                    logger.error('Unknown error occurred trying to process route map: {}'.format(e))
                    raise

            route_maps = route_map_config['routes']

        logger.debug('Current Working Directory: [{}]'.format(os.getcwd()))
        wsgi_app = api = falcon.API()

        logger.info('Running falcon version [{}]'.format(falcon.__version__))

        # Apply resources per route map to app as long-lived class instances
        for route_map in route_maps:
            if 'resources' in route_map:
                handler_route = self.__process_route(route_map['route'])
                logger.debug('Processing resource for route [[ {} ]]'.format(handler_route))
                api.add_route(handler_route, MicroApiHandler(route_map))
            elif 'module_map' in route_map:
                module_map = None
                for http_verb in HTTPVerb:
                    if http_verb.name in route_map['module_map']:
                        module_route = self.__process_route(route_map['route'])
                        logger.debug('Processing module for route [[ {} ]]'.format(module_route))
                        module_map = MicroRestApiModuleMapper.create_map(
                            module_route,
                            http_verb,
                            route_map['module_map'][http_verb.name]['module_name'],
                            MicroRestServer.http_verb_map[http_verb.name]
                        )
                if module_map is not None:
                    module_route = self.__process_route(route_map['route'])
                    logger.debug('Processing module for route [[ {} ]]'.format(module_route))
                    api.add_route(module_route, MicroApiHandler({
                        'route': route_map['route'],
                        'resource': module_map,
                        'module_map': route_map['module_map']
                    }))

        return wsgi_app

    # starts falcon.API instance as callable WSGI app
    @staticmethod
    def start(wsgi_app=None):
        httpd = simple_server.make_server('', 8080, wsgi_app)
        logger.debug('Server started.')
        httpd.serve_forever()

    # alters route per context root as needed
    def __process_route(self, route):
        if route is None:
            return None

        if route.startswith('/'):
            return route
        else:
            return self._context_root + '/' + route

    # reads environment variables from .env and assigns to os.environ
    def setup_env(self):
        main_env = os.path.join(self.get_current_app_home(), '.env')
        if not os.path.exists(main_env):
            logger.warning('.env file not found')
            raise FileNotFoundError

        results = self.process_env_file(main_env)

        """set all the changes into os.environ """
        for k, v in results.items():
            if k not in os.environ:
                os.environ[k] = v

    # reads .env file. Uses pattern to parse lines of file to dict.
    @staticmethod
    def process_env_file(env_file):
        env = re.compile(r'''^([^=]\w+)=\s*(?:["']*)(.*?)(?:["']*)\s*$''')
        results = {}
        with open(env_file) as ins:
            for line in ins:
                line = line.strip()
                if line and line[0] != '#':  # handles comments
                    match = env.match(line)
                    if match:
                        results[match.group(1)] = match.group(2)
                    else:
                        logger.warning('This line is invalid and being ignored: {}'.format(line))
        return results

    # gets current app home value from os
    @staticmethod
    def get_current_app_home():

        dir_path = os.path.dirname(os.path.realpath(__file__))
        head, tail = os.path.split(dir_path)
        src, tail = os.path.split(head)
        project_root, tail = os.path.split(src)

        app_home = os.path.join(project_root, '.env')

        if not app_home.strip():
            app_home = os.getcwd()

        return app_home

    # sets context root of os.environ
    def set_context_root(self):
        version = self.get_version()  # type: Version
        logger.debug('Version Retrieved: {}'.format(str(version)))
        os.environ['APP_CONTEXT_VERSION'] = 'v' + version.base_version.split('.')[0]
        os.environ['APP_CONTEXT'] = expand_vars_in_string('/${APP_NAME}')
        self._app_context = os.environ['APP_CONTEXT']
        context_root_version = '/' + os.environ['APP_CONTEXT_VERSION']
        return expand_vars_in_string(os.environ['APP_CONTEXT'] + context_root_version)

    # returns fully qualified version as Version object
    def get_version(self, config_file=None):
        version = self.read_version_from_config(config_file)

        if version is None:
            version = '1.0'

        logger.debug('Version is {}'.format(version))

        build_number = os.getenv('BUILD_NUMBER')

        if build_number is None:
            build_number = '0'

        revision_number = os.getenv('REVISION_NUMBER')

        if revision_number is None:
            revision_number = '0'

        fully_qualified_version = '{}.{}.{}'.format(version, build_number, revision_number)

        logger.debug('Fully Qualified Version is: {}'.format(fully_qualified_version))

        return Version(fully_qualified_version)

    # gets app version from config file
    def read_version_from_config(self, config_file=None):
        selected_config_file = self.get_config_file(config_file)

        version_retrieved = None
        config = configparser.ConfigParser()
        config.read(selected_config_file)

        logger.debug('Config info: \n{}\n'.format(pformat(vars(config))))
        if ('metadata' in config) and ('version' in config['metadata']):
            version_retrieved = config['metadata']['version']

        return version_retrieved

    # retrieves config file
    @staticmethod
    def get_config_file(config_file=None):
        if config_file is None:
            config_file_to_process = os.path.join(os.getcwd(), 'setup.cfg')
        else:
            config_file_to_process = config_file

        if not os.path.exists(config_file_to_process):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), config_file_to_process)

        return config_file_to_process


class ReplaceVarsWith(Enum):
    do_not_replace = 0
    empty_string = 1
    env_name = 2


# expands vars (strings) using pattern to replace via enum
def expand_vars_in_string(value, replace_with=ReplaceVarsWith.do_not_replace):
    def replace_var(m):
        env_name = m.group(1)
        default_value = m.group(2)

        if default_value is not None:
            default_value = default_value[2:]

        retrieved_value = os.getenv(env_name)

        if retrieved_value is None and default_value is not None:
            retrieved_value = default_value
        elif retrieved_value is None and replace_with == ReplaceVarsWith.empty_string:
            retrieved_value = ''
        elif retrieved_value is None and replace_with == ReplaceVarsWith.env_name:
            retrieved_value = env_name
        elif retrieved_value is None:
            retrieved_value = m.group(0)

        return retrieved_value

    pattern = '\$\{(\w+)(\:\-.*?)?\}'

    return re.sub(pattern, replace_var, value)


# Base API class with all methods not implemented by default
class MicroRestApiBase(object):
    def __new__(cls, *args, **kwargs):
        if cls is MicroRestApiBase:
            raise TypeError('MicroRestApiBase class may not be instantiated')
        return object.__new__(cls)

    def http_post(self, request, response, params):
        raise NotImplementedError('POST method is not implemented')

    def http_get(self, request, response, params):
        raise NotImplementedError('GET method is not implemented')

    def http_put(self, request, response, params):
        raise NotImplementedError('PUT method is not implemented')

    def http_delete(self, request, response, params):
        raise NotImplementedError('DELETE method is not implemented')

    def http_head(self, request, response, params):
        raise NotImplementedError('HEAD method is not implemented')


class HTTPVerb(Enum):
    GET = 1
    POST = 2
    PUT = 4
    DELETE = 8
    HEAD = 16


# maps resources to service endpoints to base api
class MicroRestApiModuleMapper(MicroRestApiBase):
    module_maps = {}

    def __init__(self, http_verb, module_name, module_method_name):
        self._module_map = {}
        self.add_mappings(http_verb, module_name, module_method_name)

    @property
    def module_map(self):
        return self._module_map

    def add_mappings(self, http_verb, module_name, module_method_name):
        if http_verb in self._module_map:
            raise Exception('Verb already exists')

        __method = None
        __module = importlib.import_module(module_name)
        if hasattr(__module, module_method_name):
            __method = getattr(__module, module_method_name)
            self._module_map.update({http_verb: __method})

        return __method

    @classmethod
    def create_map(cls, route, http_verb, module_name, module_method_name):
        if route in cls.module_maps:
            mapper = cls.module_maps[route]
            if http_verb in mapper.module_maps:
                raise Exception('Verb [{}] for route [{}] is already defined'.format(http_verb, route))
            __method = mapper.add_mappings(http_verb, module_name, module_method_name)

            if __method is None:
                return None

        else:
            mapper = MicroRestApiModuleMapper(http_verb, module_name, module_method_name)

            if http_verb not in mapper.module_map:
                return None

            cls.module_maps.update({route: mapper})

        return mapper

    def http_get(self, request, response, params):
        if HTTPVerb.GET in self._module_map:
            getfunc = self._module_map[HTTPVerb.GET]
            getfunc(request, response, params)
        else:
            raise NotImplementedError('GET method is not implemented')

    def http_post(self, request, response, params):
        if HTTPVerb.POST in self._module_map:
            getfunc = self._module_map[HTTPVerb.POST]
            getfunc(request, response, params)
        else:
            raise NotImplementedError('POST method is not implemented')

    def http_put(self, request, response, params):
        if HTTPVerb.PUT in self._module_map:
            getfunc = self._module_map[HTTPVerb.PUT]
            getfunc(request, response, params)
        else:
            raise NotImplementedError('PUT method is not implemented')

    def http_delete(self, request, response, params):
        if HTTPVerb.DELETE in self._module_map:
            getfunc = self._module_map[HTTPVerb.DELETE]
            getfunc(request, response, params)
        else:
            raise NotImplementedError('DELETE method is not implemented')

    def http_head(self, request, response, params):
        if HTTPVerb.HEAD in self._module_map:
            getfunc = self._module_map[HTTPVerb.HEAD]
            getfunc(request, response, params)
        else:
            raise NotImplementedError('HEAD method is not implemented')


# handles delivery of mapped resources to base api
class MicroApiHandler(object):
    def __init__(self, route_map):
        if not isinstance(route_map['resource'], MicroRestApiBase):
            raise Exception('The Resource Registered does not adhere to the MicroRestApi interface')

        self._route_map = route_map

    @property
    def route_map(self):
        return self._route_map

    @route_map.setter
    def route_map(self, value):
        self._route_map = value

    @route_map.deleter
    def route_map(self):
        del self._route_map

    def on_get(self, req, resp, **kwargs):
        self._route_map['resource'].http_get(req, resp, kwargs)

    def on_post(self, req, resp, **kwargs):
        self._route_map['resource'].http_post(req, resp, kwargs)

    def on_put(self, req, resp, **kwargs):
        self._route_map['resource'].http_put(req, resp, kwargs)

    def on_delete(self, req, resp, **kwargs):
        self._route_map['resource'].http_delete(req, resp, kwargs)

    def on_head(self, req, resp, **kwargs):
        self._route_map['resource'].http_head(req, resp, kwargs)
