#!/bin/env python3
import json
import logging
import os
import signal
import subprocess
import sys
from configparser import ConfigParser
from types import FrameType
from typing import Optional, Union

from wlanpi_mqtt_bridge.MQTTBridge.Bridge import Bridge
from wlanpi_mqtt_bridge.MQTTBridge.structures import BridgeConfig
from wlanpi_mqtt_bridge.MQTTBridge.Utils import get_default_gateways

logger = logging.getLogger(__name__)
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(encoding="utf-8", level=logging.DEBUG)

CONFIG_DIR = "/etc/wlanpi-mqtt-bridge"
CONFIG_FILE = "/etc/wlanpi-mqtt-bridge/config.toml"


def get_config(filepath) -> BridgeConfig:
    # Not the most elegant way to do this, but it's excruciatingly clear
    # how it works during development.
    # TODO: Refine this.
    config = ConfigParser()

    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)

    mqtt_server = config.get("MQTT", "server", fallback="<gateway>")
    mqtt_port = config.getint("MQTT", "port", fallback=1884)

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


def run():
    config = get_config(CONFIG_FILE)
    bridge = Bridge(**config.__dict__)

    # noinspection PyUnusedLocal
    def signal_handler(
        sig: Union[int, signal.Signals], frame: Optional[FrameType]
    ) -> None:
        logger.info("Caught signal {}".format(sig))
        if sig == signal.SIGINT:
            bridge.stop()
            sys.exit(0)

        if sig == signal.SIGHUP:
            logger.info("SIGHUP detected, reloading config and restarting daemon")
            bridge.stop()

    signal.signal(signal.SIGINT, signal_handler)
    bridge.run()


if __name__ == "__main__":
    while True:
        run()
