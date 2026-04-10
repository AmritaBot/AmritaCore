#!/bin/bash
# Run all quality checks: format, lint, type check, and tests
set -e

cd "$(dirname "$0")/.."

echo "Running comprehensive quality checks..."

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please run './scripts/init_venv.sh' first."
    exit 1
fi

echo "1. Formatting code..."
./scripts/format.sh

echo "2. Linting code..."
./scripts/lint.sh

echo "3. Type checking..."
./scripts/typecheck.sh

echo "4. Running tests..."
./scripts/run_test.sh

echo "All quality checks passed! 🎉"