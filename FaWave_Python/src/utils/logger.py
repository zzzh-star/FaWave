import logging
import sys

def setup_logger(name="FaWaveLogger", log_level=logging.INFO):
    """
    Setup a logger for the FaWave application.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid duplicate logs
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
