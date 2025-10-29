from abc import ABC, abstractmethod, abstractproperty
from dataclasses import dataclass
from typing import Any, override
from prometheus_client import (
    CollectorRegistry,
    Gauge,
    generate_latest,
)
from abc import abstractmethod

import tinytuya


@dataclass
class MetricsDefinition(ABC):
    registry: CollectorRegistry
    cloud: tinytuya.Cloud
    device_id: str

    @property
    @abstractmethod
    def metrics_schema(self) -> dict[str, Gauge]: ...

    @abstractmethod
    def collect(self) -> bytes: ...


class AutomaticTransferSwitch(MetricsDefinition):
    @property
    @override
    def metrics_schema(self) -> dict[str, Gauge]:
        metrics = {
            "fault": Gauge("fault", "Device fault code", registry=self.registry),
            "power_fault": Gauge(
                "power_fault", "Power fault flag", registry=self.registry
            ),
            "load_power": Gauge(
                "load_power_watts", "Load power (W)", registry=self.registry
            ),
            "load_current": Gauge(
                "load_current_amps", "Load current (A)", registry=self.registry
            ),
            "overpower_value": Gauge(
                "overpower_value", "Overpower threshold", registry=self.registry
            ),
            "lowpower_switch": Gauge(
                "lowpower_switch", "Low power threshold", registry=self.registry
            ),
            "lowpower_reset": Gauge(
                "lowpower_reset", "Low power reset threshold", registry=self.registry
            ),
            "totalele_add": Gauge(
                "totalele_add",
                "Total accumulated energy (Wh) from inverter",
                registry=self.registry,
            ),
            "dwele_add": Gauge(
                "dwele_add",
                "Total accumulated energy (Wh) from grid",
                registry=self.registry,
            ),
            "voltage_l1": Gauge(
                "voltage_l1_volts", "L1 voltage (V)", registry=self.registry
            ),
            "voltage_l2": Gauge(
                "voltage_l2_volts", "L2 voltage (V)", registry=self.registry
            ),
            "voltage_batt": Gauge(
                "voltage_battery_volts", "Battery voltage (V)", registry=self.registry
            ),
            "power_mode": Gauge(
                "power_mode", "Power source (0=grid,1=inverter)", registry=self.registry
            ),
        }
        return metrics

    @override
    def collect(self) -> bytes:
        result = self.cloud.getstatus(self.device_id)
        data = result.get("result")

        metrics = self.metrics_schema

        # convert list of dicts into {code: value}
        datapoints = {item["code"]: item["value"] for item in data if "code" in item}

        for code, val in datapoints.items():
            if code == "voltage_display":
                v1, v2, batt = self.parse_voltage_string(val)
                if v1 is not None:
                    metrics["voltage_l1"].set(v1)
                if v2 is not None:
                    metrics["voltage_l2"].set(v2)
                if batt is not None:
                    metrics["voltage_batt"].set(batt)

            elif code == "power_mode":
                metrics["power_mode"].set(self.map_power_mode(val))

            elif code in metrics:
                try:
                    metrics[code].set(float(val))
                except (TypeError, ValueError):
                    pass
        result = generate_latest(self.registry)
        return result

    def parse_voltage_string(self, vstr):
        """Parse concatenated voltage string like '0238024024.9'"""
        try:
            # crude example: split into 3 parts of 4, 4, and rest
            l1 = int(vstr[0:3])
            l2 = int(vstr[3:6])
            batt = float(vstr[6:])
            return l1, l2, batt
        except Exception:
            return None, None, None

    def map_power_mode(self, mode_str):
        """
        Map power mode strings to numeric values for Prometheus.
        - 'crid_power' or 'grid_power' => 0
        - 'invert_power' or 'inverter_power' => 1
        """
        if not isinstance(mode_str, str):
            return 0
        mode_str = mode_str.lower()
        if "invert" in mode_str:
            return 1
        return 0
