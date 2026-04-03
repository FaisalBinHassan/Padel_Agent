#!/usr/bin/env bash
# Quick setup: install Python dependencies
set -e

echo "Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Setup complete! Next steps:"
echo ""
echo "  1. (Optional) Copy .env.example to .env and set your NTFY_TOPIC for push notifications:"
echo "     cp .env.example .env && nano .env"
echo ""
echo "  2. Run the notifier:"
echo "     python main.py             # poll every 5 minutes (stops when slot found)"
echo "     python main.py --once      # check once and exit"
echo "     python main.py --interval 60   # check every minute"
echo "     python main.py --keep-going    # keep polling after finding slots"
