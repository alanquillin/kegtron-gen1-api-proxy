# pylint: disable=unused-import
# by importing these names, we're exposing the standard lib JSON functionality to library clients

import json
from datetime import datetime
from json import dump
from json import dumps as _dumps
from json import load, loads

import simplejson


class KegtronProxyJsonEncoder(simplejson.JSONEncoder):
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "_json_repr_"):
            return o._json_repr_()  # pylint: disable=protected-access
        return super().default(o)


def dumps(data, *_, **kwargs):
    kwargs["cls"] = KegtronProxyJsonEncoder
    return _dumps(data, **kwargs)