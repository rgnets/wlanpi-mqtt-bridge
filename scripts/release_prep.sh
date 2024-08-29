#!/bin/sh
cd "$(dirname "$0")" || exit 1

set -x

echo "Updating requirements"
cd ../
pip-compile --extra=dev --output-file=requirements-dev.txt pyproject.toml
pip-compile --output-file=requirements.txt pyproject.toml
cd "$(dirname "$0")" || exit 1

echo "Formatting..."
./format.sh

echo "Linting..."
./lint.sh

echo "Generating manpage... (Have you updated the manpage?)"
./manpage.sh

echo ""