import logging

import src.garage.status_codes as status_codes


logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, code, cause, message, status):
        self.code = code
        self.cause = cause
        self.message = message
        self.status = status


def validate_request_body(request_body, required_params=None, optional_params=None):
    param = 'Request Body'

    if type(request_body) != dict:
        raise_invalid_param_error(param, param + ' must be JSON')

    validate_params(request_body, required_params, optional_params)


def validate_params(params, required_params=None, optional_params=None):
    if required_params:
        for param, param_type in required_params.items():
            if param not in params:
                raise_invalid_param_error(param, param + ' is required')

            if type(params[param]) != param_type:
                raise_invalid_param_error(param, param + ' must be type ' + type(param).__name__)

    if optional_params:
        for param, param_type in optional_params.items():
            if param in params and type(params[param]) != param_type:
                raise_invalid_param_error(param, param + ' must be type ' + type(param).__name__)


def raise_invalid_param_error(param, cause):
    raise APIError(code='Invalid Input: ' + param,
                   cause=cause,
                   message='Please try again with a valid ' + param,
                   status=status_codes.HTTP_BAD_REQUEST)


def list_of_strings(objects):
        logger.debug('Converting list of Objects to list of strings')
        str_objects = list(map(str, objects))
        return_list = []
        for string in str_objects:
            return_list.append(string.rstrip())
        return return_list
