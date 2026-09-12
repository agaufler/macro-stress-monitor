#!/bin/bash
cd "$(dirname "$0")"

echo "==========================================="
echo "  MARKET DIVERGENCE DASHBOARD LAUNCHER"
echo "==========================================="
echo ""
echo "Fetching fresh market data..."
python3 fetch_data.py
echo ""
echo "Opening dashboard in Chrome..."
open -a "Google Chrome" "http://localhost:8001/market-divergence-monitor.html"
echo ""
echo "Server running at http://localhost:8001"
echo "Close this window to stop the server."
echo "==========================================="
python3 -m http.server 8001
