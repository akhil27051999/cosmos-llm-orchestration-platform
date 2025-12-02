import logging
import os

def setup_logger(name='student_logger', log_file=None, level=logging.DEBUG):
    if log_file is None:
        # Use absolute path based on your repo root
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        log_file = os.path.join(repo_root, 'student_api.log')
    
    # Create logger with specified name
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid multiple handlers added on repeated calls
    if not logger.hasHandlers():
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
    return logger
