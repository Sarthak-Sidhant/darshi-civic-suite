#!/bin/bash

# Build Quartz documentation and copy to frontend static directory
# This script should be run from the project root

set -e

echo "Building Quartz documentation..."
cd docs-quartz
npx quartz build --output ../frontend/static/docs

echo "Documentation built successfully!"
echo "Docs will be available at /docs/* when you run the frontend"
