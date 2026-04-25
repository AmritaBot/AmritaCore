#!/bin/bash
# Clean build artifacts and caches
set -e

cd "$(dirname "$0")/.."

echo "Cleaning build artifacts and caches..."

# Remove Python cache and coverage files
rm -rf .coverage coverage.xml test-results.xml
rm -rf .pytest_cache/
rm -rf .ruff_cache/

# Remove Python __pycache__ directories recursively
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Remove root build directory (if exists)
rm -rf build/

# Remove VitePress build output
rm -rf docs/.vitepress/dist/

# Remove node_modules cache (optional, uncomment if needed)
# rm -rf node_modules/.cache/

echo "Clean complete!"