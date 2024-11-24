import aiohttp

from exchange_base import Exchange


class XTExchange(Exchange):
    def __init__(self, api_key=None, secret_key=None, api_url=None):
        super().__init__("XT", api_key=api_key, secret_key=secret_key, api_url=api_url, logger_name="XTExchange")

    async def get_token_price_xt(self, symbol):
        try:
            market = f"{symbol.lower()}_usdt"
            url = f"https://sapi.xt.com/v4/public/ticker/price?symbol={market}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to get price for {symbol} on XT. Status code: {response.status}")
                        return None

                    data = await response.json()
                    if data.get("rc") == 0:
                        result = data.get("result", [])
                        if result:
                            price = result[0].get("p")
                            return price
                        else:
                            self.log.warning(f"No price data available for {symbol} on XT.")
                            return None
                    else:
                        self.log.error(f"Failed to get price for {symbol} on XT.")
                        return None
        except Exception as e:
            self.log.error(f"Error getting price for {symbol}: {e}")
            return None

    async def check_deposit_status(self, base_token_contract):
        try:
            url = "https://sapi.xt.com/v4/public/wallet/support/currency"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.log.error(f"Failed to retrieve data from the API for XT. Status code: {response.status}")
                        return None

                    data = await response.json()
                    if data.get("rc") == 0 and "result" in data:
                        tokens = data["result"]
                        for token in tokens:
                            currency = token.get("currency")
                            support_chains = token.get("supportChains", [])

                            for chain in support_chains:
                                contract_address = chain.get("contract", "")
                                deposit_enabled = chain.get("depositEnabled")
                                chain_name = chain.get("chain")

                                if contract_address and contract_address.lower() == base_token_contract.lower():
                                    if deposit_enabled:
                                        price = await self.get_token_price_xt(currency)
                                        if price:
                                            self.log.info(f"Price for {currency} is {price} USDT.")
                                        self.log.info(
                                            f"Deposit for {contract_address} is enabled on XT for {currency} on {chain_name} with price {price} USDT.")
                                        return {"status": "✅", "coin": currency, "chain": chain_name, "price": price}
                                    else:
                                        self.log.info(
                                            f"Deposit for {contract_address} is disabled on XT for {currency} on {chain_name}.")
                                        return {"status": "❌", "coin": currency, "chain": chain_name}

                        self.log.warning(f"No deposit information available for {base_token_contract} on XT.")
                        return None
                    else:
                        self.log.error("Failed to retrieve data from the API for XT.")
                        return None
        except Exception as e:
            self.log.error(f'Error in XTExchange: {e}')
            return None
