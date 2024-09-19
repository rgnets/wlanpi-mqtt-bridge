# stdlib imports
import argparse
import logging
import os
import platform
import sys
import signal

from types import FrameType
from typing import Optional, Union

# app imports
from .__version__ import __version__, __description__
from .MQTTBridge.Bridge import Bridge

from .utils import get_config

logger = logging.getLogger(__name__)
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(encoding="utf-8", level=logging.INFO)

CONFIG_DIR = "/etc/wlanpi-mqtt-bridge"
CONFIG_FILE = "/etc/wlanpi-mqtt-bridge/config.toml"

def setup_parser() -> argparse.ArgumentParser:
    """Set default values and handle arg parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"{__description__} Read the manual with: man wlanpi-mqtt-bridge",
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