import asyncio
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import BINGX_API_KEY, BINGX_SECRET_KEY, API_HASH, API_ID, MEXC_API_KEY, MEXC_SECRET_KEY, CHANELLE_ID
from data.api_urls import BINGX_API_URL
from data.networks import ChainMapping, InchChainMapping
from src.bid_ask import BidAsk
from src.dexes import coingecko, defilama_swap, dextools, fetch_token_data, inch, dextools_price
from src.exchange.gate_exchange import GateIOExchange
from src.exchange.coinex_exchange import CoinExExchange
from src.exchange.mexc_exchange import MEXCExchange
from src.exchange.xt_exchange import XTExchange
from src.exchange.bingx_exchange import BingXExchange
from src.exchange.kucoin_exchange import KuCoinExchange
from src.exchange.bitget_exchange import BitgetExchange
from src.exchange.bitmart_exchange import BitmartExchange
from src.exchange.huobi_exchange import HuobiExchange
from src.helper import Helper
from src.telegram_client import Telegram
from src.logger import Logger

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

helper = Helper(BINGX_API_KEY, BINGX_SECRET_KEY, BINGX_API_URL)
chain_mapping = ChainMapping()
inch_mapping = InchChainMapping()

# Инициализация экземпляров бирж
gateio_exchange = GateIOExchange()
kucoin_exchange = KuCoinExchange()
mexc_exchange = MEXCExchange(MEXC_API_KEY, MEXC_SECRET_KEY)
coinex_exchange = CoinExExchange()
bitmart_exchange = BitmartExchange()
huobi_exchange = HuobiExchange()
bitget_exchange = BitgetExchange()
xt_exchange = XTExchange()
bingx_exchange = BingXExchange()

# Инициализация Telegram клиента
telegram_client = Telegram(API_ID, API_HASH, "session")

# Инициализация логгера
logger = Logger("Main")

# Инициализация BidAsk
bid_ask = BidAsk(logger)

# Словарь экземпляров бирж
exchange_instances = {
    'huobi': huobi_exchange,
    'kucoin': kucoin_exchange,
    'mexc': mexc_exchange,
    'bitget': bitget_exchange,
    'bingx': bingx_exchange,
    'gateio': gateio_exchange,
    'coinex': coinex_exchange,
    'bitmart': bitmart_exchange,
    'xt': xt_exchange,
}

def format_liquidity(liquidity_value):
    if liquidity_value >= 1e6:
        return "{:.1f}M".format(liquidity_value / 1e6)
    elif liquidity_value >= 1e3:
        return "{:.1f}k".format(liquidity_value / 1e3)
    else:
        return "{:.0f}".format(liquidity_value)

def extract_project_links(pair):
    project_website = None
    project_twitter = None
    project_telegram = None

    if 'info' in pair:
        if 'websites' in pair['info']:
            websites = pair['info']['websites']
            for website in websites:
                if website['label'].lower() == 'website':
                    project_website = website['url']
                    break
        if 'socials' in pair['info']:
            socials = pair['info']['socials']
            for social in socials:
                if social['type'].lower() == 'twitter':
                    project_twitter = social['url']
                elif social['type'].lower() == 'telegram':
                    project_telegram = social['url']

    return project_website, project_twitter, project_telegram

async def process_single_pair(pair, seen_tokens):
    # Извлекаем необходимые данные из пары
    price_change_m5 = pair.get('priceChange', {}).get('m5')
    price_change_h1 = pair.get('priceChange', {}).get('h1')
    if price_change_m5 is None or price_change_h1 is None:
        return  # Пропускаем, если данные об изменении цены недоступны

    symbol = pair['baseToken']['symbol']
    quote_symbol = pair['quoteToken']['symbol']
    price = float(pair.get('priceUsd', 0))
    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
    liquidity_base = float(pair.get('liquidity', {}).get('base', 0))
    base_token_contract = pair['baseToken']['address']
    quote_token_contract = pair['quoteToken']['address']
    pair_address = pair['pairAddress']
    dex_id = pair.get('dexId')
    chain_id = pair.get('chainId')
    link = pair['url']

    project_website, project_twitter, project_telegram = extract_project_links(pair)

    if ((price_change_m5 < -1 or price_change_h1 < -50) and
        (symbol, quote_symbol) not in seen_tokens and
        chain_id != 'solana' and dex_id != 'dedust'):
        await process_token(pair, seen_tokens)
    elif ((price_change_m5 < -40 or price_change_h1 < -50) and
          (symbol, quote_symbol) not in seen_tokens and
          chain_id == 'solana'):
        await process_token(pair, seen_tokens, solana=True)

