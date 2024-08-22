import time
from typing import Optional
import logging, json, schedule

import paho.mqtt.client as mqtt

from MQTTBridge.CoreClient import CoreClient


class Bridge:
    __global_base_topic = "wlan-pi/all"

    def __init__(
            self,
            mqtt_server: str = "wi.fi",
            mqtt_port: int = 1883,
            wlan_pi_core_api_url : str = "http://127.0.0.1:31415/api/v1",
            identifier: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing MQTTBridge")
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.__api_url = wlan_pi_core_api_url
        self.__openapi_def_path = f"{self.__api_url}/openapi.json"
        self.__my_base_topic = f"wlan-pi/{identifier}"
        self.__client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.__core_client = CoreClient(self.__api_url)

        # Endpoints in the core that should be routinely polled and updated
        # This may go away if we can figure out to do event-based updates
        self.monitored_core_endpoints = [
            'network_config/ethernet/vlans'
        ]

        # Topics to monitor for changes
        self.topics_of_interest = [
            f"{self.__global_base_topic}/#",
            f"{self.__my_base_topic}/#"
        ]

        # Holds scheduled jobs from `scheduler` so we can clean them up on exit.
        self.scheduled_jobs = []

    def additional_supported_endpoints(self):
        """
        Defines a list of additional endpoints supported by this bridge itself that are not part of the openapi definition
        :return: []
        """
        return []

    def run(self):
        """
        Run the bridge. This calls the Paho client's `.loop_forever()` method, which blocks until the Paho client is disconnected.
        :return:
        """
        self.logger.info("Starting MQTTBridge")
        self.__client.on_connect = lambda client, userdata, flags, reason_code, properties: self.handle_connect(client, userdata, flags, reason_code, properties)
        self.__client.on_message = lambda client, userdata, msg: self.handle_message(client, userdata, msg)

        self.__client.will_set(f"{self.__my_base_topic}/status", "Abnormally Disconnected", 1, True)
        self.__client.connect(self.mqtt_server, self.mqtt_port, 60)

        # Blocking call that processes network traffic, dispatches callbacks and
        # handles reconnecting.
        # Other loop*() functions are available that give a threaded interface and a
        # manual interface.
        #self.__client.loop_forever()

        # Schedule some tasks with `https://schedule.readthedocs.io/en/stable/`
        self.scheduled_jobs.append(schedule.every(10).seconds.do(self.publish_periodic_data))

        # Start the MQTT client loop,
        self.__client.loop_start()

        while True:
            schedule.run_pending()
            time.sleep(1)

    def stop(self):
        self.logger.info("Stopping MQTTBridge")
        self.__client.publish(f"{self.__my_base_topic}/status", "Disconnected", 1, True)
        self.__client.disconnect()
        self.__client.loop_stop()

        for job in self.scheduled_jobs:
            schedule.cancel_job(job)
            self.scheduled_jobs.remove(job)

    def handle_connect(self, client, userdata, flags, reason_code, properties):
        """
        Handles the connect event from Paho. This is called when a connection has been established and we are ready to send messages.
        :param client: An instance of Paho's Client class that is used to send and receive messages
        :param userdata:
        :param flags:
        :param reason_code: The reason code that was received from the MQTT broker
        :param properties:
        :return:
        """
        self.logger.info(f"Connected with result code {reason_code}.")

        # Publish our current API definition to our own topic:
        self.logger.debug(f"Telling them a little about ourselves.")
        openapi_definition = self.__core_client.get_openapi_definition()
        client.publish(f"{self.__my_base_topic}/openapi", json.dumps(openapi_definition), 1, True)

        self.logger.info(f"Subscribing to topics of interest.")
        # Subscribe to the topics we're going to care about.
        for topic in self.topics_of_interest:
            self.logger.debug(f"Subscribing to {topic}")
            client.subscribe(topic)

        # Once we're ready, announce that we're connected:
        client.publish(f"{self.__my_base_topic}/status", "Connected", 1, True)

        # Now do the first round of periodic data:
        self.publish_periodic_data()

    def publish_periodic_data(self):
        # self.__client.publish()
        self.logger.info(f"Publishing periodic data.")
        for endpoint in self.monitored_core_endpoints:
            self.logger.debug(f"Publishing '{endpoint}'")
            response = self.__core_client.get_current_path_data(endpoint)
            self.__client.publish(f"{self.__my_base_topic}/{endpoint}/current", json.dumps(response))


    def handle_message(self, client, userdata, msg):
        self.logger.debug(f"Received message on topic '{msg.topic}': {str(msg.payload)}")

        # Watch for topics that match our base topic or the global one:
        if msg.topic.startswith(self.__my_base_topic) and msg.topic.endswith("/set"):
            item_path = msg.topic.removeprefix(f"{self.__my_base_topic}/").removesuffix("/set")
            item_url = f"{self.__api_url}/{item_path}"

            result = self.__core_client.create_path(item_url, json.loads(msg.payload))
            client.publish(f"{self.__my_base_topic}/{item_path}/result", json.dumps(result))


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()