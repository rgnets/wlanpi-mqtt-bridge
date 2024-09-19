import logging
from typing import Optional, Union

from wlanpi_mqtt_bridge.MQTTBridge.structures import Route

REST_VERBS = ['GET', "PUT", "POST", "PATCH", "DELETE"]

TopicNodePath = list[str]
TopicReplacements = list[tuple[str,str]]

class TopicNode:
    def __init__(
            self,
            name: str,
            rest: Optional[TopicNodePath] = None,
            dynamic: bool = False,
            route: Optional[Route] = None,
            parent: Optional['TopicNode'] = None,
    ):
        self.name = name
        self.dynamic = dynamic
        self.parent = parent
        self.route : Optional[Route] = None
        rest = rest or []

        self.logger = logging.getLogger(f"{__name__}:{'/'.join(self.get_my_route_path())}")
        self.logger.setLevel(logging.DEBUG)

        # Children of the node
        self.static_children: dict[str,TopicNode] = {}
        self.dynamic_children: list[TopicNode] = []

        self.known_routes: dict[str, tuple[TopicNodePath,TopicNode]] = {}

        if rest:
            self.add_child(rest[0],rest[1:] if len(rest)>1 else None, route)
        else:
            if name.upper() in REST_VERBS:
                self.route = route
                self.register_route_path(self.get_my_route_path(), self)
        # Update logger with the path we should now have:


    def add_child(self, name, rest: Optional[TopicNodePath], route: Route) -> None:
        # Catch dynamic routes
        if name.startswith("{") and name.endswith("}"):
            found = False
            for node in self.dynamic_children:
                if node.name == name:
                    if rest is not None:
                        node.add_child(rest[0],rest[1:] if len(rest)>1 else None, route=route)
                    found = True
            if not found:
                self.dynamic_children.append(TopicNode(name, rest, route=route, parent=self, dynamic=True))
        # Handle static routes
        else:
            if name in self.static_children:
                if  rest is not None:
                    self.static_children[name].add_child(rest[0], rest[1:] if len(rest) > 1 else None, route=route)
            else:
                self.static_children[name] = TopicNode(name, rest, route=route, parent=self)


    def get_next_matching_node(self, path: TopicNodePath, replacements: Optional[TopicReplacements]=None) -> tuple['TopicNode', TopicReplacements]:
        # Start tracking replacements
        if replacements is None:
            replacements = []
        # If this is the end of the path, this is likely the node we want
        if not path:
            return self, replacements

        current_segment, *rest = path

        # Assume no node matches yet
        found_node = None
        found_replacements: list[tuple[str,str]] = []

        # Try static routes first
        if current_segment in self.static_children:
            found_node, found_replacements = self.static_children[current_segment].get_next_matching_node(rest)

        # Try dynamic nodes
        if not found_node:
            for node in self.dynamic_children:
                self.logger.debug(f"Checking node: {'/'.join(node.get_my_route_path())}")
                if node.matches(current_segment):
                    self.logger.debug("Match!")
                    found_node, additional_found_replacements = node.get_next_matching_node(rest)
                    if found_node:
                        found_replacements = [(node.name, current_segment), *additional_found_replacements]
                        break
        return found_node, found_replacements

    def matches(self, path_segment: str) -> bool:
        self.logger.debug(f"{'/'.join(self.get_my_route_path())} matching against {path_segment}")
        # We'll probably never have this case, but why not cover it?
        if not self.dynamic and self.name == path_segment:
            return True

        # All dynamic nodes are considered "matching" for now until smarter logic happens.
        # Downstream matching will be handled in get_next_matching_node
        if self.dynamic:
            return True
        return False

    def get_route(self, segments: TopicNodePath) -> Union[Route, None]:
        node, replacements = self.get_next_matching_node(path=segments)
        if node and node.route:
            replacement_targets = ['topic', 'response_topic', 'route']
            replaced = {}
            for target in replacement_targets:
                if hasattr(node.route, target):
                    replaced[target] = getattr(node.route, target)
                    for original, replacement in replacements:
                        replaced[target] = replaced[target].replace(original, replacement, 1)

            new_route = node.route.copy_with(**replaced)
            return new_route
        return None

    def get_my_route_path(self) -> TopicNodePath:
        route_path = []
        if self.parent:
            route_path.extend(self.parent.get_my_route_path())
            route_path.append(self.name)
        return route_path

    def register_route_path(self, path: TopicNodePath, node: 'TopicNode' ) -> None:
        if self.parent:
            self.parent.register_route_path(path, node)
        self.known_routes['/'.join(path)] = (path, node)


class TopicMatcher(TopicNode):

    def __init__(self, name: str=''):
        super().__init__(name)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.info("TopicMatcher initialized")

    def add_route(self, route: Route):
        next_part, *rest = route.topic.lstrip('/').split('/')
        self.add_child(next_part, rest, route=route)


    def get_route_from_topic(self, topic: str) -> Union[Route, None]:
        return self.get_route(topic.lstrip('/').split('/'))
