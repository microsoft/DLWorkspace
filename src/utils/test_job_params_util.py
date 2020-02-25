#!/usr/bin/env python3

from unittest import TestCase
from job_params_util import JobParams


class TestJobParams(TestCase):
    def test(self):
        pass


class TestRegularJobParams(TestJobParams):
    pass


class TestPSDistJobParams(TestJobParams):
    pass


class TestInferenceJobParams(TestJobParams):
    pass