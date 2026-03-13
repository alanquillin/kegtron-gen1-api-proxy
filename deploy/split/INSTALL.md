# Split Deployment Mode Setup

![Architecture](../../docs/img/architecture.png)

## Installation

### Step 1: Clone the Repository

```bash
# Clone to the target directory
sudo mkdir /opt/kegtron-gen1-api-proxy
sudo chown $(id -u -n):$(id -u -n) /opt/kegtron-gen1-api-proxy
git clone https://github.com/yourusername/kegtron-gen1-api-proxy.git /opt/kegtron-gen1-api-proxy
```

### Step 2: Install Python Dependencies

```bash
# Install project dependencies using Poetry
cd /opt/kegtron-gen1-api-proxy
poetry install --no-dev --no-root
```

### Step 3: Run Installation Script

```bash
cd /opt/kegtron-gen1-api-proxy/deploy/split
sudo ./install.sh
```

#### Bluetooth Permissions

The scanner requires Bluetooth permissions. The service runs as the `kegtron` user, which needs to be in the `bluetooth` group:

```bash
sudo usermod -a -G bluetooth kegtron
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
- `KEGTRON_PROXY_API_COOKIES_SECURE` - **IMPORTANT**: Set to `false` when running over HTTP (default port 8080). Set to `true` only when using HTTPS/SSL
- **[Split mode only]**`KEGTRON_PROXY_SCANNER_SERVICE_ACCOUNT_API_KEY` A api key that will be used by the API and scanner.  This will be created when then service starts up

### Step 5: Start the Service

```bash
# Enable services to start on boot
sudo systemctl enable kegtron-api
sudo systemctl enable kegtron-scanner

# Start the services
sudo systemctl start kegtron-api
sudo systemctl start kegtron-scanner

# Check statuses
sudo systemctl status kegtron-api kegtron-scanner

# View logs
sudo journalctl -u kegtron-api -u kegtron-scanner -f
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
