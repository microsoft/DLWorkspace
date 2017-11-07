from config import global_vars
import logging
from logging.config import dictConfig

class MyLogger:
    def __init__(self):
        if "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]
        else:
            self.logger = None
    def info(self,msg):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

        if self.logger is not None:
            self.logger.info(msg)

    def info(self,msg):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

        if self.logger is not None:
            self.logger.info(msg)

    def error(self,msg):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

        if self.logger is not None:
            self.logger.error(msg)

    def warn(self,msg):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

        if self.logger is not None:
            self.logger.warn(msg)

    def debug(self,msg):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

        if self.logger is not None:
            self.logger.debug(msg)