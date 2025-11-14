#!/bin/bash

# Build script for Render
# This script runs during the build phase

echo "Installing dependencies..."
pip install --upgrade pip

# Install packages with binary-only flag to avoid compilation
echo "Installing from requirements.txt (binary packages only)..."
pip install --only-binary=:all: -r requirements.txt || pip install -r requirements.txt

echo "Build completed successfully!"
