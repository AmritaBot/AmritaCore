#!/bin/bash
# Format Python code using ruff
# Usage: ./scripts/format.sh [--check]

set -e

cd "$(dirname "$0")/.."

# Default to fix mode (write changes)
CHECK_FLAG=""

# Parse arguments
for arg in "$@"; do
    if [ "$arg" = "--check" ]; then
        CHECK_FLAG="--check"
    fi
done

echo "Formatting Python code with ruff..."

# Define directories to format
DIRECTORIES=(
    "src/"
    "tests/"
    "demo/"
    "scripts/"
)

if [ -n "$CHECK_FLAG" ]; then
    echo "Checking code formatting..."
    uv run ruff format $CHECK_FLAG "${DIRECTORIES[@]}"
    echo "Code formatting check completed! ✓"
else
    echo "Fixing code formatting..."
    uv run ruff format "${DIRECTORIES[@]}"
    echo "Code formatting fixed successfully!"
fi