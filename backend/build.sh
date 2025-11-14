#!/bin/bash

# Build script for Render
# This script runs during the build phase

echo "Installing dependencies..."
pip install --upgrade pip

# Install packages individually with prefer-binary flag
echo "Installing core dependencies with binary wheels..."
pip install --prefer-binary fastapi==0.103.0
pip install --prefer-binary uvicorn[standard]==0.23.2
pip install --prefer-binary --only-binary=pydantic-core pydantic==2.4.2 pydantic-core==2.10.1
pip install --prefer-binary pydantic-settings==2.0.3
pip install --prefer-binary cloudinary==1.36.0
pip install --prefer-binary python-dotenv==1.0.0
pip install --prefer-binary sqlalchemy==2.0.23
pip install --prefer-binary psycopg2-binary==2.9.9

echo "Build completed successfully!"
