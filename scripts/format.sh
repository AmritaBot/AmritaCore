#!/bin/bash
# Format Python code using ruff
set -e

cd "$(dirname "$0")/.."

echo "Formatting Python code with ruff..."
uv run ruff format src/ tests/ demo/ scripts/

echo "Format complete!"