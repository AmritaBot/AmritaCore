#!/bin/bash
# Run tests with coverage and generate reports
set -e

cd "$(dirname "$0")/.."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please run './scripts/init_venv.sh' first."
    exit 1
fi

# Default test directory
TEST_DIR="tests/"

# Parse command line arguments
if [ $# -gt 0 ]; then
    TEST_DIR="$1"
    if [ ! -d "$TEST_DIR" ]; then
        echo "Error: Test directory '$TEST_DIR' does not exist."
        exit 1
    fi
fi

echo "Running tests in $TEST_DIR with coverage..."

uv run pytest "$TEST_DIR" \
    --cov=src/amrita_core \
    --cov-report=term-missing \
    --cov-report=xml \
    --junitxml=test-results.xml \
    -v

echo "Tests completed! Coverage report generated."