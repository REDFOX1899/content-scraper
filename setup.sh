#!/bin/bash
# Setup script for Content Scraper

echo "=== Content Scraper Setup ==="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file. Please edit it with your API keys."
else
    echo ""
    echo ".env file already exists."
fi

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p data/raw data/processed logs

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your API keys"
echo "2. Activate the virtual environment: source venv/bin/activate"
echo "3. Run the scraper: python main.py scrape --author tim_ferriss --platform blog --max-items 10"
echo ""
