import json
import logging
import os
import subprocess
from ssl import VerifyMode

import toml

from wlanpi_mqtt_bridge.MQTTBridge.structures import BridgeConfig, TLSConfig
from wlanpi_mqtt_bridge.MQTTBridge.Utils import get_default_gateways

logger = logging.getLogger()


def confirm_prompt(question: str) -> bool:
    reply = None
    while reply not in ("y", "n"):
        reply = input(f"{question} (y/n): ").lower()
    return reply == "y"


def get_config(filepath) -> BridgeConfig:
    # Not the most elegant way to do this, but it's excruciatingly clear
    # how it works during development.
    # TODO: Refine this.
    config = {}
    if os.path.exists(filepath):
        config = toml.load(filepath)

    mqtt_config = config.get("MQTT", {})
    mqtt_server = mqtt_config.get("server", "<gateway>")
    mqtt_port = mqtt_config.get("port", 1883)

    if mqtt_server in ["<gateway>", "", None]:
        mqtt_server = get_default_gateways()["eth0"]

    eth0_res = subprocess.run(
        "jc ifconfig eth0", capture_output=True, text=True, shell=True
    )

    eth0_data = json.loads(eth0_res.stdout)[0]
    eth0_mac = eth0_data["mac_addr"]

    # TLS configuration
    # logger.debug("Checking TLS data")
    tls_config = None
    tls_data = config.get("MQTT_TLS", {})
    # logger.debug(tls_data)
    if tls_data and tls_data.get("use_tls", False) == True:
        tls_config = TLSConfig(
            ca_certs=tls_data.get("ca_certs", None),
            certfile=tls_data.get("certfile", None),
            keyfile=tls_data.get("keyfile", None),
            cert_reqs=(
                VerifyMode(tls_data.get("cert_reqs", None))
                if tls_data.get("cert_reqs", None)
                else None
            ),
            tls_version=(
                tls_data.get("tls_version", None)
                if tls_data.get("tls_version", None)
                else None
            ),
            ciphers=(tls_data.get("ciphers", None)),
            keyfile_password=tls_data.get("keyfile_password", None),
        )

    return BridgeConfig(
        mqtt_server, mqtt_port, identifier=eth0_mac, tls_config=tls_config
    )
