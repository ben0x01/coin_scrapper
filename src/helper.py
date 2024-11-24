import hmac
import aiohttp

from hashlib import sha256
from typing import Optional, Dict, List

from src.logger import Logger


class Helper:
    def __init__(self, api_key: str, secret_key: str, api_url: str) -> None:
        self.api_key = api_key
        self.secret_key = secret_key
        self.api_url = api_url
        self.log = Logger(name="Helper", log_file="main.log").get_logger()

    def get_sign(self, payload: str) -> str:
        return hmac.new(
            self.secret_key.encode("utf-8"),
            payload.encode("utf-8"),
            digestmod=sha256
        ).hexdigest()

    @staticmethod
    def parse_param(params_map: Dict[str, str]) -> str:
        sorted_keys = sorted(params_map)
        return "&".join([f"{key}={params_map[key]}" for key in sorted_keys])

    async def send_request(
        self,
        method: str,
        path: str,
        url_params: str,
        payload: Optional[Dict] = None
    ) -> Optional[Dict]:
        signature = self.get_sign(url_params)
        url = f"{self.api_url}{path}?{url_params}&signature={signature}"
        headers = {'X-BX-APIKEY': self.api_key}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        self.log.error(f"Error: HTTP {response.status} - {error_text}")
                        return None
            except aiohttp.ClientError as e:
                self.log.error(f"Error sending request: {e}")
                return None

    def get_ticker_by_contract(self, base_token_contract: str, file_path: str = 'gate_contracts.txt') -> Optional[str]:
        base_token_contract_lower = base_token_contract.lower()

        try:
            with open(file_path, 'r') as file:
                for line in file:
                    parts = line.strip().split(' / ')
                    if len(parts) == 2:
                        contract, ticker = parts
                        if contract.lower() == base_token_contract_lower:
                            return ticker
        except FileNotFoundError:
            self.log.error(f"File not found: {file_path}")
            return None
        return None

    @staticmethod
    def is_within_20_percent(change_1: float, change_2: float) -> bool:
        return abs(change_1 - change_2) / max(abs(change_1), abs(change_2)) <= 0.2

    @staticmethod
    def read_token_addresses(file_path: str) -> List[str]:
        try:
            with open(file_path, 'r') as file:
                return [line.strip() for line in file]
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")

    async def coinmarketcap(self, base_token_contract):
        try:
            url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/info"
            headers = {
                "Accepts": "application/json",
                "X-CMC_PRO_API_KEY": "f7f556e6-e244-4195-bb67-d7eeeee0b6ae"
            }
            params = {
                "address": base_token_contract
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from CoinMarketCap. Status code: {response.status}")
                        return None

                    otvet = await response.json()
                    token_id = list(otvet['data'].keys())[0]
                    print(f'Token ID: {token_id}')

            url_get_slug = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/info'
            parameters_get_slug = {
                'id': token_id,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url_get_slug, headers=headers, params=parameters_get_slug) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve slug from CoinMarketCap. Status code: {response.status}")
                        return None

                    dannye = await response.json()
                    token_slug = dannye['data'][str(token_id)]['slug']
                    print(f'Token slug: {token_slug}')
                    return token_slug
        except Exception as e:
            self.log.error(f'Error in coinmarketcap: {e}')
            return None