async def process_token(pair, seen_tokens, solana=False):
    price_change_m5 = pair['priceChange']['m5']
    price_change_h1 = pair['priceChange']['h1']
    symbol = pair['baseToken']['symbol']
    quote_symbol = pair['quoteToken']['symbol']
    price = float(pair.get('priceUsd', 0))
    liquidity = float(pair.get('liquidity', {}).get('usd', 0))
    liquidity_base = float(pair.get('liquidity', {}).get('base', 0))
    base_token_contract = pair['baseToken']['address']
    pair_address = pair['pairAddress']
    dex_id = pair.get('dexId')
    chain_id = pair.get('chainId')
    link = pair['url']

    project_website, project_twitter, project_telegram = extract_project_links(pair)

    seen_tokens.add((symbol, quote_symbol))

    native_liquidity = liquidity - liquidity_base * price
    token_liquidity = liquidity - native_liquidity

    formatted_token_liquidity = format_liquidity(token_liquidity)
    formatted_native_liquidity = format_liquidity(native_liquidity)

    emoji_down = "🔻" if price_change_m5 < -1 else ""
    fall_emoji = "🔥" if price_change_m5 < -40 else ""
    low_liquidity_emoji = "🚨" if liquidity < 300000 else "🔥"

    dextools_link = await dextools(pair_address, chain_id, chain_mapping)
    dextools_link = f" | <a href='{dextools_link}'>Tools</a>" if dextools_link else ""

    defilama_link = await defilama_swap(base_token_contract, chain_id, chain_mapping)
    defilama_link = f" | <a href='{defilama_link}'>DefiLama</a>" if defilama_link else ""

    inch_link = await inch(base_token_contract, chain_id, inch_mapping)
    inch_link = f" | <a href='{inch_link}'>1inch</a>" if inch_link else ""

    website_link = f" | <a href='{project_website}'>Website</a>" if project_website else ""
    twitter_link = f" | <a href='{project_twitter}'>Twitter</a>" if project_twitter else ""
    telegram_link = f" | <a href='{project_telegram}'>Telegram</a>" if project_telegram else ""

    token_slug = await helper.coinmarketcap(base_token_contract)
    coinmarketcap_link = f" | <a href='https://coinmarketcap.com/currencies/{token_slug}/'>CMC</a>" if token_slug else ""

    coingecko_info = await coingecko(base_token_contract, chain_id, chain_mapping)
    time.sleep(2)

    print(f"Pair: {symbol}/{quote_symbol}, Price: {price}, Liquidity Token: {formatted_token_liquidity}, Native Liquidity: {formatted_native_liquidity}")

    message_text = (
        f"<code>{symbol}</code> / {price_change_m5}% 5m / {price_change_h1}% 1h ⚡️🔻{fall_emoji}\n\n"
        f"<code>Pair:{' ' * 1}{symbol} / {quote_symbol}</code>\n"
        f"<code>Fall:{' ' * 1}{price_change_m5}% 5m / {price_change_h1}% 1h</code>\n"
        f"<code>Cost:{' ' * 1}{price}$</code>\n"
        f"<code>Pool:{' ' * 1}{formatted_token_liquidity}$ {symbol} / {formatted_native_liquidity}$ {quote_symbol}</code> {low_liquidity_emoji}\n"
        f"<code>Swap:{' ' * 1}{chain_id} / {dex_id}</code>\n\n"
        f"<a href='{link}'>Screener</a>{dextools_link}{coinmarketcap_link}{website_link}{twitter_link}{telegram_link}{defilama_link}{inch_link}\n\n"
        f"<b>Contract address:</b> <code>{base_token_contract}</code>\n"
    )

    if coingecko_info:
        message_text += "\n"
        gecko_info_lines = ["<code>Exchange   Spread</code>\n"]
        valid_exchanges = [
            "Binance",
            "Bybit",
            "OKX",
            "Bitget",
            "Gate.io",
            "Coinbase Pro",
            "Upbit",
            "HTX",
            "DigiFinex",
            "BitMart",
            "Kraken",
            "KuCoin",
            "Bithumb",
            "ProBit",
            "Bitfinex",
            "BitMEX",
            "Bitrue",
            "AscendEX (BitMax)",
            "MEXC",
            "BingX",
            "XT.COM",
            "CoinEx",
            "LBank",
            "Poloniex",
        ]
        exchange_width = 8
        info_lines = 0
        for info in coingecko_info:
            if info_lines >= 10:
                break
            market_name, converted_last_usd, _, trade_url, _, _, _ = info
            market_name_cut = market_name[:exchange_width].ljust(exchange_width)
            spread_gecko = ((float(converted_last_usd) - price) / float(converted_last_usd)) * 100
            if market_name in valid_exchanges:
                gecko_info_line = "<code>{}</code><code>{:>7.0f}%</code>    {}".format(
                    market_name_cut,
                    spread_gecko,
                    f"<a href='{trade_url}'>Link</a>"
                )
                gecko_info_lines.append(gecko_info_line)
                info_lines += 1

        if gecko_info_lines:
            gecko_info_text = "\n".join(gecko_info_lines)
            message_text += f"<blockquote>{gecko_info_text}</blockquote>\n"

    # Решаем, отправлять ли сообщение в Telegram на основе ликвидности и других условий
    if native_liquidity > 15000 and token_liquidity > 15000 and dex_id != 'balancer' and dex_id != 'dedust':
        # Для токенов Solana проверяем изменение цены с Dextools
        if solana:
            dextools_data = await dextools_price(base_token_contract)
            time.sleep(2)
            if dextools_data:
                price_change_5m_tools, price_change_1h_tools = dextools_data
                if (helper.is_within_20_percent(price_change_m5, price_change_5m_tools) and
                    helper.is_within_20_percent(price_change_h1, price_change_1h_tools)):
                    message_id = await telegram_client.send_telegram_message(message_text, base_token_contract, CHANELLE_ID)
                else:
                    print("Price changes differ by more than 20% - not sending message.")
                    return
            else:
                print("Error retrieving data from Dextools.")
                return
        else:
            # Для остальных токенов отправляем сообщение напрямую
            message_id = await telegram_client.send_telegram_message(message_text, base_token_contract, CHANELLE_ID)

        # Сохраняем message_id и base_token_contract
        with open('messages.txt', 'a', encoding='utf-8') as file:
            file.write(f"{message_id} {base_token_contract}\n")

        # Получаем информацию о депозитах и биржах с активными депозитами
        deposits_info, exchanges_with_deposits = await get_deposits_info(base_token_contract)

        # Получаем информацию о бид/аск
        bids_and_asks_info = await get_bids_and_asks_info(exchanges_with_deposits, price)

        if deposits_info:
            updated_message_text = message_text + f"\n<pre><code>Name{' ' * 4}Deposit{' ' * 2}Conf{' ' * 2}Chain{' ' * 2}\n\n{deposits_info}\n</code></pre>"
            updated_message_text += f"\n\n<pre><code>{bids_and_asks_info}</code></pre>"
            updated_message_text += (
                f"\n"
                f"{' ' * 26}<a href='https://t.me/OxDever_bot'>Dumper | Arbitrage</a>\n"
            )

            try:
                if message_id is not None:
                    await telegram_client.update_telegram_message(message_id, updated_message_text, -1002045188654)
                else:
                    print("Message ID is None")
                    with open('errors.txt', 'a', encoding='utf-8') as file:
                        file.write(f"Message ID is None for coin: {base_token_contract}\n")
            except Exception as e:
                with open('errors.txt', 'a', encoding='utf-8') as file:
                    file.write(f"Error: {str(e)}\n")
                    print(f"Error results {str(e)}")

