#!/bin/bash
# Initialize virtual environment and install dependencies using uv
set -e

cd "$(dirname "$0")/.."

echo "Initializing virtual environment with uv..."
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please install uv first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

uv init
uv sync

echo "Virtual environment initialized successfully!"
echo "You can now run other scripts or use 'uv run' to execute commands."