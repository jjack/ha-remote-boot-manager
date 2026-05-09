#!/usr/bin/env bash

set -e

cd "$(dirname "$0")/.."

pytest --cov=custom_components.grubstation "$@"
