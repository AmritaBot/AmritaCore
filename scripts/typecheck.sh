#!/bin/bash
# Type check Python code using pyright
set -e

cd "$(dirname "$0")/.."

echo "Running type checking with pyright..."
uv run pyright

echo "Type check complete!"