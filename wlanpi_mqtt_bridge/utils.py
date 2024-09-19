import json
import os
import subprocess
from configparser import ConfigParser

from wlanpi_mqtt_bridge.MQTTBridge.Utils import get_default_gateways
from wlanpi_mqtt_bridge.MQTTBridge.structures import BridgeConfig


def confirm_prompt(question: str) -> bool:
    reply = None
    while reply not in ("y", "n"):
        reply = input(f"{question} (y/n): ").lower()
    return reply == "y"


def get_config(filepath) -> BridgeConfig:
    # Not the most elegant way to do this, but it's excruciatingly clear
    # how it works during development.
    # TODO: Refine this.
    config = ConfigParser()

    if os.path.exists(filepath):
        config.read(filepath)

    mqtt_server = config.get("MQTT", "server", fallback="<gateway>")
    mqtt_port = config.getint("MQTT", "port", fallback=1883)

    if mqtt_server in ["<gateway>", "", None]:
        mqtt_server = get_default_gateways()["eth0"]

    eth0_data = json.loads(
        subprocess.run(
            "jc ifconfig eth0".split(" "), capture_output=True, text=True
        ).stdout
    )[0]
    eth0_mac = eth0_data["mac_addr"]

    return BridgeConfig(
        mqtt_server,
        mqtt_port,
        identifier=eth0_mac,
    )
