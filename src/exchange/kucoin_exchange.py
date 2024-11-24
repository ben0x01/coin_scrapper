import aiohttp

from exchange_base import Exchange


class KuCoinExchange(Exchange):
    def __init__(self):
        super().__init__("KuCoin", logger_name="KuCoinExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            url = "https://api.kucoin.com/api/v3/currencies"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.warning(f"Failed to retrieve data from the API for KuCoin. Status code: {response.status}")
                        return None

                    response_data = await response.json()

                    if 'data' not in response_data or not isinstance(response_data['data'], list):
                        self.log.warning("Invalid response format from KuCoin API.")
                        return None

                    chain_dict = {
                        chain_info.get('contractAddress').lower(): {
                            "currency": entry.get("currency"),
                            "deposit_enabled": chain_info.get("isDepositEnabled"),
                            "confirms": chain_info.get("confirms"),
                            "chain_name": chain_info.get("chainId")
                        }
                        for entry in response_data['data']
                        if 'chains' in entry and isinstance(entry['chains'], list)
                        for chain_info in entry['chains']
                        if chain_info.get('contractAddress')
                    }

                    contract_address_lower = base_token_contract.lower()
                    if contract_address_lower in chain_dict:
                        chain_info = chain_dict[contract_address_lower]
                        status = "✅" if chain_info["deposit_enabled"] else "❌"
                        return {
                            "status": status,
                            "coin": chain_info["currency"],
                            "confirmations": chain_info["confirms"],
                            "chain": chain_info["chain_name"]
                        }
                    else:
                        self.log.warning(f"No matching contract address found for {base_token_contract} on KuCoin.")
                        return None
        except Exception as e:
            self.log.error(f'Error in KuCoinExchange: {e}')
            return None