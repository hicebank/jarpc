# -*- coding: utf-8 -*-
"""
JARPC exception classes.

Modelled after JSON-RPC 2.0 errors.

"""
import inspect

import sys


class JarpcError(Exception):
    """Base JARPC exception"""
    code = None
    message = None

    def __init__(self, data=None):
        if isinstance(data, Exception):
            self.data = f'{data.__class__.__name__}: {data}'
        else:
            self.data = data

    def __str__(self):
        return f'{self.code} {self.message}: {self.data}'

    def as_dict(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data
        }


class JarpcParseError(JarpcError):
    """Parse Error: invalid JSON format. """
    code = -32700
    message = 'Parse error'


class JarpcInvalidRequest(JarpcError):
    """Invalid Request: the JSON object is not a JARPC 1.0 request."""
    code = -32600
    message = 'Invalid Request'


class JarpcMethodNotFound(JarpcError):
    """Method not found: method with requested name does not exist. """
    code = -32601
    message = 'Method not found'


class JarpcInvalidParams(JarpcError):
    """ Invalid params: invalid method call. """
    code = -32602
    message = 'Invalid params'


class JarpcInternalError(JarpcError):
    """ Internal error: internal JARPC error. """
    code = -32603
    message = 'Internal error'


class JarpcTimeout(JarpcError):
    """ Timeout: request could not be completed in time. """
    code = -32604
    message = 'Timeout'


class JarpcServerError(JarpcError):
    """ Server error: server could not complete the request. """
    code = -32000
    message = 'Server error'


class JarpcUnknownError(JarpcError):
    """ Unknown error: unknown exception code """

    def __init__(self, code, message, data):
        self.code = code
        self.message = message
        super().__init__(data=data)


# Should be thrown in dispatch methods.

# 1xxx - ошибки доступа

class JarpcUnauthorized(JarpcError):
    """ Unauthorized: Similar to JarpcForbidden, but specifically for use when authentication is required and
    has failed or has not yet been provided. """

    code = 1000
    message = 'Unauthorized'


class JarpcForbidden(JarpcError):
    """ Forbidden: The request was valid, but the server is refusing action.
    The user might not have the necessary permissions for a resource, or may need an account of some sort. """

    code = 1001
    message = 'Forbidden'


# 2xxx - неправильные входные данные

class JarpcValidationError(JarpcError):
    """ ValidationError: error validating input parameters"""
    code = 2000
    message = 'Validation error'


# 3xxx - ошибки интеграций

class JarpcExternalServiceUnavailable(JarpcError):
    """ ExternalServiceUnavailable: ошибка запроса удаленной системы """

    code = 3000
    message = 'External service unavailable'


def _get_exceptions():
    return [exception for _, exception in inspect.getmembers(sys.modules[__name__], inspect.isclass)
            if issubclass(exception, JarpcError) and exception not in {JarpcError, JarpcUnknownError}]


_exception_codes = {exception.code: exception for exception in _get_exceptions()}


def raise_exception(code, data=None, message=None):
    """Recreate JARPC exception from JARPC error code. """
    try:
        exception = _exception_codes[code](data=data)
    except KeyError:
        exception = JarpcUnknownError(code=code, message=message, data=data)

    raise exception
