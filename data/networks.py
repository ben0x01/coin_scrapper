from dataclasses import dataclass, field
from typing import Dict

@dataclass(frozen=True)
class ChainMapping:
    network: Dict[str, str] = field(default_factory=lambda: {
        "ethereum": "ether",
        "bsc": "bnb",
        "fantom": "fantom",
        "polygon": "polygon",
        "arbitrum": "arbitrum",
        "optimism": "optimism",
        "avalanche": "avalanche",
        "solana": "solana",
        "aptos": "aptos",
        "blast": "blast",
        "linea": "linea",
        "mantle": "mantle",
        "mode": "mode",
        "scroll": "scroll",
        "core": "coredao",
        "zksync": "zksync",
        "base": "base"
    })

    def get_chain_key(self, chain_id: str) -> str:
        return self.network.get(chain_id)


@dataclass(frozen=True)
class InchChainMapping:
    network: Dict[str, str] = field(default_factory=lambda: {
        "ethereum": "1",
        "bsc": "56",
        "fantom": "250",
        "polygon": "137",
        "arbitrum": "42161",
        "optimism": "10",
        "avalanche": "43114",
        "zksync": "324",
        "base": "8453"
    })
    def get_chain_key(self, chain_id: str) -> str:
        return self.network.get(chain_id)