import asyncio
import aiohttp
import itertools

from typing import Optional, Any, List, Tuple

from src.logger import Logger
from data.networks import DextoolsMapping, InchChainMapping, CoingeckoMapping, DefilamaMapping

log = Logger(name="Dex Module", log_file="dex.log").get_logger()


async def dextools(pair_address_tools: str, chain_id: str, mapping: DextoolsMapping) -> Optional[str]:
    try:
        chain_key = mapping.get_chain_key(chain_id)
        if chain_key is None:
            log.warning(f"Unknown chain_id: {chain_id}")
            return None

        dextools_url = f"https://www.dextools.io/app/ru/{chain_key}/pair-explorer/{pair_address_tools}"
        return dextools_url
    except Exception as e:
        log.error(f"An error occurred: {str(e)}")
        return None


async def defilama_swap(base_token_contract: str, chain_id: str, mapping: DefilamaMapping) -> Optional[str]:
    try:
        chain_key = mapping.get_chain_key(chain_id)
        if chain_key is None:
            log.warning(f"Unknown chain_id defilama: {chain_id}")
            return None

        defilama_url = f"https://swap.defillama.com/?chain={chain_key}&from=0x0000000000000000000000000000000000000000&tab=swap&to={base_token_contract}"
        return defilama_url
    except Exception as e:
        log.error(f"An error occurred: {str(e)}")
        return None


async def coingecko(base_token_contract: str, chain_id: str, mapping: CoingeckoMapping) -> list[dict[
    str, dict[Any, Any] | Any]] | None:
    try:
        chain_key = mapping.get_chain_key(chain_id)
        if chain_key is None:
            log.warning(f"Unknown chain_id: {chain_id}")
            return None

        url = f"https://api.coingecko.com/api/v3/coins/{chain_id}/contract/{base_token_contract}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url=url) as response:
                response.raise_for_status()
                data = await response.json()

                if not data:
                    log.warning('Failed to get data from coingecko for', base_token_contract)
                    return None

                tickers = data.get('tickers', [])
                limited_platforms = dict(itertools.islice(data.get('platforms', {}).items(), 5))
                web_slug = data.get("web_slug")

                result = []
                for ticker in tickers:
                    market_name = ticker.get("market", {}).get("name")
                    converted_last_usd = ticker.get("converted_last", {}).get("usd")
                    converted_volume_usd = ticker.get("converted_volume", {}).get("usd")
                    trade_url = ticker.get("trade_url")

                    result.append({
                        "market_name": market_name,
                        "converted_last_usd": converted_last_usd,
                        "converted_volume_usd": converted_volume_usd,
                        "trade_url": trade_url,
                        "web_slug": web_slug,
                        "platforms": limited_platforms,
                    })

                for platform, address in limited_platforms.items():
                    log.info(f"- {platform}: {address}")

                return result

    except aiohttp.ClientError as e:
        log.error(f"Error fetching data from coingecko: {str(e)}")
        return None


async def inch(base_token_contract: str, chain_id: str, mapping: InchChainMapping) -> str | None:
    try:
        chain_key = mapping.get_chain_key(chain_id)
        if chain_key is None:
            log.warning(f"Unknown chain_id inch: {chain_id}")
            return None

        inch_url = f"https://app.1inch.io/#/{chain_key}/simple/swap/USDT/{base_token_contract}/import-token"
        return inch_url
    except Exception as e:
        log.error(f"An error occurred: {str(e)}")
        return None


async def fetch_token_data(token_addresses: List[str]) -> Optional[dict]:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{','.join(token_addresses)}"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    log.warning(f"Error: HTTP {response.status}")
                    return None
        except aiohttp.ClientError as e:
            log.error(f"Error fetching token data: {str(e)}")
            return None
        except Exception as e:
            log.error(f"Unexpected error: {str(e)}")
            return None


async def dextools_price(base_token_address: str) -> Optional[Tuple[float, float]]:
    url = f"https://public-api.dextools.io/trial/v2/token/solana/{base_token_address}/price"
    headers = {
        "accept": "application/json",
        "x-api-key": "aKNoPGjg975qJRiWdppF27eohCYtjZg14V3mXQaa"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()

                    if 'data' not in data or not data['data']:
                        log.warning(f"Unexpected response structure: {data}")
                        return None

                    price_change_5m_tools = data['data'].get('variation5m')
                    price_change_1h_tools = data['data'].get('variation1h')

                    if price_change_5m_tools is None or price_change_1h_tools is None:
                        log.warning(f"Missing price change data in response: {data['data']}")
                        return None

                    log.info(price_change_5m_tools)
                    log.info(price_change_1h_tools)
                    await asyncio.sleep(2)
                    return price_change_5m_tools, price_change_1h_tools
                else:
                    error_text = await response.text()
                    log.error(f"Error fetching token price: HTTP {response.status} - {error_text}")
                    return None
    except aiohttp.ClientError as e:
        log.error(f"Error fetching token price: {e}")
        return None
    except Exception as e:
        log.error(f"Unexpected error in dextools_price: {e}")
        return None
