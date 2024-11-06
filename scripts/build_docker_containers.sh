#!/usr/bin/env bash
script_dir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
docker build -t wlanpi-mqtt-bridge-builder $script_dir/../docker/builder