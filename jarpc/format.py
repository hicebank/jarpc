# -*- coding: utf-8 -*-
import json
import time
import uuid
from typing import Optional, Any

from .errors import JarpcInvalidRequest, JarpcParseError, JarpcServerError


def json_dumps(data):
    """Default JSON serialiser."""
    return json.dumps(data, ensure_ascii=False)


def json_loads(data):
    """Default JSON deserialiser."""
    return json.loads(data)


class JarpcRequest:
    VERSION = '1.0'

    def __init__(self, method: str, params: dict, ts: Optional[float]=None, ttl: Optional[float]=None,
                 id: Optional[str]=None, rsvp: bool=True):
        self.method = method
        self.params = params
        self.ts = time.time() if ts is None else float(ts)
        self.ttl = float(ttl) if ttl is not None else None
        self.id = str(uuid.uuid4()) if id is None else id
        self.rsvp = bool(rsvp)

    def __repr__(self):
        return f'<JarpcRequest version {self.version}, method {self.method}, params {self.params}, ts {self.ts}, ' \
               f'ttl {self.ttl}, id {self.id}, rsvp {self.rsvp}>'

    @property
    def version(self):
        return self.VERSION

    @property
    def expired(self):
        if self.ttl is None:
            return False
        return time.time() > self.ts + self.ttl

    @property
    def data(self):
        return {
            'version': self.VERSION,
            'method': self.method,
            'params': self.params,
            'ts': self.ts,
            'ttl': self.ttl,
            'id': self.id,
            'rsvp': self.rsvp,
        }

    def serialize(self, dumps=json_dumps):
        return dumps(self.data)

    @classmethod
    def from_json(cls, body, loads=json_loads):
        try:
            data = loads(body)
        except (TypeError, json.JSONDecodeError) as e:
            raise JarpcParseError(e) from e

        return cls.from_data(data)

    field_types = (
        ('method', str),
        ('params', dict),
        ('ts', float),
        ('ttl', (float, type(None))),
        ('id', str),
        ('rsvp', bool),
    )

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict):
            raise JarpcInvalidRequest('Request body must be an object')

        for field in ('version', 'method', 'params', 'ts', 'ttl', 'id', 'rsvp'):
            if field not in data:
                raise JarpcInvalidRequest(f'Missing required field "{field}"')

        if data['version'] != cls.VERSION:
            raise JarpcInvalidRequest(f'Version must be {cls.VERSION}')

        for field, field_type in cls.field_types:
            if not isinstance(data[field], field_type):
                raise JarpcInvalidRequest(f'Bad "{field}" value')

        return cls(
            method=data['method'],
            params=data['params'],
            ts=data['ts'],
            ttl=data['ttl'],
            id=data['id'],
            rsvp=data['rsvp'],
        )


class JarpcResponse:
    def __init__(self, request_id: str, result: Any=None, error: Any=None, id: Optional[str]=None):
        self.result = result
        self.error = error
        self.request_id = request_id
        self.id = str(uuid.uuid4()) if id is None else id

    def __repr__(self):
        return f'<JarpcResponse id {self.id} result {self.result}, error {self.error}, request_id {self.request_id}>'

    @property
    def success(self):
        return self.error is None

    @property
    def data(self):
        if self.success:
            data = {
                'result': self.result,
                'request_id': self.request_id,
                'id': self.id
            }
        else:
            data = {
                'error': self.error,
                'request_id': self.request_id,
                'id': self.id
            }
        return data

    def serialize(self, dumps=json_dumps):
        return dumps(self.data)

    @classmethod
    def from_json(cls, body, loads=json_loads):
        try:
            data = loads(body)
        except (TypeError, json.JSONDecodeError) as e:
            raise JarpcServerError(e) from e

        return cls.from_data(data)

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, dict):
            raise JarpcServerError('Invalid response')
        if 'result' in data != 'error' in data:
            raise JarpcServerError('Invalid response')
        if 'id' not in data or not isinstance(data['id'], str):
            raise JarpcServerError('Invalid response')
        if 'request_id' not in data or not isinstance(data['request_id'], str):
            raise JarpcServerError('Invalid response')
        return cls(id=data['id'], request_id=data['request_id'], result=data.get('result'), error=data.get('error'))
