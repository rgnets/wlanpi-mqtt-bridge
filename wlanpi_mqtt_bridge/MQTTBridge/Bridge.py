import json
import logging
import time
from typing import Optional, Union

import paho.mqtt.client as mqtt
import schedule

from wlanpi_mqtt_bridge.MQTTBridge.CoreClient import CoreClient
from wlanpi_mqtt_bridge.MQTTBridge.structures import MQTTResponse, Route
from wlanpi_mqtt_bridge.MQTTBridge.Utils import get_full_class_name


class Bridge:
    __global_base_topic = "wlan-pi/all"

    def __init__(
        self,
        mqtt_server: str = "wi.fi",
        mqtt_port: int = 1883,
        wlan_pi_core_base_url: str = "http://127.0.0.1:31415",
        identifier: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing MQTTBridge")
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.__core_base_url = wlan_pi_core_base_url
        self.__my_base_topic = f"wlan-pi/{identifier}"
        self.__client = mqtt.Client(mqtt.CallbackAPIVersion.API_VERSION2)
        self.__core_client = CoreClient(base_url=self.__core_base_url)

        # Endpoints in the core that should be routinely polled and updated
        # This may go away if we can figure out to do event-based updates
        self.monitored_core_endpoints = ["network_config/ethernet/vlans"]

        # Topics to monitor for changes
        self.topics_of_interest: list[str] = [
            # f"{self.__global_base_topic}/#",
            # f"{self.__my_base_topic}/#"
        ]

        # Holds scheduled jobs from `scheduler` so we can clean them up
        # on exit.
        self.scheduled_jobs: list[schedule.Job] = []

        # Stores the route mappings between MQTT topics and REST endpoints
        self.bridge_routes: dict[str, Route] = dict()

        self.add_routes_from_openapi_definition()

    @staticmethod
    def additional_supported_endpoints():
        """
        Defines a list of additional endpoints supported by this bridge
        itself that are not part of the openapi definition
        :return: []
        """
        return []

    def run(self):
        """
        Run the bridge. This calls the Paho client's `.loop_forever()` method,
        which blocks until the Paho client is disconnected.
        :return:
        """
        self.logger.info("Starting MQTTBridge")

        def on_connect(client, userdata, flags, reason_code, properties) -> None:
            return self.handle_connect(client, userdata, flags, reason_code, properties)

        self.__client.on_connect = on_connect

        def on_message(client, userdata, msg) -> None:
            return self.handle_message(client, userdata, msg)

        self.__client.on_message = on_message

        self.__client.will_set(
            f"{self.__my_base_topic}/status", "Abnormally Disconnected", 1, True
        )
        self.__client.connect(self.mqtt_server, self.mqtt_port, 60)

        # Schedule some tasks with `https://schedule.readthedocs.io/en/stable/`
        # self.scheduled_jobs.append(schedule.every(10).seconds.do(self.publish_periodic_data))

        # Start the MQTT client loop,
        self.__client.loop_start()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def stop(self) -> None:
        """
        Closes the MQTT connection and shuts down any scheduled tasks for a clean exit.
        :return:
        """
        self.logger.info("Stopping MQTTBridge")
        self.__client.publish(f"{self.__my_base_topic}/status", "Disconnected", 1, True)
        self.__client.disconnect()
        self.__client.loop_stop()

        for job in self.scheduled_jobs:
            schedule.cancel_job(job)
            self.scheduled_jobs.remove(job)

    def add_subscription(self, topic) -> bool:
        """
        Adds an MQTT subscription, and tracks it for re-subscription on reconnect
        :param topic: The MQTT topic to subscribe to
        :return: Whether the subscription was successfully added
        """
        if topic not in self.topics_of_interest:
            result, mid = self.__client.subscribe(topic)
            self.topics_of_interest.append(topic)
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

        # Publish our current API definition to our own topic:
        self.logger.debug("Telling them a little about ourselves.")
        openapi_definition = self.__core_client.get_openapi_definition()
        client.publish(
            f"{self.__my_base_topic}/openapi", json.dumps(openapi_definition), 1, True
        )

        self.logger.info("Subscribing to topics of interest.")
        # Subscribe to the topics we're going to care about.
        for topic in self.topics_of_interest:
            self.logger.debug(f"Subscribing to {topic}")
            client.subscribe(topic)

        # Once we're ready, announce that we're connected:
        client.publish(f"{self.__my_base_topic}/status", "Connected", 1, True)

        # Now do the first round of periodic data:
        self.publish_periodic_data()

    def publish_periodic_data(self) -> None:
        # self.__client.publish()
        self.logger.info("Publishing periodic data.")
        for endpoint in self.monitored_core_endpoints:
            self.logger.debug(f"Publishing '{endpoint}'")
            response = self.__core_client.get_current_path_data(endpoint)
            self.__client.publish(
                f"{self.__my_base_topic}/{endpoint}/current", json.dumps(response)
            )

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

        if msg.topic in self.bridge_routes.keys():
            route = self.bridge_routes[msg.topic]

            try:
                response = self.__core_client.execute_request(
                    method=route.method,
                    path=route.route,
                    data=(
                        json.loads(msg.payload)
                        if msg.payload is not None and msg.payload not in ["", b""]
                        else None
                    ),
                )
                mqtt_response = MQTTResponse(
                    status="success" if response.ok else "rest_error",
                    rest_status=response.status_code,
                    rest_reason=response.reason,
                    data=response.text,
                )
                route.callback(
                    client=client,
                    topic=route.response_topic,
                    message=mqtt_response.to_json(),
                )
            except Exception as e:
                self.logger.error(
                    f"Exception while handling message on topic '{msg.topic}'",
                    exc_info=e,
                )
                client.publish(
                    route.response_topic,
                    MQTTResponse(
                        status="bridge_error",
                        errors=[[get_full_class_name(e), str(e)]],
                    ).to_json(),
                )

        else:
            client.publish(
                f"{msg.topic}/response",
                MQTTResponse(
                    status="bridge_error",
                    errors=[
                        [
                            "NoBridgeRouteFound",
                            "No route found for topic  '{msg.topic}'",
                        ]
                    ],
                ).to_json(),
            )
            self.logger.warning(f"No route found for topic '{msg.topic}'")

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
            openapi_definition = self.__core_client.get_openapi_definition()

        for uri, action in openapi_definition["paths"].items():
            for method, definition in action.items():
                topic = f"{uri}/{method}"
                # Add route to respond to our own topics
                self.add_route(
                    Route(
                        route=uri,
                        topic=f"{self.__my_base_topic}{topic}",
                        method=method,
                        callback=self.default_callback,
                    )
                )

                # Add route to respond to global topics, but respond on our own.
                self.add_route(
                    Route(
                        route=uri,
                        topic=f"{self.__global_base_topic}{topic}",
                        response_topic=self.bridge_routes[
                            f"{self.__my_base_topic}{topic}"
                        ].response_topic,
                        method=method,
                        callback=self.default_callback,
                    )
                )

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

    def __enter__(self) -> object:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()
