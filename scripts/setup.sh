#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

echo "Installing pre-commit hooks..."
uv run pre-commit install
