#!/usr/bin/env bash
cd "$(dirname "$0")"/../ || exit 1

set -x

mypy wlanpi_mqtt_bridge
black wlanpi_mqtt_bridge --check
isort --check-only wlanpi_mqtt_bridge
flake8 wlanpi_mqtt_bridge