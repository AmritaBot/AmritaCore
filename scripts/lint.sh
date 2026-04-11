#!/bin/bash
# Lint Python code using ruff
set -e

cd "$(dirname "$0")/.."

echo "Linting Python code with ruff..."
uv run ruff check src/ tests/ demo/ scripts/

echo "Lint complete!"