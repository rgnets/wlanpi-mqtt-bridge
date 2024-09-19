import argparse
import json
import logging
import signal
import sys
import time
from types import FrameType
from typing import Optional, Union

import paho.mqtt.client as mqtt

from wlanpi_mqtt_bridge.MQTTBridge.CoreClient import CoreClient
from wlanpi_mqtt_bridge.MQTTBridge.TopicMatcher import TopicMatcher
from wlanpi_mqtt_bridge.MQTTBridge.structures import Route
from wlanpi_mqtt_bridge.utils import get_config

logger = logging.getLogger(__name__)
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
logging.basicConfig(encoding="utf-8", level=logging.DEBUG)

CONFIG_DIR = "/etc/wlanpi-mqtt-bridge"
CONFIG_FILE = "/etc/wlanpi-mqtt-bridge/config.toml"

def setup_parser() -> argparse.ArgumentParser:
    """Set default values and handle arg parser"""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=f"An overbuilt test client for wlanpi mqtt bridge",
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
    return parser

class TestClient:
    __global_base_topic = "wlan-pi/all"

    def __init__(
        self,
        mqtt_server: str = "wi.fi",
        mqtt_port: int = 1883,
        wlan_pi_core_base_url: str = "http://127.0.0.1:31415",
        identifier: Optional[str] = None,
    ):
        self.route_matcher :TopicMatcher = TopicMatcher()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing MQTTBridge")
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.core_base_url = wlan_pi_core_base_url
        self.my_base_topic = f"wlan-pi/{identifier}"
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.core_client = CoreClient(base_url=self.core_base_url)

        # Topics to monitor for changes
        self.topics_of_interest: list[str] = [
            # f"{self.__global_base_topic}/#",
            # f"{self.__my_base_topic}/#"
        ]

        # Stores the route mappings between MQTT topics and REST endpoints
        self.bridge_routes: dict[str, Route] = dict()

    def __enter__(self) -> 'TestClient':
        self.run()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()


    def run(self):
        """
        Run the bridge. This calls the Paho client's `.loop_forever()` method,
        which blocks until the Paho client is disconnected.
        :return:
        """
        self.logger.info("Starting TestClient")

        def on_connect(client, userdata, flags, reason_code, properties) -> None:
            return self.handle_connect(client, userdata, flags, reason_code, properties)

        self.mqtt_client.on_connect = on_connect

        def on_message(client, userdata, msg) -> None:
            return self.handle_message(client, userdata, msg)

        self.mqtt_client.on_message = on_message
        self.logger.info(f"Connecting to MQTT server at {self.mqtt_server}:{self.mqtt_port}")
        self.mqtt_client.connect(self.mqtt_server, self.mqtt_port, 60)

        # Start the MQTT client loop,
        self.mqtt_client.loop_start()

        # while True:
        #     time.sleep(1)

    def stop(self) -> None:
        """
        Closes the MQTT connection and shuts down any scheduled tasks for a clean exit.
        :return:
        """
        self.logger.info("Stopping TestClient")
        self.mqtt_client.disconnect()
        self.mqtt_client.loop_stop()

    def add_subscription(self, topic) -> bool:
        """
        Adds an MQTT subscription, and tracks it for re-subscription on reconnect
        :param topic: The MQTT topic to subscribe to
        :return: Whether the subscription was successfully added
        """
        if topic not in self.topics_of_interest:
            result, mid = self.mqtt_client.subscribe(topic)
            # self.topics_of_interest.append(topic)
            self.logger.debug(f"Sub result: {str(result)}")
            return result == mqtt.MQTT_ERR_SUCCESS
        else:
            return True

    # noinspection PyUnusedLocal
    def handle_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """
        Handles the connect event from Paho. This is called when a connection
        has been established, and we are ready to send messages.
        :param client: An instance of Paho's Client class that is used to send
         and receive messages
        :param userdata:
        :param flags:
        :param reason_code: The reason code that was received from the MQTT
         broker
        :param properties:
        :return:
        """
        self.logger.info(f"Connected with result code {reason_code}.")
        self.add_routes_from_openapi_definition()

        self.logger.info("Subscribing to topics of interest.")
        # Subscribe to the topics we're going to care about.
        for topic in self.topics_of_interest:
            self.logger.debug(f"Subscribing to {topic}")
            client.subscribe(topic)

    def handle_message(self, client, userdata, msg) -> None:
        """
        Handles all incoming MQTT messages, usually dispatching them onward
        to the REST API
        :param client:
        :param userdata:
        :param msg:
        :return:
        """
        self.logger.debug(
            f"Received message on topic '{msg.topic}': {str(msg.payload)}"
        )
        self.logger.debug(f"User Data: {str(userdata)}")



    def add_routes_from_openapi_definition(
        self, openapi_definition: Optional[dict] = None
    ) -> None:
        """
        Add routes to the bridge based on the open api definition.
        :param openapi_definition: The parsed OpenAPI definition. If not
            provided, the OpenAPI definition will be retrieved from the CoreClient.
        :return: None
        """
        if openapi_definition is None:
            openapi_definition = self.core_client.get_openapi_definition()

        for uri, action in openapi_definition["paths"].items():
            for method, definition in action.items():
                topic = f"{uri}/{method}"
                # Add route to respond to our own topics
                my_route = Route(
                    route=uri,
                    topic=f"{self.my_base_topic}{topic}",
                    method=method,
                    callback=self.default_callback,
                )
                self.add_route(my_route)
                self.route_matcher.add_route(my_route)
                self.logger.debug("New OAPI route: ", my_route.__dict__)
                # Add route to respond to global topics, but respond on our own.
                global_route = Route(
                        route=uri,
                        topic=f"{self.__global_base_topic}{topic}",
                        response_topic=my_route.response_topic,
                        method=method,
                        callback=self.default_callback,
                    )
                self.add_route(global_route)
                self.route_matcher.add_route(global_route)
        self.logger.debug("Routes from openapi definition added")
        self.logger.debug(self.bridge_routes)

    def add_route(self, route: Route) -> bool:
        """
        Adds a route to the route lookup table
        :param route: A populated Route object.
        :return: Whether the Route was added to the lookup table.
        """
        if self.add_subscription(route.topic):
            self.bridge_routes[route.topic] = route
            return True
        return False

    def default_callback(self, client, topic, message: Union[str, bytes]) -> None:
        """
        Default callback for sending a REST response on to the MQTT endpoint.
        :param client:
        :param topic:
        :param message:
        :return:
        """
        self.logger.info(f"Default callback. Topic: {topic} Message: {str(message)}")
        client.publish(topic, message)




def main():
    parser = setup_parser()
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.DEBUG)
    config = get_config(CONFIG_FILE)

    if args.server is not None:
        config.server = args.server
    if args.port is not None:
        config.port = args.port

    with TestClient(**config.__dict__) as test_client:
        # noinspection PyUnusedLocal
        def signal_handler(
                sig: Union[int, signal.Signals], frame: Optional[FrameType]
        ) -> None:
            logger.info("Caught signal {}".format(sig))
            if sig == signal.SIGINT:
                test_client.stop()
                sys.exit(0)

            if sig == signal.SIGHUP:
                logger.info("SIGHUP detected, reloading config and restarting daemon")
                test_client.stop()

        signal.signal(signal.SIGINT, signal_handler)


        res = test_client.route_matcher.get_route_from_topic("wlan-pi/dc:a6:32:8e:04:17/api/v1/network/get")
        print(res)


if __name__ == "__main__":
    sys.exit(main())