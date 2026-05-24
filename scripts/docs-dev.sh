#!/bin/bash
# Start VitePress documentation development server
set -e

cd "$(dirname "$0")/.."
cd docs/
echo "Starting VitePress documentation development server..."
npm run docs:dev

echo "Documentation server started!"