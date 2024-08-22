from requests import JSONDecodeError
from typing import Literal, Callable, Optional
import logging, json


class Route:
    """
    Represents a mapping between a REST API route, REST method, and MQTT topics for its invocation and response.
    """
    def __init__(
            self,
            route: str,
            topic: str,
            response_topic: Optional[str] = None,
            callback: Optional[Callable] = None,
            method: Literal['post', 'patch', 'head', 'options', 'put', 'delete', 'get'] = 'get'
    ):
        self.logger = logging.getLogger(__name__)
        self.route = route
        self.topic = topic
        self.response_topic = response_topic or f"{topic}/response"
        self.method = method
        self.callback = callback or self.default_callback

    def default_callback(self, *args, **kwargs) -> None:
        self.logger.info(
            f"Default do-nothing callback for {self.topic}. You should really define one that does something.")


class MQTTResponse:
    """
    Standardized MQTT response object that contains details on internal failures, REST failures, and the response data.
    Additionally, it tries to parse the response data into JSON but will return the original data in case of failure.
    """
    def __init__(
            self,
            data=None,
            errors: list = None,
            status: Literal['success', 'bridge_error', 'rest_error', 'other_error'] = 'success',
            rest_status: Optional[int] = None,
            rest_reason: Optional[str] = None,
    ):
        self.logger = logging.getLogger(__name__)
        if errors is None:
            self.errors = []
        self.status = status
        self.data = data
        self.rest_status = rest_status
        self.rest_reason = rest_reason

        # Try to parse data into json, but don't fret if we can't.
        if type(data) in ['str', 'bytes', 'bytearray']:
            try:
                self.data = json.loads(data)
            except JSONDecodeError as e:
                self.logger.debug(f"Tried to decode data as JSON but it was not valid: {str(e)}")
                self.logger.debug(data)

    def to_json(self) -> str:
        return json.dumps(
            {i:self.__dict__[i] for i in self.__dict__ if i not in ['logger']},
            default=lambda o: o.__dict__,
            sort_keys=True,
            indent=4
        )
