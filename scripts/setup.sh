#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

echo "installing packages"
export UV_LINK_MODE=copy
uv sync

echo "Installing pre-commit hooks..."
uv run pre-commit install
