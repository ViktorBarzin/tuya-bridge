from abc import abstractmethod
import time
import cachetools
from typing import Any, override
from tenacity import retry, stop_after_attempt, wait_exponential
import tinytuya
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    Gauge,
)

from metrics_definition import (
    AutomaticTransferSwitch,
    Fuse,
    MetricsDefinition,
    Thermostat,
)

cache = cachetools.TTLCache(maxsize=100, ttl=30)

device_id_to_metrics: dict[str, type[MetricsDefinition]] = {
    "bfe98afa941d5a1e2def8s": AutomaticTransferSwitch,
    "bf1a684e80ae942e4dji6b": Fuse,  # main
    "bf62301ef04e38d881ugcu": Fuse,  # garage
    "bf7efce9519bd508df431s": Thermostat,  # hol
    "bf70e80159641f61a5lzho": Thermostat,  # master bedroom
    "bf9597a0064f0349d4b09x": Thermostat,  # office
    "bfe64da91577117e0annt5": Thermostat,  # kid's room
}


@cachetools.cached(cache)
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def collect_metrics(cloud: tinytuya.Cloud, device_id: str) -> CollectorRegistry:
    registry = CollectorRegistry()

    collector = device_id_to_metrics[device_id](
        registry=registry, cloud=cloud, device_id=device_id
    )
    return collector.collect()
