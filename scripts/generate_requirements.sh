#!/bin/sh
cd "$(dirname "$0")" || exit 1
set -x
cd ../
pip-compile --verbose --extra=dev --output-file=requirements-dev.txt pyproject.toml
pip-compile --verbose --extra=testing --output-file=testing.txt pyproject.toml
pip-compile --verbose --output-file=requirements.txt pyproject.toml
cd "$(dirname "$0")" || exit 1
