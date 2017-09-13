import coloredlogs, logging


LEVEL_TO_STRING = {logging.DEBUG: "DEBUG", logging.INFO: "INFO",
                   logging.WARN: "WARN", logging.ERROR: "ERROR",
                   logging.CRITICAL: "CRITICAL"}


def setup_logger(name, log_filename=None, log_level=logging.DEBUG):
    """Setup a logger with the specified name and file.
    If a log_filename is specified, the logger will also output logs to that
    file-
    """
    FORMAT = "%(asctime)s %(name)s[%(process)d] %(levelname)s %(message)s"
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    coloredlogs.install(fmt=FORMAT, datefmt="%H:%M:%S",
                        level=LEVEL_TO_STRING[log_level], logger=logger)



    if log_filename:
        handler = logging.FileHandler(log_filename)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

    # logger = setup_logger('first_logger', 'first_logfile.log')


#logger.info('This is just info message')
# second file logger
#super_logger = setup_logger('second_logger', 'second_logfile.log')
#super_logger.error('This is an error message')