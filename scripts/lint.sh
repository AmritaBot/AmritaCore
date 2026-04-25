#!/bin/bash
# Lint Python code using ruff
# Usage: ./scripts/lint.sh [--fix]

set -e

cd "$(dirname "$0")/.."

# Default to check mode (no fix)
FIX_FLAG=""

# Parse arguments
for arg in "$@"; do
    if [ "$arg" = "--fix" ]; then
        FIX_FLAG="--fix"
    fi
done

echo "Linting Python code with ruff..."

# Define directories to lint
DIRECTORIES=(
    "src/"
    "tests/"
    "demo/"
    "scripts/"
)

if [ -n "$FIX_FLAG" ]; then
    echo "Fixing lint issues..."
    uv run ruff check $FIX_FLAG "${DIRECTORIES[@]}"
    echo "Lint issues fixed successfully!"
else
    echo "Checking for lint issues..."
    uv run ruff check "${DIRECTORIES[@]}"
    echo "All checks passed!"
    echo "Lint complete!"
fi