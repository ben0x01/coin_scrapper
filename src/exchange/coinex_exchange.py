import aiohttp

from exchange_base import Exchange


class CoinExExchange(Exchange):
    def __init__(self):
        super().__init__("CoinEx", logger_name="CoinExExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            url_contracts = "https://api.coinex.com/v2/assets/info"
            async with aiohttp.ClientSession() as session:
                async with session.get(url_contracts) as response_contracts:
                    if response_contracts.status != 200:
                        self.log.error(f"Failed to retrieve data from the API for CoinEx. Status code: {response_contracts.status}")
                        return None

                    data_contracts = await response_contracts.json()

                    if data_contracts.get('code') == 0:
                        tokens = data_contracts.get('data', [])

                        token_found = None

                        for token in tokens:
                            chain_info_list = token.get('chain_info', [])
                            for chain_info in chain_info_list:
                                contract_address = chain_info.get('identity')
                                if contract_address and contract_address.lower() == base_token_contract.lower():
                                    token_found = token
                                    break
                            if token_found:
                                break

                        if token_found:
                            token_short_name = token_found.get('short_name')

                            url_deposit_info = f"https://api.coinex.com/v2/assets/deposit-withdraw-config?ccy={token_short_name}"
                            async with session.get(url_deposit_info) as response_deposit_info:
                                if response_deposit_info.status != 200:
                                    self.log.error(f"Failed to retrieve deposit information for {token_short_name} from CoinEx. Status code: {response_deposit_info.status}")
                                    return None

                                data_deposit_info = await response_deposit_info.json()

                                if data_deposit_info.get('code') == 0:
                                    deposit_info = data_deposit_info.get('data', {})
                                    chains_info = deposit_info.get('chains', [])

                                    for chain_info in chains_info:
                                        deposit_enabled = chain_info.get('deposit_enabled')
                                        chain_name = chain_info.get('chain')
                                        confirms = chain_info.get('safe_confirmations')

                                        status = "✅" if deposit_enabled else "❌"
                                        return {"status": status, "coin": token_short_name, "confirmations": confirms, "chain": chain_name}
                                else:
                                    self.log.error(f"Failed to retrieve deposit information for {token_short_name} from CoinEx.")
                                    return None
                        else:
                            self.log.warning(f"No matching contract address found for {base_token_contract} on CoinEx.")
                            return None
                    else:
                        self.log.error("Failed to retrieve token data from CoinEx.")
                        return None
        except Exception as e:
            self.log.error(f"Error in CoinExExchange: {e}")
            return None
