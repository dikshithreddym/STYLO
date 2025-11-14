#!/bin/bash

# Build script for Render
# This script runs during the build phase

echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed successfully!"
