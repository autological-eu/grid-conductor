"""Ten-step curve multistart with model-only price-root fallback, Jan/Apr pilot."""
from pathlib import Path

import numpy as np

import test_batched_transport_multistart_2025 as pilot
from batched_transport_price_multistart_2025 import PriceMultistartMarket
from sigmoid_month_pairs_2025 import ROOT


def market_factory(source):
    market=PriceMultistartMarket(source.zones,source.groups,source.lower,source.upper,
        source.edges,source.capacity,source.source,source.load,cost=source.cost,
        thermal_tau=source.thermal_tau,renewable_tau=source.renewable_tau,
        flow_tau=source.flow_tau)
    market.reference=np.maximum(market.capacity.max(axis=0),.001)
    return market


if __name__=='__main__':
    pilot.OUT=ROOT/'data/bidding-zone-network-2025/curve-price-multistart-10-v1'
    pilot.MARKET_FACTORY=market_factory
    pilot.EXTRA_SOURCES=(Path(__file__),ROOT/'tools/batched_transport_price_multistart_2025.py')
    pilot.main()
