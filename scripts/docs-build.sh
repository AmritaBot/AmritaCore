#!/bin/bash
# Build VitePress documentation site
set -e

cd "$(dirname "$0")/.."
cd docs/
echo "Building VitePress documentation site..."
npm run docs:build

echo "Documentation build complete!"