import time

from exchange_base import Exchange


class BingXExchange(Exchange):
    def __init__(self):
        super().__init__("BingX", logger_name="BingXExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            path = '/openApi/wallets/v1/capital/config/getall'
            method = "GET"
            params_map = {
                "timestamp": str(int(time.time() * 1000))
            }
            params_str = "&".join([f"{k}={v}" for k, v in params_map.items()])

            response_data = await self.helper.send_request(method, path, params_str)
            if response_data is None:
                self.log.error("Failed to retrieve data from the API for BingX.")
                return None

            if 'data' in response_data and isinstance(response_data['data'], list):
                for coin in response_data['data']:
                    network_list = coin.get('networkList', [])
                    for network in network_list:
                        contract_address = network.get('contractAddress', '').strip()
                        deposit_enabled = network.get('depositEnable')
                        currency = coin.get('coin')
                        confirms = network.get('minConfirm')
                        chain_name = network.get('network')

                        if contract_address and contract_address.lower() == base_token_contract.lower():
                            status = "✅" if deposit_enabled else "❌"
                            return {"status": status, "coin": currency, "confirmations": confirms, "chain": chain_name}
                self.log.warning(f"No matching contract address found for {base_token_contract} for BingX.")
                return None
            else:
                self.log.error("Failed to retrieve valid data from the API for BingX.")
                return None
        except Exception as e:
            self.log.error(f'Error in BingXExchange: {e}')
            return None