async def get_deposits_info(base_token_contract):
    # Получаем информацию о депозитах с бирж
    htx_deposit_info = await huobi_exchange.check_deposit_status(base_token_contract)
    kucoin_deposit_info = await kucoin_exchange.check_deposit_status(base_token_contract)
    mexc_deposit_info = await mexc_exchange.check_deposit_status(base_token_contract)
    bitget_deposit_info = await bitget_exchange.check_deposit_status(base_token_contract)
    bingx_deposit_info = await bingx_exchange.check_deposit_status(base_token_contract)
    gateio_deposit_info = await gateio_exchange.check_deposit_status(base_token_contract)
    bitmart_deposit_info = await bitmart_exchange.check_deposit_status(base_token_contract)
    coinex_deposit_info = await coinex_exchange.check_deposit_status(base_token_contract)
    xt_deposit_info = await xt_exchange.check_deposit_status(base_token_contract)

    deposits_info = ""
    exchanges_with_deposits = []
    exchange_width = 10
    status_width = 6
    confirms_width = 4

    for exchange_name, deposit_info, exchange_key in [
        ('HTX', htx_deposit_info, 'huobi'),
        ('KuCoin', kucoin_deposit_info, 'kucoin'),
        ('MEXC', mexc_deposit_info, 'mexc'),
        ('Bitget', bitget_deposit_info, 'bitget'),
        ('BingX', bingx_deposit_info, 'bingx'),
        ('Gate.io', gateio_deposit_info, 'gateio'),
        ('CoinEx', coinex_deposit_info, 'coinex'),
        ('BitMart', bitmart_deposit_info, 'bitmart'),
        ('XT.COM', xt_deposit_info, 'xt'),
    ]:
        if deposit_info is not None:
            status = deposit_info['status']
            confirmations = deposit_info.get('confirmations', '')
            chain = deposit_info.get('chain', '')
            deposits_info += f"<code>{exchange_name:<{exchange_width}}{' '}{status:<{status_width}}{' '}{confirmations:<{confirms_width}}{' '}{chain}</code>\n"
            if status == '✅':
                exchange_instance = exchange_instances[exchange_key]
                exchanges_with_deposits.append((exchange_instance, deposit_info['coin']))

    return deposits_info, exchanges_with_deposits

