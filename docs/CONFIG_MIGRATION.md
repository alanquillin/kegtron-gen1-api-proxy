# Configuration Migration Guide

## Migrating from Dual-Config to Unified Config (v2.0)

This guide helps you migrate from the old dual configuration setup (separate `api.default.json` and `scanner.default.json`) to the new unified configuration in `default.json`.

### Overview of Changes

**Before (v1.x):**
- Two separate config files: `api.default.json` and `scanner.default.json`
- Scanner and API ran as separate processes
- Different environment variables for each component

**After (v2.0):**
- Single unified config file: `default.json`
- Scanner and API run in a single process
- Unified environment variables with `KEGTRON_PROXY_` prefix

### Step-by-Step Migration

#### 1. Backup Your Current Configuration

```bash
# Create a backup of your existing configs
cp config/api.default.json config/api.default.json.backup
cp config/scanner.default.json config/scanner.default.json.backup
cp config/custom.json config/custom.json.backup  # if you have custom overrides
```

#### 2. Merge Configuration Files

The new `default.json` combines settings from both files. Here's the mapping:

##### From `api.default.json`:
```json
// Old location → New location
"api.host" → "api.host"
"api.port" → "api.port"  // Default changed from 5000 to 8080
"api.cookies" → "api.cookies"
"auth" → "auth"
"logging" → "logging"  // Merged with scanner logging
```

##### From `scanner.default.json`:
```json
// Old location → New location
"proxy" → "proxy"
"force_device_update_after_sec" → "scanner.force_device_update_after_sec"
"logging.levels" → "logging.levels"  // Merged with API logging
```

##### New Settings:
```json
{
  "scanner": {
    "enabled": true,  // Enable/disable scanner
    "backend": "db"   // "db" or "api" - where scanner writes data
  }
}
```

#### 3. Update Environment Variables

Replace old environment variables with new unified ones:

| Old Variable | New Variable | Notes |
|-------------|--------------|-------|
| `KEGTRON_API_PORT` | `KEGTRON_PROXY_API_PORT` | Default changed to 8080 |
| `KEGTRON_API_HOST` | `KEGTRON_PROXY_API_HOST` | Same values |
| `KEGTRON_API_LOG_LEVEL` | `KEGTRON_PROXY_LOG_LEVEL` | Now controls both components |
| `KEGTRON_SCANNER_LOG_LEVEL` | `KEGTRON_PROXY_SCANNER_LOG_LEVEL` | Scanner-specific override |
| `KEGTRON_SCANNER_PROXY_PORT` | `KEGTRON_PROXY_PROXY_PORT` | For scanner API backend |
| `KEGTRON_SCANNER_PROXY_ENABLED` | `KEGTRON_PROXY_SCANNER_BACKEND` | Set to "api" to use API backend |

#### 4. Update Docker Compose / Systemd Services

##### Docker Compose Example:

**Before:**
```yaml
services:
  api:
    image: kegtron-api
    command: python src/api.py
    environment:
      - KEGTRON_API_PORT=5000
      - KEGTRON_API_LOG_LEVEL=INFO
    
  scanner:
    image: kegtron-scanner
    command: python src/scan.py
    environment:
      - KEGTRON_SCANNER_LOG_LEVEL=INFO
      - KEGTRON_SCANNER_PROXY_ENABLED=true
```

**After:**
```yaml
services:
  kegtron:
    image: kegtron-proxy
    command: python src/app.py
    environment:
      - KEGTRON_PROXY_API_PORT=8080
      - KEGTRON_PROXY_LOG_LEVEL=INFO
      - KEGTRON_PROXY_SCANNER_ENABLED=true
      - KEGTRON_PROXY_SCANNER_BACKEND=db
```

##### Systemd Service Example:

**Before:**
```ini
# /etc/systemd/system/kegtron-api.service
[Service]
ExecStart=/usr/bin/python3 /opt/kegtron/src/api.py
Environment="KEGTRON_API_PORT=5000"

# /etc/systemd/system/kegtron-scanner.service
[Service]
ExecStart=/usr/bin/python3 /opt/kegtron/src/scan.py
Environment="KEGTRON_SCANNER_PROXY_ENABLED=true"
```

**After:**
```ini
# /etc/systemd/system/kegtron-proxy.service
[Service]
ExecStart=/usr/bin/python3 /opt/kegtron/src/app.py
Environment="KEGTRON_PROXY_API_PORT=8080"
Environment="KEGTRON_PROXY_SCANNER_ENABLED=true"
```

#### 5. Update Custom Configuration

If you have a `custom.json` file with overrides:

1. Review the new structure in `default.json`
2. Update your `custom.json` to match the new paths
3. Remove any obsolete settings

Example `custom.json` migration:
```json
// Before
{
  "api": {
    "port": 3000
  },
  "proxy": {
    "enabled": false
  }
}

// After
{
  "api": {
    "port": 3000
  },
  "scanner": {
    "backend": "db"  // Instead of proxy.enabled=false
  }
}
```

#### 6. Testing Your Migration

1. Start the application with the new config:
   ```bash
   make run-local
   ```

2. Check the health endpoint for scanner status:
   ```bash
   curl http://localhost:8080/api/v1/health
   ```

3. Verify scanner is running:
   ```bash
   curl http://localhost:8080/api/v1/scanner/status
   ```

4. Check logs for any configuration warnings:
   ```bash
   journalctl -u kegtron-proxy -f  # For systemd
   docker logs kegtron -f           # For Docker
   ```

### Rollback Plan

If you need to rollback to the previous version:

1. Restore your backed-up configuration files
2. Revert to the old Docker image/code version
3. Update environment variables back to old format
4. Restart services with old configuration

### Common Issues and Solutions

#### Issue: Port 5000 is in use
**Solution:** The default port changed from 5000 to 8080. Update your reverse proxy or client configurations.

#### Issue: Scanner not detecting devices
**Solution:** Ensure `scanner.enabled` is `true` and check BLE permissions:
```bash
sudo setcap cap_net_raw,cap_net_admin+eip $(which python3)
```

#### Issue: Scanner writing to wrong location
**Solution:** Check `scanner.backend` setting:
- `"db"` - Direct database writes (recommended)
- `"api"` - Write via API (requires `proxy` settings)

#### Issue: Logs are too verbose/quiet
**Solution:** Adjust logging levels:
```bash
export KEGTRON_PROXY_LOG_LEVEL=INFO  # Overall level
export KEGTRON_PROXY_LOGGING_LEVELS_BLEAK=WARNING  # Component-specific
```

### Breaking Changes Summary

1. **Default API port changed from 5000 to 8080**
2. **Single process instead of two** - Update deployment scripts
3. **Config file structure changed** - Review and update custom configs
4. **Environment variable prefixes unified** - Update all `KEGTRON_API_` and `KEGTRON_SCANNER_` to `KEGTRON_PROXY_`

### Need Help?

If you encounter issues during migration:

1. Check the logs for specific error messages
2. Review the [README](../README.md) for updated documentation
3. Open an issue on GitHub with your configuration (sanitized) and error logs