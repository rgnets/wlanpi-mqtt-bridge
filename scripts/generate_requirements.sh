#!/bin/sh
cd "$(dirname "$0")" || exit 1
set -x
cd ../
pip-compile --extra=dev --output-file=requirements-dev.txt pyproject.toml
pip-compile --output-file=requirements.txt pyproject.toml
cd "$(dirname "$0")" || exit 1
