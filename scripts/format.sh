#!/usr/bin/env bash
cd "$(dirname "$0")"/../ || exit 1
set -x

autoflake --remove-all-unused-imports --recursive --remove-unused-variables --in-place wlanpi_mqtt_bridge --exclude=__init__.py
black wlanpi_mqtt_bridge
isort wlanpi_mqtt_bridge