from config import global_vars
import logging
from logging.config import dictConfig

class MyLogger:

    def init(self):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

    def __init__(self):
        self.logger = None
        self.init()

    def info(self,msg):
        self.init()
        print msg
        if self.logger is not None:
            self.logger.info(msg)

    def error(self,msg):
        self.init()
        print msg

        if self.logger is not None:
            self.logger.error(msg)

    def warn(self,msg):
        self.init()
        print msg

        if self.logger is not None:
            self.logger.warn(msg)

    def debug(self,msg):
        self.init()
        print msg

        if self.logger is not None:
            self.logger.debug(msg)
