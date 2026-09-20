import logging

LOGGER_FORMAT="%(asctime)s - %(name)s - %(message)s"

def get_logger(name:str)->logging.Logger:
    
    loger=logging.getLogger(name)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format=LOGGER_FORMAT)
 
    return loger
