import aiohttp

from exchange_base import Exchange


class MEXCExchange(Exchange):
    def __init__(self, api_key, secret_key, api_url="https://api.mexc.com"):
        super().__init__("MEXC", api_key, secret_key, api_url)

    async def _get_server_time(self):
        url = f'{self.helper.api_url}/api/v3/time'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('serverTime')
                else:
                    print(f"Error fetching server time: {response.status} - {await response.text()}")
                    return None

    async def check_deposit_status(self, base_token_contract):
        try:
            server_time = await self._get_server_time()
            if server_time is None:
                return None

            query_string = f'recvWindow=5000&timestamp={server_time}'
            signature = self.helper.get_sign(query_string)
            url = f'{self.helper.api_url}/api/v3/capital/config/getall?{query_string}&signature={signature}'
            headers = {'X-MEXC-APIKEY': self.helper.api_key}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()

                        contract_dict = {
                            network_info.get('contract').lower(): {
                                "coin": coin_data.get('coin'),
                                "deposit_enabled": network_info.get('depositEnable'),
                                "confirms": network_info.get('minConfirm'),
                                "chain_name": network_info.get('netWork')
                            }
                            for coin_data in data
                            for network_info in coin_data.get('networkList', [])
                            if network_info.get('contract')
                        }

                        contract_address_lower = base_token_contract.lower()
                        if contract_address_lower in contract_dict:
                            network_info = contract_dict[contract_address_lower]
                            status = "✅" if network_info["deposit_enabled"] else "❌"
                            return {
                                "status": status,
                                "coin": network_info["coin"],
                                "confirmations": network_info["confirms"],
                                "chain": network_info["chain_name"]
                            }
                        else:
                            print(f"No matching contract address found for {base_token_contract} on MEXC.")
                            return None
                    else:
                        print(f"Error fetching data from MEXC: {response.status} - {await response.text()}")
                        return None
        except Exception as e:
            print(f'Error in MEXCExchange: {e}')
            return None
