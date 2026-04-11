#!/bin/bash
# Prepare for release: run all checks, build documentation, and clean
set -e

cd "$(dirname "$0")/.."

echo "Preparing for release..."

# Check if uv and npm are available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed. Please run './scripts/init_venv.sh' first."
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js first."
    exit 1
fi

echo "1. Running comprehensive quality checks..."
./scripts/check.sh

echo "2. Building documentation..."
./scripts/docs-build.sh

echo "3. Cleaning unnecessary files..."
./scripts/clean.sh

echo "Release preparation complete! 🚀"
echo "You can now proceed with publishing the package."