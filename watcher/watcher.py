#!/usr/bin/env python3
"""
Blue/Green Deployment Log Watcher
Monitors Nginx logs and sends Slack alerts for failovers and high error rates.
"""

import os
import re
import time
import requests
from collections import deque
from datetime import datetime, timedelta

# Configuration from environment variables
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', 2))
WINDOW_SIZE = int(os.getenv('WINDOW_SIZE', 200))
ALERT_COOLDOWN_SEC = int(os.getenv('ALERT_COOLDOWN_SEC', 300))
MAINTENANCE_MODE = os.getenv('MAINTENANCE_MODE', 'false').lower() == 'true'
LOG_FILE = '/logs/access.log'

# State tracking
last_pool = None
request_window = deque(maxlen=WINDOW_SIZE)
last_alert_time = {}

print(f"🔍 Log Watcher Started")
print(f"   Slack Webhook: {'Configured' if SLACK_WEBHOOK_URL else 'NOT SET'}")
print(f"   Error Threshold: {ERROR_RATE_THRESHOLD}%")
print(f"   Window Size: {WINDOW_SIZE} requests")
print(f"   Alert Cooldown: {ALERT_COOLDOWN_SEC}s")
print(f"   Maintenance Mode: {MAINTENANCE_MODE}")
print(f"   Watching: {LOG_FILE}")
print("-" * 50)


def tail_log_file(filename):
    """Generator that yields new log lines as they appear."""
    while not os.path.exists(filename):
        print(f"⏳ Waiting for log file: {filename}")
        time.sleep(2)
    
    print(f"✅ Log file found, starting to tail...")
    
    # Read existing lines first, then tail new ones
    with open(filename, 'r') as file:
        # Skip to end by reading all existing lines
        for _ in file:
            pass
        
        # Now tail new lines
        while True:
            line = file.readline()
            if line:
                yield line.strip()
            else:
                time.sleep(0.1)


def parse_log_line(line):
    """
    Parse Nginx log line to extract pool, status, and other metrics.
    
    Example log line:
    192.168.1.1 - "GET /version HTTP/1.1" 200 pool=blue release=blue-v1.0.0 
    upstream_status=200 upstream=172.18.0.2:3000 request_time=0.045 upstream_time=0.032
    """
    data = {
        'pool': None,
        'release': None,
        'upstream_status': None,
        'upstream': None,
        'request_time': None,
        'upstream_time': None,
        'status': None
    }
    
    # Extract pool
    match = re.search(r'pool=(\w+)', line)
    if match:
        data['pool'] = match.group(1)
    
    # Extract release
    match = re.search(r'release=([\w\-\.]+)', line)
    if match:
        data['release'] = match.group(1)
    
    # Extract upstream status
    match = re.search(r'upstream_status=(\d+)', line)
    if match:
        data['upstream_status'] = int(match.group(1))
    
    # Extract upstream address
    match = re.search(r'upstream=([\d\.:]+)', line)
    if match:
        data['upstream'] = match.group(1)
    
    # Extract request time
    match = re.search(r'request_time=([\d\.]+)', line)
    if match:
        data['request_time'] = float(match.group(1))
    
    # Extract upstream response time
    match = re.search(r'upstream_time=([\d\.]+)', line)
    if match:
        data['upstream_time'] = float(match.group(1))
    
    # Extract HTTP status
    match = re.search(r'"\s+(\d{3})\s+', line)
    if match:
        data['status'] = int(match.group(1))
    
    return data


def detect_failover(current_pool):
    """
    Detect if traffic has failed over to a different pool.
    Sends Slack alert when failover occurs.
    """
    global last_pool
    
    if not current_pool:
        return
    
    # First request - establish baseline
    if last_pool is None:
        last_pool = current_pool
        print(f"📊 Baseline established: Pool={current_pool}")
        return
    
    # Detect pool change (failover)
    if current_pool != last_pool:
        message = f"🔄 *Failover Detected*\n" \
                  f"From: `{last_pool}` → To: `{current_pool}`\n" \
                  f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                  f"Reason: Primary pool health check failed"
        
        print(f"🚨 {message.replace('*', '').replace('`', '')}")
        send_slack_alert(message, alert_type='failover')
        
        last_pool = current_pool


def check_error_rate():
    """
    Calculate 5xx error rate over sliding window.
    Sends alert if error rate exceeds threshold.
    """
    if len(request_window) < WINDOW_SIZE:
        return  # Not enough data yet
    
    # Count 5xx errors in window
    error_count = sum(1 for status in request_window if status and status >= 500)
    error_rate = (error_count / WINDOW_SIZE) * 100
    
    # Check if threshold exceeded
    if error_rate > ERROR_RATE_THRESHOLD:
        message = f"⚠️ *High Error Rate Alert*\n" \
                  f"Current Rate: `{error_rate:.1f}%` (Threshold: {ERROR_RATE_THRESHOLD}%)\n" \
                  f"Errors: {error_count}/{WINDOW_SIZE} requests\n" \
                  f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n" \
                  f"Action: Check upstream logs and consider manual intervention"
        
        print(f"🚨 {message.replace('*', '').replace('`', '')}")
        send_slack_alert(message, alert_type='error_rate')


def send_slack_alert(message, alert_type='general'):
    """
    Send alert to Slack with cooldown to prevent spam.
    """
    # Skip if in maintenance mode
    if MAINTENANCE_MODE:
        print(f"🔧 Maintenance mode - alert suppressed: {alert_type}")
        return
    
    # Skip if no webhook configured
    if not SLACK_WEBHOOK_URL:
        print(f"⚠️  Slack webhook not configured - alert not sent")
        return
    
    # Check cooldown
    now = datetime.now()
    cooldown_key = alert_type
    
    if cooldown_key in last_alert_time:
        elapsed = (now - last_alert_time[cooldown_key]).total_seconds()
        if elapsed < ALERT_COOLDOWN_SEC:
            remaining = ALERT_COOLDOWN_SEC - elapsed
            print(f"⏸️  Alert cooldown active: {remaining:.0f}s remaining")
            return
    
    # Send alert to Slack
    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json={'text': message},
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"✅ Alert sent to Slack: {alert_type}")
            last_alert_time[cooldown_key] = now
        else:
            print(f"❌ Slack alert failed: HTTP {response.status_code}")
    
    except Exception as e:
        print(f"❌ Error sending Slack alert: {e}")


def main():
    """
    Main loop: tail logs, parse, detect issues, send alerts.
    """
    print("🚀 Starting log monitoring...")
    
    request_count = 0
    
    try:
        for line in tail_log_file(LOG_FILE):
            # Parse log line
            data = parse_log_line(line)
            
            # Track request for error rate calculation
            if data['upstream_status']:
                request_window.append(data['upstream_status'])
                request_count += 1
            
            # Check for failover
            if data['pool']:
                detect_failover(data['pool'])
            
            # Check error rate (only after we have enough data)
            if request_count >= WINDOW_SIZE:
                check_error_rate()
            
            # Debug output every 50 requests
            if request_count % 50 == 0:
                error_count = sum(1 for s in request_window if s and s >= 500)
                error_rate = (error_count / len(request_window)) * 100 if request_window else 0
                print(f"📊 Stats: {request_count} requests | "
                      f"Pool: {data['pool'] or 'unknown'} | "
                      f"Error Rate: {error_rate:.1f}%")
    
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
