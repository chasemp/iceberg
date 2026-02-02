#!/bin/bash
# Simple HTTP server for local SPA testing
cd "$(dirname "$0")"
echo "🌐 Starting local SPA server at http://localhost:8000"
echo "Press Ctrl+C to stop"
python3 -m http.server 8000
