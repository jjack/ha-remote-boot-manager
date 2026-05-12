#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

echo "Installing requirements..."
python3 -m pip install --upgrade pip
python3 -m pip install --requirement requirements_dev.txt

echo "Installing pre-commit hooks..."
pre-commit install
