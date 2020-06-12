#!/usr/bin/env python3

import logging
import os
import sys
import unittest

sys.path.append(os.path.abspath("../src/"))

from repairmanager import RepairManager, RepairManagerAgent


class TestRepairManager(unittest.TestCase):
    def test_step(self):
        pass