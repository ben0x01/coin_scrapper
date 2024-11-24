import aiohttp

from exchange_base import Exchange


class HuobiExchange(Exchange):
    def __init__(self):
        super().__init__("Huobi", logger_name="HuobiExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            url = "https://api.huobi.pro/v1/settings/common/chains"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from the API for Huobi. Status code: {response.status}")
                        return None

                    data = await response.json()

                    if data.get('status') == 'ok':
                        chains = data.get('data', [])

                        for chain in chains:
                            contract_address = chain.get('ca')
                            deposit_enabled = chain.get('de')
                            currency = chain.get('currency')
                            confirms = chain.get('fc')
                            chain_name = chain.get('dn')

                            if contract_address and contract_address.lower() == base_token_contract.lower():
                                status = "✅" if deposit_enabled else "❌"
                                return {"status": status, "coin": currency, "confirmations": confirms, "chain": chain_name}

                        self.log.warning(f"No matching contract address found for {base_token_contract} for Huobi.")
                        return None
                    else:
                        self.log.error("Failed to retrieve data from the API for Huobi.")
                        return None
        except Exception as e:
            self.log.error(f'Error in HuobiExchange: {e}')
            return None