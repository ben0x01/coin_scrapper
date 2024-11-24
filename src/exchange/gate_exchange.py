import aiohttp

from exchange_base import Exchange


class GateIOExchange(Exchange):
    def __init__(self):
        super().__init__("GateIO", logger_name="GateIOExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            if not self.helper:
                self.log.error("Helper is not initialized. Please provide API credentials.")
                return None

            ticker = self.helper.get_ticker_by_contract(base_token_contract)
            if ticker is None:
                self.log.warning(f"No matching ticker found for contract: {base_token_contract}")
                return None

            host = "https://api.gateio.ws"
            prefix = "/api/v4"
            headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

            query_param = f'currency={ticker}'
            url = f'{host}{prefix}/wallet/currency_chains?{query_param}'

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from API. Status code: {response.status}")
                        return None

                    data = await response.json()
                    for item in data:
                        contract_address = item.get('contract_address')
                        deposit_enabled = item.get('is_deposit_disabled')
                        chain_name = item.get('chain')
                        status = '✅' if deposit_enabled == 0 else '❌'

                        if contract_address and contract_address.lower() == base_token_contract.lower():
                            self.log.info(f"Deposit for {contract_address} is {status} for Gate.io on {chain_name}.")
                            return {"status": status, "coin": ticker, "chain": chain_name}

                    self.log.warning(f"No deposit information available for {base_token_contract} for Gate.io.")
                    return None
        except Exception as e:
            self.log.error(f'Error in GateIOExchange: {e}')
            return None
