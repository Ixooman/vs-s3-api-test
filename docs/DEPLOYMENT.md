# S3 Compatibility Checker - Deployment Guide

This guide provides detailed instructions for deploying and running the S3 Compatibility Checker on various environments, with a focus on Ubuntu 24.04 Linux systems.

## System Requirements

### Minimum Requirements
- **Operating System**: Ubuntu 24.04 LTS (or compatible Linux distribution)
- **Python**: Python 3.8 or higher
- **Memory**: 512 MB RAM (1 GB recommended)
- **Storage**: 100 MB for application + space for test data
- **Network**: Access to your S3-compatible storage endpoint

### Recommended Requirements
- **Memory**: 2 GB RAM for large file testing
- **Storage**: 1 GB free space for comprehensive testing
- **Network**: Low-latency connection to S3 endpoint for accurate performance metrics

## Installation on Ubuntu 24.04

### Step 1: System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3 python3-pip python3-venv git curl

# Verify Python version (should be 3.8+)
python3 --version
```

### Step 2: Create Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/s3-compatibility-checker
sudo chown $USER:$USER /opt/s3-compatibility-checker

# Or use a user directory
mkdir -p ~/s3-compatibility-checker
cd ~/s3-compatibility-checker
```

### Step 3: Download Application Files

If you have the files locally:
```bash
# Copy all application files to the directory
cp /path/to/source/* /opt/s3-compatibility-checker/
cd /opt/s3-compatibility-checker
```

Or if downloading from a repository:
```bash
# Clone from repository (if available)
git clone <repository-url> /opt/s3-compatibility-checker
cd /opt/s3-compatibility-checker
```

### Step 4: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### Step 5: Make Application Executable

```bash
# Make main script executable
chmod +x main.py

# Create symlink for easy access (optional)
sudo ln -sf /opt/s3-compatibility-checker/main.py /usr/local/bin/s3-checker
```

## Configuration Setup

### Step 1: Generate Configuration Template

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Generate configuration template
python main.py --generate-config
```

### Step 2: Configure S3 Endpoint

Edit the generated `config.ini` file:

```bash
nano config.ini
```

Example configuration for local MinIO:
```ini
[connection]
endpoint_url = http://localhost:9000
access_key = minioadmin
secret_key = minioadmin
region = us-east-1
verify_ssl = false
max_retries = 3
```

Example configuration for remote S3-compatible storage:
```ini
[connection]
endpoint_url = http://192.168.10.81
access_key = your-access-key
secret_key = your-secret-key
region = us-east-1
verify_ssl = false
max_retries = 3
```

### Step 3: Validate Configuration

```bash
# Test configuration with a simple connectivity check
python main.py --scope buckets --log-level debug
```

## Running the Application

### Basic Execution

```bash
# Activate virtual environment
source venv/bin/activate

# Run all compatibility checks
python main.py --scope all

# Run specific check categories
python main.py --scope buckets,objects

# Run with detailed logging
python main.py --scope all --log-level debug
```

### Production Execution

```bash
# Run with comprehensive logging and result export
python main.py \
    --scope all \
    --log-level info \
    --log-file /var/log/s3-checker.log \
    --export-results /var/log/s3-checker-results.json
```

## Automated Deployment

### Using systemd Service (Optional)

Create a systemd service for regular compatibility checks:

```bash
# Create service file
sudo nano /etc/systemd/system/s3-checker.service
```

Service file content:
```ini
[Unit]
Description=S3 Compatibility Checker
After=network.target

[Service]
Type=oneshot
User=s3checker
Group=s3checker
WorkingDirectory=/opt/s3-compatibility-checker
Environment=PATH=/opt/s3-compatibility-checker/venv/bin
ExecStart=/opt/s3-compatibility-checker/venv/bin/python main.py --scope all --quiet --export-results /var/log/s3-checker-results.json
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create dedicated user:
```bash
# Create user for the service
sudo useradd -r -s /bin/false -d /opt/s3-compatibility-checker s3checker
sudo chown -R s3checker:s3checker /opt/s3-compatibility-checker
```

Enable and start service:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service
sudo systemctl enable s3-checker.service

# Run service manually
sudo systemctl start s3-checker.service

# Check service status
sudo systemctl status s3-checker.service
```

### Using Cron for Scheduled Checks

```bash
# Edit crontab
crontab -e

# Add entry for daily checks at 2 AM
0 2 * * * /opt/s3-compatibility-checker/venv/bin/python /opt/s3-compatibility-checker/main.py --scope all --quiet --export-results /var/log/s3-checker-$(date +\%Y\%m\%d).json >> /var/log/s3-checker-cron.log 2>&1
```

## Docker Deployment

### Creating Docker Image

Create `Dockerfile`:
```dockerfile
FROM ubuntu:24.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy application files
COPY . /app/

# Create virtual environment and install dependencies
RUN python3 -m venv venv && \
    . venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Make script executable
RUN chmod +x main.py

# Create non-root user
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /app

USER appuser

# Set entry point
ENTRYPOINT ["./venv/bin/python", "main.py"]
```

Build and run Docker image:
```bash
# Build image
docker build -t s3-compatibility-checker .

# Run with mounted config
docker run -v $(pwd)/config.ini:/app/config.ini s3-compatibility-checker --scope all
```

### Docker Compose Setup

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  s3-checker:
    build: .
    volumes:
      - ./config.ini:/app/config.ini:ro
      - ./logs:/app/logs
    command: ["--scope", "all", "--export-results", "logs/results.json"]
    restart: "no"
```

