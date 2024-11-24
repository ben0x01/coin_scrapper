import aiohttp

from exchange_base import Exchange


class BitmartExchange(Exchange):
    def __init__(self):
        super().__init__("Bitmart", logger_name="BitmartExchange")

    async def check_deposit_status(self, base_token_contract):
        try:
            url = "https://api-cloud.bitmart.com/account/v1/currencies"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from the API for Bitmart. Status code: {response.status}")
                        return None

                    data = await response.json()

                    if data.get("code") == 1000:
                        currencies = data.get("data", {}).get("currencies", [])

                        if currencies:
                            base_token_contract_lower = base_token_contract.lower()

                            for currency_info in currencies:
                                currency_contract_address = currency_info.get("contract_address")
                                if currency_contract_address is not None:
                                    currency_contract_address_lower = currency_contract_address.lower()

                                    if currency_contract_address_lower == base_token_contract_lower:
                                        deposit_enabled = currency_info.get("deposit_enabled")
                                        currency = currency_info.get("currency")
                                        status = "✅" if deposit_enabled else "❌"
                                        return {"status": status, "coin": currency}
                            else:
                                self.log.warning("No matching contract address found for Bitmart.")
                                return None
                        else:
                            self.log.warning("No currencies found in the data from Bitmart.")
                            return None
                    else:
                        self.log.error("Failed to retrieve data from the API for Bitmart.")
                        return None
        except Exception as e:
            self.log.error(f'Error in BitmartExchange: {e}')
            return None
