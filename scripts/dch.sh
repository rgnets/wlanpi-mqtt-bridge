#!/usr/bin/env bash
docker run -it -v./:/mnt -e"DEBEMAIL=$DEBEMAIL" -e"NAME=$NAME" wlanpi-mqtt-bridge-builder dch "$@"