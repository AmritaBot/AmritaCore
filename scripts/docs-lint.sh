#!/bin/bash

# AmritaCore Documentation Lint Script
# Uses Prettier to format documentation files
# Usage: ./scripts/docs-lint.sh [--fix]

set -e

# Check if prettier is available
if ! command -v prettier &> /dev/null; then
    echo "Error: prettier is not installed."
    echo "Please install it with: npm install -g prettier"
    echo "Or ensure it's available in your project dependencies."
    exit 1
fi

# Default to check mode (no fix)
FIX_FLAG=""

# Parse arguments
for arg in "$@"; do
    if [ "$arg" = "--fix" ]; then
        FIX_FLAG="--write"
    fi
done

echo "Linting documentation files with Prettier..."

# Collect documentation files to lint with a single, simple approach
FILES_TO_LINT=()
while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find docs -name "*.md" -type f -print0 2>/dev/null || true)

while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find docs -name "*.mts" -type f -print0 2>/dev/null || true)

while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find docs -name "*.ts" -type f -print0 2>/dev/null || true)

while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find docs -name "*.json" -type f -print0 2>/dev/null || true)

while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find readmes -name "*.md" -type f -print0 2>/dev/null || true)

while IFS= read -r -d '' file; do
    FILES_TO_LINT+=("$file")
done < <(find . -maxdepth 1 -name "README.md" -type f -print0 2>/dev/null || true)

# Remove duplicates and sort
mapfile -t UNIQUE_FILES < <(printf '%s\n' "${FILES_TO_LINT[@]}" | sort -u)

if [ ${#UNIQUE_FILES[@]} -eq 0 ]; then
    echo "No documentation files found to lint."
    exit 0
fi

echo "Found ${#UNIQUE_FILES[@]} files to process."

# Run prettier
if [ -n "$FIX_FLAG" ]; then
    echo "Fixing formatting issues..."
    prettier $FIX_FLAG "${UNIQUE_FILES[@]}"
    echo "Documentation formatting fixed successfully!"
else
    echo "Checking formatting..."
    if prettier --check "${UNIQUE_FILES[@]}"; then
        echo "All documentation files are properly formatted! ✓"
    else
        echo "Some files have formatting issues. Run with --fix to auto-fix them."
        exit 1
    fi
fi