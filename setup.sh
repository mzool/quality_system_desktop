#!/bin/bash
# Quick Start Script for Quality Management System

echo "=================================="
echo "Quality Management System Setup"
echo "=================================="
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

if [ $? -ne 0 ]; then
    echo "ERROR: Python 3 is not installed!"
    echo "Please install Python 3.10 or higher"
    exit 1
fi

echo ""
echo "Creating virtual environment..."
python3 -m venv env

echo ""
echo "Activating virtual environment..."
source env/bin/activate

echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=================================="
echo "Setup Complete!"
echo "=================================="
echo ""
echo "To run the application:"
echo "  1. Activate virtual environment: source env/bin/activate"
echo "  2. Run application: python main.py"
echo ""
echo "Default login credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "IMPORTANT: Change the default password after first login!"
echo ""
