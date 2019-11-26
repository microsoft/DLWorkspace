# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from logging import getLogger, FileHandler, StreamHandler
from os import environ
from sys import stdout

# Read environment variables
log_level = environ.get('LOG_LEVEL', 'INFO')
log_file = environ.get('LOG_FILE')

# Configure logger
logger = getLogger()
logger.setLevel(log_level)
logger.addHandler(StreamHandler(stdout))
if log_file is not None:
    logger.addHandler(FileHandler(log_file))
