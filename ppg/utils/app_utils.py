import os
import logging
from logging.handlers import TimedRotatingFileHandler
from enum import Enum
from flask import jsonify
from datetime import datetime

class LogLevel(int, Enum):
    CRITICAL = 50
    FATAL = CRITICAL
    ERROR = 40
    WARNING = 30
    WARN = WARNING
    INFO = 20
    DEBUG = 10
    NOTSET = 0

class AppUtils:
    LOG_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), "which_log")
    print("Log path:",LOG_DIR)

    @staticmethod
    def responseWithData(response_status, status_code, message, response_data):
        data = {
            "status": response_status,
            "status_code": status_code,
            "message": message,
            "data": response_data
        }
        return jsonify(data), 200

    @staticmethod
    def responseWithoutData(response_status, status_code, message):
        data = {
            "status": response_status,
            "status_code": status_code,
            "message": message
        }
        return jsonify(data), 200

    @staticmethod
    def setup_logger(name: str, file_name: str, level: int = logging.ERROR) -> logging.Logger:
        if not os.path.exists(AppUtils.LOG_DIR):
            os.makedirs(AppUtils.LOG_DIR)

        log_file_path = os.path.join(AppUtils.LOG_DIR, file_name)

        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Avoid adding multiple handlers if already exists
        if not logger.handlers:
            format_str = "[%(levelname)s %(name)s %(module)s:%(lineno)d - %(funcName)s() - %(asctime)s]\n\t %(message)s \n"
            time_format = "%d.%m.%Y %I:%M:%S %p"

            handler = TimedRotatingFileHandler(
                log_file_path,
                when="midnight",
                interval=1,
                backupCount=7,
                encoding="utf-8",
                delay=False
            )
            handler.setFormatter(logging.Formatter(format_str, datefmt=time_format))
            handler.suffix = "%Y-%m-%d"  # log filename format

            logger.addHandler(handler)

        return logger

    @staticmethod
    def logger(name: str, level: int, message: str):
        file_name = "serverlog.log"
        logger = AppUtils.setup_logger(name, file_name, level=level)
        logger.log(level=level, msg=message)

    @staticmethod
    def getLogLevel() -> LogLevel:
        return LogLevel
