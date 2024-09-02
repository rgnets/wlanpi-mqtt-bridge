# stdlib imports
import argparse
import json
import logging
import os
import platform
import sys
import signal
import subprocess

from configparser import ConfigParser
from types import FrameType
from typing import Optional, Union

# app imports
from .__version__ import __version__, __description__
from .MQTTBridge.Bridge import Bridge
from .MQTTBridge.structures import BridgeConfig
from .MQTTBridge.Utils import get_default_gateways

logger = logging.getLogger(__name__)
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(encoding="utf-8", level=logging.INFO)

CONFIG_DIR = "/etc/wlanpi-mqtt-bridge"
CONFIG_FILE = "/etc/wlanpi-mqtt-bridge/config.toml"

def setup_parser() -> argparse.ArgumentParser:
    """Set default values and handle arg parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"{__description__} Read the manual with: man wlanpi-core",
    )

    parser.add_argument(
        "--debug", "-d", dest="debug", action="store_true", default=False
    )

    parser.add_argument(
        "--server", "-s", dest="server", action="store", default=None
    )

    parser.add_argument(
        "--port", "-p", dest="port", action="store", default=None
    )
    parser.add_argument(
        "--identifier", dest="identifier", action="store", default=None
    )

    parser.add_argument(
        "--version", "-V", "-v", action="version", version=f"{__version__}"
    )
    return parser


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


def main():
    parser = setup_parser()
    args = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG if args.debug else logging.INFO)

    config = get_config(CONFIG_FILE)

    if args.server is not None:
        config.server = args.server
    if args.port is not None:
        config.port = args.port
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



def init() -> None:
    """Handle main init"""

    # hard set no support for python < v3.9
    if sys.version_info < (3, 9):
        sys.exit(
            "{0} requires Python version 3.9 or higher...\nyou are trying to run with Python version {1}...\nexiting...".format(
                os.path.basename(__file__), platform.python_version()
            )
        )

    if __name__ == "__main__":
        sys.exit(main())


init()