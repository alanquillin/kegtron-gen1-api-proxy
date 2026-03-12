# Kegtron Gen1 API Proxy - Deployment Guide

This guide explains how to deploy the Kegtron Gen1 API Proxy on a Raspberry Pi using systemd services.

## Platform Compatibility

This software is **designed and optimized for Raspberry Pi** running Raspberry Pi OS (Debian-based). The Bluetooth scanning functionality requires a Bluetooth adapter that supports BLE (Bluetooth Low Energy), which is built into Raspberry Pi 3+ models.

**Note for other platforms:** While the API component can run on other Linux systems, the Bluetooth scanner functionality may have limited compatibility outside of Raspberry Pi. The software has been primarily tested on:
- Raspberry Pi 3B+
- Raspberry Pi 4
- Raspberry Pi Zero W (with performance considerations)

## Prerequisites

Before installing, ensure you have the following dependencies installed:

### System Dependencies

```bash
# Update package lists
sudo apt update

# Install Python 3.9+ and development tools
sudo apt install python3 python3-pip python3-venv python3-dev

# Install Bluetooth libraries (required for scanner)
sudo apt install bluetooth bluez libbluetooth-dev

# Install build essentials
sudo apt install build-essential git vim
```

### Poetry Installation

This project uses Poetry for dependency management. Install it using the official installer:

```bash
# Install Poetry to /usr/local/bin (it adds the "/bin")
curl -sSL https://install.python-poetry.org | sudo POETRY_HOME=/usr/local python3 -

# Add Poetry to PATH (add this to ~/.bashrc for permanent effect)
export PATH="$HOME/.local/bin:$PATH"

# Verify installation
poetry --version

# Install Poetry v1.8.5
poetry self update 1.8.5
```

## Deployment Modes

The Kegtron API Proxy supports two deployment configurations:

### 1. Default Mode (Single Service)

**Recommended**

In this mode, both the API and scanner run as a single systemd service:
- ✅ Simplest setup and maintenance
- ✅ Scanner writes directly to the SQLite database
- ✅ Lower resource usage

**Architecture:**

```

[Kegtron Device] --BLE--> [Scanner] --DB--> [SQLite] <--DB-- [API] <-- [Web UI/Clients]
                          └─────────── Single Service ──────────┘
└─────────────────────────────────── Raspberry Pi ─────────────────────────────────────┘

```

### 2. Split Mode (Separate Services)

In this mode, the scanner and API run as separate services:
- ✅ More complex setup and maintenance
- ✅ API can run on a more powerful server
- ✅ Higher resource utilization but better performance for each service

**Architecture:**

```

[Kegtron Device] --BLE--> [Scanner Service] --HTTP--> [API Service] <-- [Web UI/Clients]
└─────────── Scanner Service ─────────────┘           └────────── API Service ─────────┘
└─────────────────────────────────── Raspberry Pi ─────────────────────────────────────┘

```

## Installation

### Step 1: Clone the Repository

```bash
# Clone to the target directory
sudo mkdir /opt/kegtron-gen1-api-proxy
sudo chown $(id -u -n):$(id -u -n) /opt/kegtron-gen1-api-proxy
git clone https://github.com/yourusername/kegtron-gen1-api-proxy.git /opt/kegtron-gen1-api-proxy
cd /opt/kegtron-gen1-api-proxy
```

### Step 2: Install Python Dependencies

```bash
# Install project dependencies using Poetry
cd /opt/kegtron-gen1-api-proxy
poetry install --no-dev --no-root
```

### Step 3: Run Installation Script

For **Default Mode**:

```bash
cd /opt/kegtron-gen1-api-proxy/deploy/default
sudo ./install.sh
```

For **Split Mode** installation:

```bash
cd /opt/kegtron-gen1-api-proxy/deploy/split
sudo ./install.sh
```

### Step 4: Configure Environment Variables

Edit the environment file to match your setup:

```bash
sudo vim deploy/kegtron.env
```

**Important variables to configure:**

- `KEGTRON_PROXY_APP_SECRET_KEY` - Change this to a secure random string
- `KEGTRON_PROXY_AUTH_INITIAL_USER_EMAIL` - set to your email
- `KEGTRON_PROXY_AUTH_INITIAL_USER_PASSWORD` = set an initial password.  You will be able to change this on the profile page later
- **[Split mode only]**`KEGTRON_PROXY_SCANNER_SERVICE_ACCOUNT_API_KEY` A api key that will be used by the API and scanner.  This will be created when then service starts up

### Step 6: Start the Service

```bash
# Enable service to start on boot
sudo systemctl enable kegtron-api

# Start the service
sudo systemctl start kegtron-api

# Check status
sudo systemctl status kegtron-api

# View logs
sudo journalctl -u kegtron-api -f
```

**For Split mode also do the following**

```bash
# Enable scanner service to start on boot
sudo systemctl enable kegtron-scanner

# Start the scanner service
sudo systemctl start kegtron-scanner

# View logs for both services
journalctl -u kegtron-api -u kegtron-scanner -f
```

Default login uses the admin credentials created during installation.

## Bluetooth Permissions

The scanner requires Bluetooth permissions. The service runs as the `kegtron` user, which needs to be in the `bluetooth` group:

```bash
sudo usermod -a -G bluetooth kegtron
```

## Updating

To update to the latest in main or a different branch/tag.  make sure to check the release notes for any changes to the configuration

``` bash
sudo systemctl stop kegtron-api

cd /opt/kegtron-gen1-api-proxy

git checkout main

git pull

git checkout <branch|tag>

sudo chown -R :kegtron /opt/kegtron-gen1-api-proxy

poetry update

sudo systemctl start kegtron-api
```

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
sudo journalctl -u kegtron-api -n 50

# Verify permissions
sudo chown -R :kegtron /opt/kegtron-gen1-api-proxy

# Test manually
sudo -u kegtron /opt/kegtron-gen1-api-proxy/entrypoint.sh
```

### Bluetooth scanner not finding devices

```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Restart Bluetooth
sudo systemctl restart bluetooth

# Scan manually
sudo hcitool lescan
```

### Permission denied errors

```bash
# Ensure kegtron user has necessary permissions
sudo usermod -a -G bluetooth kegtron
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)
```

## Uninstallation

To remove the service:

```bash
# Stop and disable service
sudo systemctl stop kegtron-api
sudo systemctl disable kegtron-api

sudo systemctl stop kegtron-scanner
sudo systemctl disable kegtron-scanner

# Remove service file
sudo rm /etc/systemd/system/kegtron-api.service
sudo rm /etc/systemd/system/kegtron-scanner.service

# Reload systemd
sudo systemctl daemon-reload

# Optionally remove application files
sudo rm -rf /opt/kegtron-gen1-api-proxy
```
