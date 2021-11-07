# -*- coding: utf-8 -*-
import time
import uuid
from typing import Optional, Callable, Any, Union

from .format import json_loads, json_dumps, JarpcRequest, JarpcResponse
from .errors import raise_exception, JarpcError, JarpcServerError


class JarpcClient:
    """
    JARPC Client implementation.

    To make RPC it requires transport.
    Transport gets JARPC request as string, JarpcRequest-object and kwargs given with client call.
    If rsvp is True, transport must return JARPC response string, otherwise transport may not return any result.
    Transport's exceptions will be overwritten with `JarpcServerError` unless they are `JarpcError` subclasses.

    Example of usage with python "requests" library:
    ```
    def requests_transport(request_string, request, timeout=60.0):
        try:
            return requests.post(url='https://kitchen.org/jsonrpc', data=request_string, timeout=timeout)
        except Timeout:
            raise JarpcTimeout

    kitchen = JarpcClient(transport=requests_transport)
    salad = kitchen(method='cook_salad', params=dict(name='Caesar'), id='1', timeout=15)
    ```

    You can also define transport as class:
    ```
    class RequestsTransport:
        def __init__(self, url, headers=None):
            self.url = url
            self.headers = headers or {}
        def __call__(self, request_string, request, timeout=60.0):
            try:
                return requests.post(url=self.url, headers=self.headers, data=request_string, timeout=timeout)
            except Timeout:
                raise JarpcTimeout

    transport = RequestsTransport(url='https://kitchen.org/jsonrpc', headers={'Content-Type': 'application/json'})
    kitchen = JarpcClient(transport)
    salad = kitchen(method='cook_salad', params=dict(name='Caesar'), id='1', timeout=15)
    ```

    If you don't need to pass JARPC meta params and transport kwargs, you can use method-like calling syntax:
    ```
    salad = kitchen.cook_salad(name='Caesar')
    ```
    """

    def __init__(self,
                 # transport: Callable[[str, JarpcRequest, **kwargs], Union[str, None]]
                 transport: Callable[[str, JarpcRequest, Optional[Any]], Union[str, None]],
                 default_ttl: Optional[float] = None,
                 default_rpc_ttl: Optional[float] = None,
                 default_notification_ttl: Optional[float] = None,
                 loads: Callable[[str], Any] = json_loads,
                 dumps: Callable[[Any], str] = json_dumps):
        """
        :param transport: callable to send request
        :param default_ttl: float time interval while calling still actual
        :param default_rpc_ttl: default_ttl for rsvp=True calls (if None default_ttl will be used)
        :param default_notification_ttl: default_ttl for rsvp=False calls (if None default_ttl will be used)
        :param loads: json loads
        :param dumps: json dumps
        """
        self._transport = transport
        self._default_rpc_ttl = default_rpc_ttl or default_ttl
        self._default_notification_ttl = default_notification_ttl or default_ttl
        self._loads = loads
        self._dumps = dumps

    def __getattr__(self, method):
        def simple_call(**params):
            return self(method=method, params=params)
        return simple_call

    def __call__(self, method: str, params: dict, ts: Optional[float] = None, ttl: Optional[float] = None,
                 id: Optional[str] = None, rsvp: bool = True, durable: bool = False, **transport_kwargs) -> str:

        request = self._prepare_request(method, params, ts, ttl, id, rsvp, durable)
        request_string = request.serialize(dumps=self._dumps)

        try:
            response_string = self._transport(request_string, request, **transport_kwargs)
        except JarpcError:
            raise
        except Exception as e:
            raise JarpcServerError(e)

        return self._parse_response(response_string, rsvp)

    def _prepare_request(self, method: str, params: dict, ts: Optional[float] = None, ttl: Optional[float] = None,
                         id: Optional[str] = None, rsvp: bool = True, durable: bool = False) -> JarpcRequest:
        """Make request."""
        if durable:
            ttl = None
        else:
            default_ttl = self._default_rpc_ttl if rsvp else self._default_notification_ttl
            ttl = default_ttl if ttl is None else ttl

        return JarpcRequest(
            method=method,
            params=params,
            ts=time.time() if ts is None else ts,
            ttl=ttl,
            id=str(uuid.uuid4()) if id is None else id,
            rsvp=rsvp
        )

    def _parse_response(self, response_string: str, rsvp: bool):
        """Parse response and either return result or raise JARPC error."""
        if rsvp:
            response = JarpcResponse.from_json(response_string, loads=self._loads)
            if response.success:
                return response.result
            else:
                error = response.error
                raise_exception(code=error.get('code'), data=error.get('data'), message=error.get('message'))


class AsyncJarpcClient(JarpcClient):
    """
    Asynchronous JARPC Client implementation.

    To make RPC it requires async transport.
    Transport gets JARPC request as string, JarpcRequest-object and kwargs given with client call.
    If rsvp is True, transport must return JARPC response string, otherwise transport may not return any result.
    Transport's exceptions will be overwritten with `JarpcServerError` unless they are `JarpcError` subclasses.

    Example of usage with python "aiohttp" library:
    ```
    async def aiohttp_transport(request_string, request, timeout=60.0):
        try:
            async with aiohttp.ClientSession() as session:
                response = await session.post(url='https://kitchen.org/jsonrpc', data=request_string, timeout=timeout)
                return await response.text()
        except TimeoutError:
            raise JarpcTimeout

    kitchen = AsyncJarpcClient(transport=aiohttp_transport)
    salad = await kitchen(method='cook_salad', params=dict(name='Caesar'), id='1', timeout=15)
    ```

    You can also define transport as class:
    ```
    class AiohttpTransport:
        def __init__(self, session, url, headers=None):
            self.session = session
            self.url = url
            self.headers = headers or {}
        async def __call__(self, request_string, request, timeout=60.0):
            try:
                response = await session.post(url=self.url, headers=self.headers, data=request_string, timeout=timeout)
                return await response.text()
            except TimeoutError:
                raise JarpcTimeout

    async with aiohttp.ClientSession() as session:
        transport = AiohttpTransport(session=session, url='https://kitchen.org/jsonrpc',
                                     headers={'Content-Type': 'application/json'})
        kitchen = AsyncJarpcClient(transport=transport)
        salad = await kitchen(method='cook_salad', params=dict(name='Caesar'), id='1', timeout=15)
    ```

    If you don't need to pass JARPC meta params and transport kwargs, you can use method-like calling syntax:
    ```
    salad = await kitchen.cook_salad(name='Caesar')
    ```
    """
    async def __call__(self, method: str, params: dict, ts: Optional[float] = None, ttl: Optional[float] = None,
                       id: Optional[str] = None, rsvp: bool = True, durable: bool = False, **transport_kwargs) -> str:

        request = self._prepare_request(method, params, ts, ttl, id, rsvp, durable)
        request_string = request.serialize(dumps=self._dumps)

        try:
            response_string = await self._transport(request_string, request, **transport_kwargs)
        except JarpcError:
            raise
        except Exception as e:
            raise JarpcServerError(e)

        return self._parse_response(response_string, rsvp)
