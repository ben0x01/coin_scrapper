from src.helper import Helper
from src.logger import Logger


class Exchange:
    def __init__(self, name=None, api_key=None, secret_key=None, api_url=None, logger_name=None):
        self.name = name
        self.log = Logger(name=logger_name, log_file="main.log").get_logger()
        if api_key and secret_key and api_url:
            self.helper = Helper(api_key, secret_key, api_url)
        else:
            self.helper = None

    async def check_deposit_status(self, base_token_contract):
        raise NotImplementedError("This method must be overridden in a subclass")