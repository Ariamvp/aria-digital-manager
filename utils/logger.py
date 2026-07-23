import logging
import os

def setup_logger():
    os.makedirs('logs', exist_ok=True)
    logger = logging.getLogger("ARIA_Pipeline")
    logger.setLevel(logging.INFO)
    
    # Prevent duplicate logs if logger is re-initialized
    if not logger.handlers:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File handler
        fh = logging.FileHandler('logs/aria_pipeline.log', encoding='utf-8')
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
    return logger