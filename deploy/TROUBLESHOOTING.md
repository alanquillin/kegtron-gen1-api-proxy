# Troubleshooting

## Service won't start

```bash
# Check logs for errors
sudo journalctl -u kegtron-api -n 50

# Verify permissions
sudo chown -R :kegtron /opt/kegtron-gen1-api-proxy

# Test manually
sudo -u kegtron /opt/kegtron-gen1-api-proxy/entrypoint.sh
```

## Bluetooth scanner not finding devices

```bash
# Check Bluetooth service
sudo systemctl status bluetooth

# Restart Bluetooth
sudo systemctl restart bluetooth

# Scan manually
sudo hcitool lescan
```

## Permission denied errors

```bash
# Ensure kegtron user has necessary permissions
sudo usermod -a -G bluetooth kegtron
sudo setcap 'cap_net_raw,cap_net_admin+eip' $(which python3)
```