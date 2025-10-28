#!/usr/bin/env bash

docker build -t viktorbarzin/tuya_bridge:latest . && docker push viktorbarzin/tuya_bridge:latest && kubectl rollout restart deployment tuya-bridge -n tuya-bridge
