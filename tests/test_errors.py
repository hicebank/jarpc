# -*- coding: utf-8 -*-
import pytest

from ..jarpc import (JarpcUnauthorized, JarpcForbidden, JarpcExternalServiceUnavailable, JarpcValidationError,
                     JarpcUnknownError, JarpcError, raise_exception)


@pytest.mark.parametrize('code, error_class, data',
                         [
                             (1000, JarpcUnauthorized, 'test1'),
                             (1001, JarpcForbidden, 'test2'),
                             (2000, JarpcValidationError, 'test3'),
                             (3000, JarpcExternalServiceUnavailable, 'test3'),
                             (9999, JarpcUnknownError, 'test4')
                         ]
                         )
def test_raise_exception(code, error_class, data):
    with pytest.raises(error_class) as e:
        raise_exception(code=code, data=data)

    assert e.value.data == data
    assert e.value.code == code
    assert e.value.message == error_class.message


@pytest.mark.parametrize('code, error_class, message, data',
                         [
                             (9999, JarpcUnknownError, 'test1', 'testst'),
                             (9999, JarpcUnknownError, 'test2', {}),
                             (9999, JarpcUnknownError, 'test3', ()),
                             (9999, JarpcUnknownError, 'test4', None),
                         ]
                         )
def test_raise_exception_unknown_error(code, error_class, data, message):
    with pytest.raises(error_class) as e:
        raise_exception(code=code, data=data, message=message)

    assert e.value.data == data
    assert e.value.code == code
    assert e.value.message == message


def test_as_dict_method():
    exception = JarpcError('test_as_dict_method')
    exception.code = 4444
    exception.message = 'test exception'

    assert exception.as_dict() \
        == {
        'code': 4444,
        'data': 'test_as_dict_method',
        'message': 'test exception',
    }
