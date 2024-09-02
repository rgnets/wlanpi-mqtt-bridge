#!/bin/sh
cd "$(dirname "$0")" || exit 1
echo >&2 "Generating man page using pandoc"
pandoc -s -f markdown-smart -t man ../debian/wlanpi-mqtt-bridge.1.md -o ../debian/wlanpi-mqtt-bridge.1 || exit
echo >&2 "Done. You can read it with:   man ./debian/wlanpi-mqtt-bridge.1"