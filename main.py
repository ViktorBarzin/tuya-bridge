import tinytuya
import json
import asyncio
import os

# tinytuya.json format:
# {
#     "apiKey": "",
#     "apiSecret": "",
#     "apiRegion": "eu",
#     "apiDeviceID": ""
# }


async def main() -> None:
    # Connect to Tuya Cloud
    c = tinytuya.Cloud()  # uses tinytuya.json
    # c = tinytuya.Cloud(
    #     apiRegion="eu",
    #     apiKey="",
    #     apiSecret="",
    #     apiDeviceID="",
    # )

    # Display list of devices
    # devices = c.getdevices()
    # print("Device List: %r" % devices)

    # Select a Device ID to Test
    id = ""  # ATS

    # Display Properties of Device
    # result = c.getproperties(id)
    # print("Properties of device:\n", result)

    # Display Status of Device
    # result = c.getstatus(id)
    # change swtih 1
    # result = c.getfunctions(id)
    # print("Status of device:\n", json.dumps(result, indent=4))

    # return
    # Send Command - Turn on switch
    commands = {
        "commands": [
            {"code": "power_mode", "value": "inverter_power"},
            # {"code": "power_mode", "value": "crid_power"},
            # {"code": "countdown_1", "value": 0},
        ]
    }
    print("Sending command...")
    result = c.sendcommand(id, commands)
    print("Results\n:", result)


if __name__ == "__main__":
    asyncio.run(main())
