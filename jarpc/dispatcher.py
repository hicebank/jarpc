# -*- coding: utf-8 -*-
from .errors import JarpcMethodNotFound


class JarpcDispatcher:
    """Mapping for API methods. Effectively a dictionary wrapper."""

    def __init__(self, method_map: dict = None):
        if not isinstance(method_map, (dict, type(None))):
            raise TypeError
        self.method_map = method_map or dict()

    def __getitem__(self, item):
        try:
            return self.method_map[item]
        except KeyError as e:
            raise JarpcMethodNotFound(e) from e

    def rpc_method(self, f):
        """Decorator: adds `f` as RPC method.
        `f` can retrieve JarpcRequest object through optional `jarpc_request` argument.
        """
        self.method_map[f.__name__] = f
        return f

    def add_rpc_method(self, f, name=None):
        """Adds `f` as RPC method.
        If `name` is not None, it is used as method name.
        `f` can retrieve JarpcRequest object through optional `jarpc_request` argument.
        """
        self.method_map[name or f.__name__] = f

    def update(self, dispatcher):
        """Add methods from `dispatcher`, overriding on any collisions. """
        self.method_map.update(dispatcher.method_map)
