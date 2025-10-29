from abc import abstractmethod
import time
from typing import override
import tinytuya
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    Gauge,
)

from metrics_definition import AutomaticTransferSwitch, Fuse, MetricsDefinition

device_id_to_metrics: dict[str, type[MetricsDefinition]] = {
    "bfe98afa941d5a1e2def8s": AutomaticTransferSwitch,
    "bf62301ef04e38d881ugcu": Fuse,
    "bf1a684e80ae942e4dji6b": Fuse,
}


def collect_metrics(cloud: tinytuya.Cloud, device_id: str) -> bytes:
    registry = CollectorRegistry()

    collector = device_id_to_metrics[device_id](
        registry=registry, cloud=cloud, device_id=device_id
    )
    return collector.collect()
