# -*- coding: utf-8 -*-
import json
from datetime import datetime

import pytest
from freezegun import freeze_time

from ..jarpc import JarpcInvalidRequest, JarpcParseError, JarpcRequest, JarpcResponse, JarpcServerError


VALID_REQUEST_KWARGS = {
    'method': 'get_result',
    'params': {'a': 1, 'b': 2},
    'ts': 0.0,
    'ttl': 10.0,
    'id': '429284302',
    'rsvp': True
}
VALID_REQUEST_DATA = {**VALID_REQUEST_KWARGS, 'version': '1.0'}


class TestJarpcRequest:

    @freeze_time('1996-06-06 06:06:06')
    def test_expired(self):
        jarpc_request = JarpcRequest(**VALID_REQUEST_KWARGS)
        jarpc_request.ttl = 1
        jarpc_request.ts = datetime(1996, 6, 6, 6, 6, 6).timestamp() - 2
        assert jarpc_request.expired

    def test_expired_ttl_empty(self):
        jarpc_request = JarpcRequest(**VALID_REQUEST_KWARGS)
        jarpc_request.ttl = None
        assert not jarpc_request.expired

    def test_data(self):
        jarpc_request = JarpcRequest(**VALID_REQUEST_KWARGS)
        assert jarpc_request.data == VALID_REQUEST_DATA

    def test_serialize(self):
        jarpc_request = JarpcRequest(**VALID_REQUEST_KWARGS)
        assert json.loads(jarpc_request.serialize()) == VALID_REQUEST_DATA

    def test_from_json(self):
        jarpc_request = JarpcRequest.from_json(json.dumps(VALID_REQUEST_DATA))
        assert jarpc_request.data == VALID_REQUEST_DATA

    def test_from_json_invalid_json(self):
        with pytest.raises(JarpcParseError):
            JarpcRequest.from_json(123)

    def test_from_data(self):
        jarpc_request = JarpcRequest.from_data(VALID_REQUEST_DATA)
        assert jarpc_request.method == VALID_REQUEST_DATA['method']
        assert jarpc_request.version == VALID_REQUEST_DATA['version']
        assert jarpc_request.params == VALID_REQUEST_DATA['params']
        assert jarpc_request.ts == VALID_REQUEST_DATA['ts']
        assert jarpc_request.ttl == VALID_REQUEST_DATA['ttl']
        assert jarpc_request.id == VALID_REQUEST_DATA['id']
        assert jarpc_request.rsvp == VALID_REQUEST_DATA['rsvp']

    def test_from_data_invalid_data(self):
        with pytest.raises(JarpcInvalidRequest) as e:
            JarpcRequest.from_data(123)
        assert e.value.data == 'Request body must be an object'

    def test_from_data_missing_field(self):
        request = VALID_REQUEST_DATA.copy()
        request.pop('params')
        with pytest.raises(JarpcInvalidRequest) as e:
            JarpcRequest.from_data(request)
        assert e.value.data == 'Missing required field "params"'

    def test_from_data_invalid_version(self):
        request = VALID_REQUEST_DATA.copy()
        request.update(version='2.0')
        with pytest.raises(JarpcInvalidRequest) as e:
            JarpcRequest.from_data(request)
        assert e.value.data == 'Version must be 1.0'

    def test_from_data_invalid_param_type(self):
        request = VALID_REQUEST_DATA.copy()
        request.update(method=123)
        with pytest.raises(JarpcInvalidRequest) as e:
            JarpcRequest.from_data(request)
        assert e.value.data == 'Bad "method" value'


VALID_RESULT = {
    'result': 'some result',
    'request_id': '123-456-788',
    'id': '123-456-789'
}

VALID_ERROR = {
    'error': {
        'code': 2000,
        'message': 'Validation error',
        'data': 'some data'
    },
    'request_id': '123-456-788',
    'id': '123-456-789'
}


class TestJarpcResponse:

    @pytest.mark.parametrize('data', [VALID_RESULT, VALID_ERROR])
    def test_data(self, data):
        jarpc_response = JarpcResponse(**data)
        assert jarpc_response.data == data
        jarpc_response = JarpcResponse(**data)
        assert jarpc_response.data == data

    @pytest.mark.parametrize('data', [VALID_RESULT, VALID_ERROR])
    def test_serialize(self, data):
        jarpc_response = JarpcResponse(**data)
        assert json.loads(jarpc_response.serialize()) == data

    @pytest.mark.parametrize('data', [VALID_RESULT, VALID_ERROR])
    def test_from_json(self, data):
        jarpc_response = JarpcResponse.from_json(json.dumps(data))
        assert jarpc_response.data == data

    def test_from_json_invalid_json(self):
        with pytest.raises(JarpcServerError):
            JarpcResponse.from_json(123)

    @pytest.mark.parametrize('data', [VALID_RESULT, VALID_ERROR])
    def test_from_data(self, data):
        jarpc_response = JarpcResponse.from_data(data)
        assert jarpc_response.result == data.get('result')
        assert jarpc_response.error == data.get('error')
        assert jarpc_response.request_id == data['request_id']
        assert jarpc_response.id == data['id']

    def test_from_data_invalid_data(self):
        with pytest.raises(JarpcServerError) as e:
            JarpcResponse.from_data(123)
        assert e.value.data == 'Invalid response'

    def test_from_data_invalid_fields(self):
        request = {**VALID_RESULT, **VALID_ERROR}
        with pytest.raises(JarpcServerError) as e:
            JarpcResponse.from_data(request)
            assert e.value.data == 'Invalid response'

    def test_from_data_missing_fields(self):
        request = VALID_RESULT.copy()
        request.pop('id')
        with pytest.raises(JarpcServerError) as e:
            JarpcResponse.from_data(request)
            assert e.value.data == 'Invalid response'

    def test_from_data_invalid_param_type(self):
        request = VALID_RESULT.copy()
        request.update(request_id=123)
        with pytest.raises(JarpcServerError) as e:
            JarpcResponse.from_data(request)
        assert e.value.data == 'Invalid response'
