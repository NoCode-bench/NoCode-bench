import logging
import logging.handlers

def get_logger(log_name="mylogger", log_file="error.log", log_level=logging.INFO):
    logger = logging.getLogger(log_name)
    logger.setLevel(log_level)

    info_handler = logging.StreamHandler()
    info_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

    error_handler = logging.FileHandler(log_file)
    error_handler.setLevel(log_level)
    error_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(filename)s[:%(lineno)d] - %(message)s"))

    # logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger