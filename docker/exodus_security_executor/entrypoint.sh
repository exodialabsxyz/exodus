#!/bin/bash
set -e

# Create the socket directory if it doesn't exist
mkdir -p /tmp/exodus

# Print startup message
echo "========================================="
echo "  Exodus Security Executor Container"
echo "========================================="
echo "Starting exodus-server..."
echo ""

# Execute exodus-server in the foreground
exec exodus-server

