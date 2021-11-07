# -*- coding: utf-8 -*-
import json
from unittest import mock

import pytest
from asynctest import CoroutineMock, Mock, ANY
from freezegun import freeze_time

from ..jarpc import AsyncJarpcClient, JarpcClient, JarpcRequest, JarpcServerError, JarpcTimeout, JarpcValidationError


class TestJarpcClient:

    @pytest.mark.parametrize('is_async', [False, True])
    @freeze_time('2012-01-14')
    def test_prepare_request(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None)

        with mock.patch('uuid.uuid4') as uuid_mock:
            uuid_mock.return_value = 'example-uuid'
            request = jarpc_client._prepare_request(method='test_method', params={'a': 1})

        assert request.data == {
            'method': 'test_method',
            'params': {'a': 1},
            'id': 'example-uuid',
            'version': '1.0',
            'ts': 1326499200.0,
            'ttl': None,
            'rsvp': True,
        }

    @pytest.mark.parametrize('rsvp, ttl, default_ttl, default_rpc_ttl, default_notification_ttl, expected_ttl', [
        (True,  None, None, None, None, None),
        (False, None, None, None, None, None),
        (True,  10.0, None, None, None, 10.0),
        (False, 10.0, None, None, None, 10.0),
        (True,  None, 10.0, None, None, 10.0),
        (False, None, 10.0, None, None, 10.0),
        (True,  30.0, 10.0, None, None, 30.0),
        (False, 30.0, 10.0, None, None, 30.0),
        (True,  None, None, 10.0, 20.0, 10.0),
        (False, None, None, 10.0, 20.0, 20.0),
        (True,  None, 30.0, 10.0, 20.0, 10.0),
        (False, None, 30.0, 10.0, 20.0, 20.0),
        (True,  30.0, None, 10.0, 20.0, 30.0),
        (False, 30.0, None, 10.0, 20.0, 30.0),
        (True,  40.0, 30.0, 10.0, 20.0, 40.0),
        (False, 40.0, 30.0, 10.0, 20.0, 40.0),
    ])
    @pytest.mark.parametrize('is_async', [False, True])
    @freeze_time('2012-01-14')
    def test_prepare_request_default_ttl(self, is_async, rsvp, ttl, default_ttl, default_rpc_ttl,
                                         default_notification_ttl, expected_ttl):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None, default_ttl=default_ttl, default_rpc_ttl=default_rpc_ttl,
                              default_notification_ttl=default_notification_ttl)

        with mock.patch('uuid.uuid4') as uuid_mock:
            uuid_mock.return_value = 'example-uuid'
            request = jarpc_client._prepare_request(method='test_method', params={'a': 1}, ttl=ttl, rsvp=rsvp)

        assert request.data == {
            'method': 'test_method',
            'params': {'a': 1},
            'id': 'example-uuid',
            'version': '1.0',
            'ts': 1326499200.0,
            'ttl': expected_ttl,
            'rsvp': rsvp,
        }

    @pytest.mark.parametrize('is_async', [False, True])
    @freeze_time('2012-01-14')
    def test_prepare_request_durable(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None, default_ttl=1.0, default_rpc_ttl=2.0, default_notification_ttl=3.0)

        with mock.patch('uuid.uuid4') as uuid_mock:
            uuid_mock.return_value = 'example-uuid'
            request = jarpc_client._prepare_request(method='test_method', params={'a': 1}, ttl=4.0, durable=True)

        assert request.data == {
            'method': 'test_method',
            'params': {'a': 1},
            'id': 'example-uuid',
            'version': '1.0',
            'ts': 1326499200.0,
            'ttl': None,
            'rsvp': True,
        }

    @pytest.mark.parametrize('is_async', [False, True])
    def test_parse_response_no_rsvp(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None)
        assert jarpc_client._parse_response(response_string='', rsvp=False) is None

    @pytest.mark.parametrize('is_async', [False, True])
    def test_parse_response_ok(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None)
        result = {
            'result': 'some result',
            'request_id': '123-456-788',
            'id': '123-456-789'
        }
        assert jarpc_client._parse_response(response_string=json.dumps(result), rsvp=True) == result['result']

    @pytest.mark.parametrize('is_async', [False, True])
    def test_parse_response_error(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None)
        error = {
            'error': {
                'code': 2000,
                'message': 'Validation error',
                'data': 'some data'
            },
            'request_id': '123-456-788',
            'id': '123-456-789'
        }
        with pytest.raises(JarpcValidationError) as e:
            jarpc_client._parse_response(response_string=json.dumps(error), rsvp=True)
        assert e.value.code == error['error']['code']
        assert e.value.message == error['error']['message']
        assert e.value.data == error['error']['data']

    @pytest.mark.parametrize('is_async', [False, True])
    def test_parse_response_invalid_json(self, is_async):
        client = AsyncJarpcClient if is_async else JarpcClient
        jarpc_client = client(transport=None)

        with pytest.raises(JarpcServerError):
            jarpc_client._parse_response(response_string='', rsvp=True)

    @pytest.mark.parametrize('is_async', [False, True])
    @pytest.mark.asyncio
    @freeze_time('2012-01-14')
    async def test_call(self, is_async):
        if is_async:
            mock_class = CoroutineMock
            client = AsyncJarpcClient
        else:
            mock_class = Mock
            client = JarpcClient

        request_id = '123-456-788'
        response = {
            'result': 'some result',
            'request_id': request_id,
            'id': '123-456-789'
        }
        transport = mock_class(return_value=json.dumps(response))
        jarpc_client = client(transport=transport)

        call_kwargs = dict(method='method', params={'param1': 1}, id=request_id, extra_kwarg=1)
        call_result = jarpc_client(**call_kwargs)
        if is_async:
            call_result = await call_result
        assert call_result == response['result']

        request = JarpcRequest(method='method', params={'param1': 1}, id=request_id)
        transport.assert_called_once()
        args, kwargs = transport.call_args  # (request_string, request, **kwargs)
        assert len(args) == 2
        assert json.loads(args[0]) == request.data
        assert args[1].data == request.data
        assert kwargs == dict(extra_kwarg=1)

    @pytest.mark.parametrize('is_async', [False, True])
    @pytest.mark.asyncio
    @freeze_time('2012-01-14')
    async def test_call_simple_syntax(self, is_async):
        if is_async:
            mock_class = CoroutineMock
            client = AsyncJarpcClient
        else:
            mock_class = Mock
            client = JarpcClient

        response = {
            'result': 'some result',
            'request_id': 'no check',
            'id': '123-456-789'
        }
        transport = mock_class(return_value=json.dumps(response))
        jarpc_client = client(transport=transport)

        call_result = jarpc_client.method(param1=1)
        if is_async:
            call_result = await call_result
        assert call_result == response['result']

        request = JarpcRequest(method='method', params={'param1': 1}, id=ANY)
        transport.assert_called_once()
        args, kwargs = transport.call_args  # (request_string, request, **kwargs)
        assert len(args) == 2
        assert json.loads(args[0]) == request.data
        assert args[1].data == request.data
        assert kwargs == {}

    @pytest.mark.parametrize('is_async', [False, True])
    @pytest.mark.asyncio
    async def test_call_raise_jarpc_error(self, is_async):
        if is_async:
            mock_class = CoroutineMock
            client = AsyncJarpcClient
        else:
            mock_class = Mock
            client = JarpcClient

        transport = mock_class(side_effect=JarpcTimeout)
        jarpc_client = client(transport=transport)

        with pytest.raises(JarpcTimeout):
            call_result = jarpc_client.method()
            if is_async:
                await call_result

        transport.assert_called_once()

    @pytest.mark.parametrize('is_async', [False, True])
    @pytest.mark.asyncio
    async def test_call_raise_exception(self, is_async):
        if is_async:
            mock_class = CoroutineMock
            client = AsyncJarpcClient
        else:
            mock_class = Mock
            client = JarpcClient

        transport = mock_class(side_effect=Exception)
        jarpc_client = client(transport=transport)

        with pytest.raises(JarpcServerError):
            call_result = jarpc_client.method()
            if is_async:
                await call_result

        transport.assert_called_once()
