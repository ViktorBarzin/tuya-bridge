#!/usr/bin/env python3
import time
import tinytuya
from prometheus_client import (
    CollectorRegistry,
    generate_latest,
    Gauge,
)

registry = CollectorRegistry()

metrics = {
    "fault": Gauge("tuya_fault_code", "Device fault code", registry=registry),
    "power_fault": Gauge("tuya_power_fault", "Power fault flag", registry=registry),
    "load_power": Gauge("tuya_load_power_watts", "Load power (W)", registry=registry),
    "load_current": Gauge(
        "tuya_load_current_amps", "Load current (A)", registry=registry
    ),
    "overpower_value": Gauge(
        "tuya_overpower_value", "Overpower threshold", registry=registry
    ),
    "lowpower_switch": Gauge(
        "tuya_lowpower_switch", "Low power threshold", registry=registry
    ),
    "lowpower_reset": Gauge(
        "tuya_lowpower_reset", "Low power reset threshold", registry=registry
    ),
    "totalele_add": Gauge(
        "tuya_total_energy_wh", "Total accumulated energy (Wh)", registry=registry
    ),
    "dwele_add": Gauge(
        "tuya_partial_energy_wh", "Partial energy (Wh)", registry=registry
    ),
    "voltage_l1": Gauge("tuya_voltage_l1_volts", "L1 voltage (V)", registry=registry),
    "voltage_l2": Gauge("tuya_voltage_l2_volts", "L2 voltage (V)", registry=registry),
    "voltage_batt": Gauge(
        "tuya_voltage_battery_volts", "Battery voltage (V)", registry=registry
    ),
    "power_mode": Gauge(
        "tuya_power_mode", "Power source (0=grid,1=inverter)", registry=registry
    ),
}


def parse_voltage_string(vstr):
    """Parse concatenated voltage string like '0238024024.9'"""
    try:
        # crude example: split into 3 parts of 4, 4, and rest
        l1 = int(vstr[0:3])
        l2 = int(vstr[3:6])
        batt = float(vstr[6:])
        return l1, l2, batt
    except Exception:
        return None, None, None


def map_power_mode(mode_str):
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


def collect_metrics(cloud: tinytuya.Cloud, device_id: str) -> bytes:
    result = cloud.getstatus(device_id)
    data = result.get("result")

    # convert list of dicts into {code: value}
    datapoints = {item["code"]: item["value"] for item in data if "code" in item}

    for code, val in datapoints.items():
        if code == "voltage_display":
            v1, v2, batt = parse_voltage_string(val)
            if v1 is not None:
                metrics["voltage_l1"].set(v1)
            if v2 is not None:
                metrics["voltage_l2"].set(v2)
            if batt is not None:
                metrics["voltage_batt"].set(batt)

        elif code == "power_mode":
            metrics["power_mode"].set(map_power_mode(val))

        elif code in metrics:
            try:
                metrics[code].set(float(val))
            except (TypeError, ValueError):
                pass
    result = generate_latest(registry)
    return result