Run with Docker Compose:
```bash
docker-compose up
```

## Network and Security Configuration

### Firewall Configuration

If running on a server with UFW:
```bash
# Allow outbound connections to S3 endpoint
sudo ufw allow out 80
sudo ufw allow out 443
sudo ufw allow out 9000  # For MinIO default port

# If accessing remote endpoints
sudo ufw allow out to <s3-endpoint-ip>
```

### Network Connectivity Testing

```bash
# Test basic connectivity to S3 endpoint
curl -v http://your-s3-endpoint/

# Test with AWS CLI (if available)
aws --endpoint-url http://your-s3-endpoint s3 ls
```

### Security Considerations

1. **Credentials Management**:
   ```bash
   # Secure config file permissions
   chmod 600 config.ini
   
   # Use environment variables for sensitive data (optional)
   export S3_ACCESS_KEY="your-access-key"
   export S3_SECRET_KEY="your-secret-key"
   ```

2. **Log File Security**:
   ```bash
   # Create secure log directory
   sudo mkdir -p /var/log/s3-checker
   sudo chown s3checker:s3checker /var/log/s3-checker
   sudo chmod 750 /var/log/s3-checker
   ```

3. **File Permissions**:
   ```bash
   # Set secure permissions for application directory
   sudo chown -R s3checker:s3checker /opt/s3-compatibility-checker
   sudo chmod -R 750 /opt/s3-compatibility-checker
   sudo chmod 600 /opt/s3-compatibility-checker/config.ini
   ```

## Monitoring and Logging

### Log Rotation Setup

Create logrotate configuration:
```bash
sudo nano /etc/logrotate.d/s3-checker
```

Logrotate configuration:
```
/var/log/s3-checker*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 640 s3checker s3checker
}
```

### Monitoring Script

Create monitoring script:
```bash
#!/bin/bash
# Monitor S3 checker results

RESULT_FILE="/var/log/s3-checker-results.json"
LOG_FILE="/var/log/s3-checker-monitor.log"

if [ -f "$RESULT_FILE" ]; then
    # Extract success rate from results
    SUCCESS_RATE=$(python3 -c "
import json
with open('$RESULT_FILE', 'r') as f:
    data = json.load(f)
    print(data.get('overall_success_rate', 0))
")
    
    echo "$(date): S3 Checker Success Rate: ${SUCCESS_RATE}%" >> $LOG_FILE
    
    # Alert if success rate is below threshold
    if (( $(echo "$SUCCESS_RATE < 90" | bc -l) )); then
        echo "ALERT: S3 compatibility success rate below 90%: ${SUCCESS_RATE}%" | \
        mail -s "S3 Checker Alert" admin@yourdomain.com
    fi
else
    echo "$(date): No S3 checker results found" >> $LOG_FILE
fi
```

## Troubleshooting Deployment Issues

### Common Problems and Solutions

1. **Python Version Issues**:
   ```bash
   # Check Python version
   python3 --version
   
   # Install specific Python version if needed
   sudo apt install python3.9 python3.9-venv python3.9-pip
   ```

2. **Permission Errors**:
   ```bash
   # Fix ownership
   sudo chown -R $USER:$USER /opt/s3-compatibility-checker
   
   # Fix permissions
   chmod +x main.py
   chmod 600 config.ini
   ```

3. **Dependency Installation Issues**:
   ```bash
   # Update pip
   pip install --upgrade pip
   
   # Install dependencies with verbose output
   pip install -v -r requirements.txt
   
   # Clear pip cache if needed
   pip cache purge
   ```

4. **Network Connectivity Issues**:
   ```bash
   # Test DNS resolution
   nslookup your-s3-endpoint
   
   # Test port connectivity
   telnet your-s3-endpoint 80
   
   # Check firewall status
   sudo ufw status
   ```

5. **S3 Endpoint Issues**:
   ```bash
   # Verify endpoint is accessible
   curl -I http://your-s3-endpoint/
   
   # Test with different protocols
   curl -I https://your-s3-endpoint/
   ```

### Debug Mode Deployment

For troubleshooting, deploy with debug configuration:

```bash
# Run with maximum verbosity
python main.py \
    --scope all \
    --log-level debug \
    --log-file debug.log \
    --export-results debug-results.json

# Monitor debug log in real-time
tail -f debug.log
```

## Performance Optimization

### System Optimization

```bash
# Increase file descriptor limits for high-concurrency testing
echo "* soft nofile 65535" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65535" | sudo tee -a /etc/security/limits.conf

# Optimize network settings
echo "net.core.rmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### Application Optimization

```bash
# Use optimized Python settings
export PYTHONOPTIMIZE=1
export PYTHONUNBUFFERED=1

# Run with optimizations
python -O main.py --scope all
```

## Maintenance

### Regular Maintenance Tasks

1. **Update Dependencies**:
   ```bash
   source venv/bin/activate
   pip list --outdated
   pip install --upgrade -r requirements.txt
   ```

2. **Clean Log Files**:
   ```bash
   # Clean old logs (older than 30 days)
   find /var/log -name "s3-checker*" -mtime +30 -delete
   ```

3. **Monitor Disk Space**:
   ```bash
   # Check available space
   df -h /opt/s3-compatibility-checker
   df -h /var/log
   ```

4. **Validate Configuration**:
   ```bash
   # Test configuration periodically
   python main.py --scope buckets --quiet
   ```

This deployment guide provides comprehensive instructions for setting up the S3 Compatibility Checker in production environments. Adjust the configurations based on your specific requirements and security policies.