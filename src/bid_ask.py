import sys
import asyncio
import ccxt.async_support as ccxt
from typing import List, Tuple
from src.logger import Logger

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class BidAsk:
    def __init__(self, logger: Logger = None) -> None:
        self.logger = logger.get_logger() if logger else None

    async def get_order_book(self, exchange_name: str, symbol: str) -> List[Tuple[float, float]]:
        try:
            exchange_class = getattr(ccxt, exchange_name, None)
            if exchange_class is None:
                raise ValueError(f"Exchange '{exchange_name}' is not supported by ccxt.")

            exchange_instance = exchange_class()
            try:
                order_book = await exchange_instance.fetch_order_book(symbol.upper())
                bids = order_book.get('bids', [])[:3]
                return bids
            finally:
                await exchange_instance.close()  # Ensure the instance is closed
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error fetching order book from {exchange_name}: {e}")
            else:
                print(f"Error fetching order book from {exchange_name}: {e}")
            return []

    async def get_bids_and_asks_info_for_exchange(self, exchange_name: str, symbol: str, price_dex: float) -> str:
        bids = await self.get_order_book(exchange_name, symbol)
        info = ""

        if bids:
            info += f"<b>{exchange_name.capitalize()}</b>\n\n"
            info += f"<code>{'Price':<12}{'Amount $':<11}{'Spread'}</code>\n\n"

            for price, amount in bids:
                if price <= 0 or amount <= 0:
                    if self.logger:
                        self.logger.warning(f"Invalid bid data received: price={price}, amount={amount}")
                    else:
                        print(f"Invalid bid data received: price={price}, amount={amount}")
                    continue

                amount_in_usd = price * amount
                spread = ((price - price_dex) / price) * 100
                info += "<code>{:<13.8f}{:<10.2f}{:>6.2f}%</code>\n".format(
                    price, amount_in_usd, spread
                )

            info += f"{'-' * 30}\n"
        else:
            if self.logger:
                self.logger.info(f"No bids available for {symbol} on {exchange_name}.")
            else:
                print(f"No bids available for {symbol} on {exchange_name}.")

        return info
