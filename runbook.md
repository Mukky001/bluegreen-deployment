Here is the updated `runbook.md` content. I've added the new section for **Maintenance Mode** at the end.

-----

### `runbook.md`

# 🚨 Blue/Green Deployment Operations Runbook

## Overview

This runbook provides guidance for responding to alerts from the Blue/Green deployment monitoring system.

-----

## Alert: 🔄 Failover Detected

### What It Means

Traffic has automatically switched from the primary pool (e.g., `blue`) to the backup pool (e.g., `green`) due to health check failures.

### Severity

**Medium** - System is self-healing but requires investigation.

### Immediate Actions

1.  **Verify Backup Pool:** Confirm the backup pool is healthy and serving traffic.

    ```bash
    curl http://YOUR_IP:8080/version
    # Look for the backup pool's 'X-App-Pool' header
    ```

2.  **Check Container Status:**

    ```bash
    docker compose ps
    # Look for unhealthy containers (e.g., app_blue)
    ```

3.  **Check Failed Pool Logs:**

    ```bash
    docker compose logs app_blue  # if Blue failed
    ```

### Investigation Steps

1.  **Check container logs** for errors (OOM, crashes) just before the failover.
2.  **Review resource usage**: CPU, memory, disk.
3.  **Check upstream dependencies**: Database, external APIs, etc.
4.  **Review recent deployments**: Was anything changed?

### Resolution

  * **If transient issue**: Nginx will automatically fail back to the primary pool once it becomes healthy again (after `fail_timeout=5s`).
  * **If persistent**:
      * Investigate and fix the root cause in the failed container.
      * Restart the fixed container: `docker compose start app_blue`.

-----

## Alert: ⚠️ High Error Rate

### What It Means

More than 2% (configurable) of requests in the last 200 requests (configurable) returned 5xx errors. This is an early warning *before* a full failover might occur.

### Severity

**High** - Active service degradation affecting users.

### Immediate Actions

1.  **Identify Active Pool:**

    ```bash
    curl -i http://YOUR_IP:8080/version | grep X-App-Pool
    ```

2.  **Check Application Logs (of the active pool):**

    ```bash
    docker compose logs app_blue app_green --tail=50
    # Look for 500 errors and stack traces in the *active* pool's logs
    ```

3.  **Check Watcher Logs:**

    ```bash
    docker compose logs alert_watcher --tail=20
    # Look for error rate percentage
    ```

### Investigation Steps

1.  **Analyze error patterns**: Are errors consistent or intermittent?
2.  **Check dependencies**: Database connections, external APIs.
3.  **Resource constraints**: Memory, CPU, disk space.
4.  **Recent changes**: Code deployments, config changes.

### Resolution

  * If the primary pool is degrading, this alert is your chance to fix it *before* a full failover.
  * If it cannot be fixed quickly, you may need to prepare for a **manual failover** by updating `ACTIVE_POOL` in your `.env` file and restarting Nginx (`docker compose up -d --no-deps nginx`).

-----

## ⚙️ Maintenance Mode (Suppressing Alerts)

### What It Means

If you are performing planned maintenance (like a manual pool toggle, deployment, or chaos test), you can prevent alert spam by temporarily suppressing all Slack notifications.

### How to Use

1.  **Enable Maintenance Mode:**

      * Edit your `.env` file.
      * Set `MAINTENANCE_MODE=true`.

2.  **Apply the Change:**

      * Restart the `alert_watcher` service to read the new setting.
      * ```bash
          docker compose up -d --no-deps alert_watcher
        ```

3.  **Perform Your Maintenance:**

      * You can now stop containers or trigger failovers without sending alerts to Slack. The watcher log will show `[MAINTENANCE] Alert Suppressed`.

4.  **CRITICAL: Disable Maintenance Mode:**

      * When finished, edit your `.env` file.
      * Set `MAINTENANCE_MODE=false`.
      * Restart the watcher again to re-enable alerts:
      * ```bash
          docker compose up -d --no-deps alert_watcher
        ```
