import aiohttp

from exchange_base import Exchange

class BitgetExchange(Exchange):
    def __init__(self):
        super().__init__("Bitget", logger_name="BitgetExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            url = "https://api.bitget.com/api/v2/spot/public/coins"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from the API for Bitget. Status code: {response.status}")
                        return None

                    data = await response.json()

                    if data.get('code') == '00000' and 'data' in data:
                        coins_data = data['data']
                        for coin_data in coins_data:
                            chains = coin_data.get('chains', [])
                            for chain_info in chains:
                                contract_address = chain_info.get('contractAddress')
                                deposit_enabled = chain_info.get('rechargeable')
                                currency = coin_data.get('coin')
                                confirms = chain_info.get('depositConfirm')
                                chain_name = chain_info.get('chain')

                                if contract_address and contract_address.lower() == base_token_contract.lower():
                                    status = "✅" if deposit_enabled.lower() == 'true' else "❌"
                                    return {"status": status, "coin": currency, "confirmations": confirms, "chain": chain_name}
                        self.log.warning(f"No deposit information available for {base_token_contract} for Bitget.")
                        return None
                    else:
                        self.log.error("Failed to retrieve data from the API for Bitget.")
                        return None
        except Exception as e:
            self.log.error(f'Error in BitgetExchange: {e}')
            return None