async def get_bids_and_asks_info(exchanges_with_deposits, price):
    bids_and_asks_info = ""
    for exchange_instance, coin_symbol in exchanges_with_deposits:
        market_symbol = f"{coin_symbol}/USDT"
        info = await bid_ask.get_bids_and_asks_info_for_exchange(exchange_instance, market_symbol, price)
        if info:
            bids_and_asks_info += info
    return bids_and_asks_info

async def process_pairs(pairs):
    seen_tokens = set()
    try:
        for pair in pairs:
            await process_single_pair(pair, seen_tokens)
    except Exception as e:
        with open('errors.txt', 'a', encoding='utf-8') as file:
            file.write(f"Error: {str(e)}\n")
            print(f"Error results {str(e)}")

async def process_tokens(file_path):
    try:
        token_addresses = helper.read_token_addresses(file_path)
        batch_size = 30
        max_requests_per_minute = 295
        delay_between_batches = 55 / max_requests_per_minute

        while True:
            start_time = time.time()

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for i in range(0, len(token_addresses), batch_size):
                    batch = token_addresses[i:i + batch_size]
                    futures.append(executor.submit(fetch_token_data, batch))

                    # Ожидаем между пакетами, чтобы не превысить лимиты
                    if len(futures) >= max_requests_per_minute:
                        for future in as_completed(futures):
                            result = future.result()
                            if result and 'pairs' in result:
                                await process_pairs(result['pairs'])
                        futures = []
                        elapsed_time = time.time() - start_time
                        if elapsed_time < delay_between_batches:
                            time.sleep(delay_between_batches - elapsed_time)
                        start_time = time.time()

                for future in as_completed(futures):
                    result = future.result()
                    if result and 'pairs' in result:
                        await process_pairs(result['pairs'])

            print("Sleeping for 60 seconds...")
            time.sleep(65)
            print("Waking up...")
    except Exception as e:
        with open('errors.txt', 'a', encoding='utf-8') as file:
            file.write(f"Error: {str(e)}\n")
            print(f"Error results {str(e)}")

def main():
    file_path = 'valid_exchanges.txt'
    asyncio.run(process_tokens(file_path))

if __name__ == "__main__":
    main()