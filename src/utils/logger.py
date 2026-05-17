import logging
import os
from datetime import datetime

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"sim_{timestamp}.log")
    
    logger = logging.getLogger("SFCSimulation")
    logger.setLevel(logging.DEBUG)
    
    # File Handler
    fh = logging.FileHandler(log_file)
    fh.setLevel(logging.DEBUG)
    
    # Console Handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter('%(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Avoid attaching multiple handlers if logger is initialized repeatedly
    if not logger.handlers:
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger

def log_event(logger, sim_time, message):
    """Format: Time X: message"""
    logger.info(f"Time {sim_time:.2f}: {message}")
