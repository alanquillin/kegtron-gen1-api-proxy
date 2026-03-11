#!/bin/bash

# Installation script for Kegtron API systemd service

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
   echo "Please run as root (use sudo)"
   exit 1
fi

# Create kegtron user if it doesn't exist
if ! id "kegtron" &>/dev/null; then
    echo "Creating kegtron user..."
    useradd -r -s /bin/false kegtron
fi

# Copy service file to systemd directory
echo "Installing systemd service..."
cp kegtron.env ../
echo "{}" > ../../config/kegtron.config.json
cp kegtron-api.service /etc/systemd/system/

# Create directory and set ownership
echo "Setting up application directory..."
chown -R kegtron:kegtron /opt/kegtron-gen1-api-proxy
chmod +x /opt/kegtron-gen1-api-proxy/entrypoint.sh

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. install dependencies: poetry install --no-root"
echo "2. Edit the environment file at /opt/kegtron-gen1-api-proxy/deploy/kegtron.env or /opt/kegtron-gen1-api-proxy/config/kegtron.config.json"
echo "3. Enable the service: sudo systemctl enable kegtron-api"
echo "4. Start the service: sudo systemctl start kegtron-api"
echo "5. Check status: sudo systemctl status kegtron-api"