from abc import ABC, abstractmethod, abstractproperty
import base64
from dataclasses import dataclass
import struct
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


class Fuse(MetricsDefinition):
    """
    RC-RCBO device

         Example format:

         {
        "result": [
            {
                "code": "switch_1",
                "value": true
            },
            {
                "code": "countdown_1",
                "value": 0
            },
            {
                "code": "fault",
                "value": 0
            },
            {
                "code": "relay_status",
                "value": "2"
            },
            {
                "code": "child_lock",
                "value": false
            },
            {
                "code": "Voltage",
                "value": "CUsAAAAA"
            },
            {
                "code": "Current",
                "value": "AAcTAAAAAAAA"
            },
            {
                "code": "ActivePower",
                "value": "AA40AA40AAAAAAAA"
            },
            {
                "code": "LeakageCurrent",
                "value": 9
            },
            {
                "code": "Temperature",
                "value": 36
            },
            {
                "code": "RemainingEnergy",
                "value": 0
            },
            {
                "code": "CostParameters",
                "value": "CRQA"
            },
            {
                "code": "LeakageParameters",
                "value": "AQAAASwBAQA="
            },
            {
                "code": "VoltageThreshold",
                "value": "CcQBAQfQAQE="
            },
            {
                "code": "CurrentThreshold",
                "value": "ALuAAQE="
            },
            {
                "code": "TemperatureThreshold",
                "value": "MgEB"
            },
            {
                "code": "KWH",
                "value": 351644
            },
            {
                "code": "NumberAndType",
                "value": "280100000002        "
            },
            {
                "code": "locking",
                "value": false
            },
            {
                "code": "RKWH",
                "value": 0
            },
            {
                "code": "VRecording",
                "value": "CUYAAAAA"
            },
            {
                "code": "IRecording",
                "value": "AArqAAAAAAAA"
            }
        ],
        "success": true,
        "t": 1761770761925,
        "tid": "47de5af7b50811f0a25e9ed280a40f39"
    }

    """

    @override
    def collect(self) -> bytes:
        result = self.cloud.getstatus(self.device_id)
        data = result.get("result")
        metrics = self.metrics_schema

        # convert list of dicts into {code: value}
        datapoints = {item["code"]: item["value"] for item in data if "code" in item}

        for code, value in datapoints.items():
            if metrics.get(code) is None:
                print(f"{code=} not used in out definition")
                continue
            decoded = self.decode_metric(code, value)
            print(f"{code=}:{decoded}")
            # metrics[code].set(self.decode_metric(code, value))
            metrics[code].set(decoded)

        result = generate_latest(self.registry)
        return result

    @property
    @override
    def metrics_schema(self) -> dict[str, Gauge]:
        return {
            "switch_1": Gauge(
                "switch_1", "Switch status (0=false, 1=true)", registry=self.registry
            ),
            "countdown_1": Gauge("countdown_1", "Countdown", registry=self.registry),
            "fault": Gauge("fault", "Fault", registry=self.registry),
            "relay_status": Gauge(
                "relay_status", "Relay status", registry=self.registry
            ),
            "child_lock": Gauge(
                "child_lock", "Child lock (0=off, 1=on)", registry=self.registry
            ),
            "Voltage": Gauge("voltage", "Voltage", registry=self.registry),
            "Current": Gauge("current", "Current", registry=self.registry),
            "ActivePower": Gauge(
                "active_power",
                "Active power",
                registry=self.registry,
            ),
            "LeakageCurrent": Gauge(
                "leakage_current",
                "Leakage current",
                registry=self.registry,
            ),
            "Temperature": Gauge("temperature", "Temperature", registry=self.registry),
            "RemainingEnergy": Gauge(
                "remaining_energy", "Remaining energy", registry=self.registry
            ),
            "VoltageThreshold": Gauge(
                "voltage_threshold", "Voltage threshold", registry=self.registry
            ),
            "CurrentThreshold": Gauge(
                "current_threshold", "Current Threshold", registry=self.registry
            ),
            "TemperatureThreshold": Gauge(
                "temperature_threshold", "Temperature threshold", registry=self.registry
            ),
            "KWH": Gauge("kwh", "kwh", registry=self.registry),
            "RKWH": Gauge("rkwh", "rkwh", registry=self.registry),
        }

    def decode_metric(self, name: str, val: str | int | bool):
        if isinstance(val, int):
            return val
        if isinstance(val, bool):
            return int(bool)
        if isinstance(val, str):
            try:
                return float(val)
            except Exception:
                ...  # continue trying
        try:
            raw = base64.b64decode(val)
            # Most Tuya encodings use 4 bytes for a little-endian integer
            num = struct.unpack("<I", raw[:4])[0]

            if name.lower().startswith("voltage"):
                return num / 100.0  # e.g. 19273 -> 192.73 V
            elif name.lower().startswith("current"):
                return num / 1000.0  # e.g. 749568 -> 0.749 A
            elif name.lower().startswith("activepower"):
                return num / 100.0  # e.g. 13326 -> 133.26 W
            else:
                return float(num)
        except Exception as e:
            print(f"{e} for {name=}:{val=}")
            return -1
