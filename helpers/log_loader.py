import logging
import datetime
from colorama import Fore
import sys
import traceback



logger_name = "speedrr"
default_stdout_log_level = logging.INFO
default_file_log_level = logging.WARNING
file_log_name = 'logs/{:%Y-%m-%d %H.%M.%S}.log'.format(datetime.datetime.now())
log_format = '[%(asctime)s] [%(levelname)s] %(message)s (%(filename)s:%(lineno)d)'


class ColourFormatter(logging.Formatter):
    FORMATS = {
        logging.DEBUG:      Fore.LIGHTBLACK_EX + log_format + Fore.RESET,
        logging.INFO:       log_format + Fore.RESET,
        logging.WARNING:    Fore.YELLOW + log_format + Fore.RESET,
        logging.ERROR:      Fore.LIGHTRED_EX + log_format + Fore.RESET,
        logging.CRITICAL:   Fore.RED + log_format + Fore.RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


logger = logging.getLogger(logger_name)
logger.setLevel(logging.DEBUG)

stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(default_stdout_log_level)
stdout_handler.setFormatter(ColourFormatter())
logger.addHandler(stdout_handler)

file_handler = logging.FileHandler(file_log_name, encoding="utf-8")
file_handler.setLevel(default_file_log_level)
file_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(file_handler)

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.error("Uncaught exception: " + ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

sys.excepthook = handle_exception
