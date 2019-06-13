from config import global_vars
import logging
from logging.config import dictConfig
import thread


class MyLogger:

    def init(self):
        if self.logger is None and "logger" in global_vars and global_vars["logger"] is not None:
            self.logger = global_vars["logger"]

    def __init__(self):
        self.logger = None
        self.init()

    def info(self, msg):
        self.init()
        txt = str(thread.get_ident()) + " : "  + msg 
        #print txt
        if self.logger is not None:
            self.logger.info(txt)

    def error(self, msg):
        self.init()
        txt = str(thread.get_ident()) + " : "  + msg 
        #print msg

        if self.logger is not None:
            self.logger.error(txt)

    def warn(self, msg):
        self.init()
        txt = str(thread.get_ident()) + " : "  + msg 
        #print msg

        if self.logger is not None:
            self.logger.warn(txt)

    def debug(self, msg):
        self.init()
        print msg

        if self.logger is not None:
            self.logger.debug(msg)

    def exception(self, msg):
        self.init()
        print msg

        if self.logger is not None:
            self.logger.exception(msg)
