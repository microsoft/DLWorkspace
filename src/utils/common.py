#!/usr/bin/env python3

import base64


def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")


def override(func):
    return func


def walk_json(obj, *fields, default=None):
    """ for example a=[{"a": {"b": 2}}]
    walk_json(a, 0, "a", "b") will get 2
    walk_json(a, 0, "not_exist") will get None
    """
    try:
        for f in fields:
            obj = obj[f]
        return obj
    except:
        return default
