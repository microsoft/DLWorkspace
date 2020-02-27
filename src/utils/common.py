#!/usr/bin/env python3

import base64


def base64encode(str_val):
    return base64.b64encode(str_val.encode("utf-8")).decode("utf-8")


def base64decode(str_val):
    return base64.b64decode(str_val.encode("utf-8")).decode("utf-8")


def override(func):
    return func
