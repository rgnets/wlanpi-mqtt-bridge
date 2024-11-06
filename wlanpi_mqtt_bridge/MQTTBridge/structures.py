import json
import logging
from ssl import VerifyMode
from typing import Any, Callable, Literal, Optional

from requests import JSONDecodeError

from wlanpi_mqtt_bridge.MQTTBridge.Utils import get_current_unix_timestamp


class Route:
    """
    Represents a mapping between a REST API route, REST method, and MQTT
    topics for its invocation and response.
    """

    def __init__(
        self,
        route: str,
        topic: str,
        response_topic: Optional[str] = None,
        callback: Optional[Callable] = None,
        method: Literal[
            "post", "patch", "head", "options", "put", "delete", "get"
        ] = "get",
    ):
        self.logger = logging.getLogger(__name__)
        self.route = route
        self.topic = topic
        self.response_topic = response_topic or f"{topic}/_response"
        self.method = method
        self.callback = callback or self.default_callback

    # noinspection PyUnusedLocal
    def default_callback(self, *args, **kwargs) -> None:
        self.logger.info(
            f"Default do-nothing callback for {self.topic}. You should really"
            "define one that does something."
        )

    def copy_with(self, **kwargs) -> "Route":
        new_route = Route(
            route=self.route,
            topic=self.topic,
            response_topic=self.response_topic,
            callback=self.callback,
            method=self.method,
        )
        for key, value in kwargs.items():
            if hasattr(new_route, key):
                setattr(new_route, key, value)
        return new_route


class MQTTResponse:
    """
    Standardized MQTT response object that contains details on internal
    failures, REST failures, and the response data. Additionally, it
    tries to parse the response data into JSON but will return the
    original data in case of failure.
    """

    def __init__(
        self,
        data=None,
        errors: Optional[list] = None,
        status: Literal[
            "success", "bridge_error", "rest_error", "other_error"
        ] = "success",
        rest_status: Optional[int] = None,
        rest_reason: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        if errors is None:
            self.errors: list = []
        self.status = status
        self.data = data
        self.rest_status = rest_status
        self.rest_reason = rest_reason
        self.published_at = get_current_unix_timestamp()
        self.is_hydrated_object = False

        # Try to parse data into json, but don't fret if we can't.
        if type(data) in [str, bytes, bytearray]:
            try:
                self.data = json.loads(data)
                self.is_hydrated_object = True
            except (JSONDecodeError,json.decoder.JSONDecodeError) as e:
                self.logger.debug(
                    f"Tried to decode data as JSON but it was not valid: {str(e)}"
                )
                self.logger.debug(data)
        else:
            # We're going to assume in this case it's some kind of
            # JSON-compatible structure.
            self.is_hydrated_object = True

    def to_json(self) -> str:
        return json.dumps(
            {i: self.__dict__[i] for i in self.__dict__ if i not in ["logger"]},
            default=lambda o: o.__dict__,
            # sort_keys=True,
            # indent=4,
        )


class TLSConfig:
    def __init__(
        self,
        ca_certs: Optional[str] = None,
        certfile: Optional[str] = None,
        keyfile: Optional[str] = None,
        cert_reqs: Optional[VerifyMode] = None,
        tls_version: Optional[Any] = None,
        ciphers: Optional[str] = None,
        keyfile_password: Optional[Any] = None,
    ):
        self.ca_certs = ca_certs
        self.certfile = certfile
        self.keyfile = keyfile
        self.cert_reqs = cert_reqs
        self.tls_version = tls_version
        self.ciphers = ciphers
        self.keyfile_password = keyfile_password


class BridgeConfig:
    def __init__(
        self,
        mqtt_server: str,
        mqtt_port: int,
        identifier: str,
        tls_config: Optional[TLSConfig] = None,
    ):
        self.mqtt_server = mqtt_server
        self.mqtt_port = mqtt_port
        self.identifier = identifier
        self.tls_config = tls_config
