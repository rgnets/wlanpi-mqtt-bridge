#!/bin/env python3
import logging, subprocess, json
from MQTTBridge.Bridge import Bridge

logger = logging.getLogger(__name__)
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig( encoding='utf-8', level=logging.DEBUG)

if __name__ == '__main__':
    eth0_data = json.loads(subprocess.run('jc ifconfig eth0'.split(' '), capture_output=True, text=True).stdout)[0]
    eth0_mac = eth0_data['mac_addr']
    bridge = Bridge(
        mqtt_server="rxg.ketchel.xyz",
        mqtt_port=1884,
        identifier=eth0_mac
    )

    bridge.run()
