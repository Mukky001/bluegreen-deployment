:# Blue/Green Deployment Operations Runbook

## Overview
This runbook provides guidance for responding to alerts from the Blue/Green deployment monitoring system.

---

## Alert: 🔄 Failover Detected

### What It Means
Traffic has automatically switched from the primary pool to the backup pool due to health check failures.

### Severity
**Medium** - System is self-healing but requires investigation

### Immediate Actions
1. Verify backup pool is healthy:
```bash
   curl http://YOUR_IP:8080/version
   # Should return 200 with correct pool in header
```

2. Check container status:
```bash
   docker compose ps
   # Look for unhealthy containers
```

3. Check failed pool logs:
```bash
   docker compose logs app_blue    # if Blue failed
   docker compose logs app_green   # if Green failed
```

### Investigation Steps
1. **Check container logs** for errors before failover
2. **Review resource usage**: CPU, memory, disk
3. **Check upstream dependencies**: Database, APIs, etc.
4. **Review recent deployments**: Was anything changed?

### Resolution
- **If transient issue**: Wait for automatic recovery (fail_timeout=5s)
- **If persistent**: 
  - Investigate root cause
  - Fix underlying issue
  - Consider manual intervention if backup also degrading

### Post-Incident
- Document root cause
- Update monitoring if needed
- Review if thresholds need adjustment

---

## Alert: ⚠️ High Error Rate

### What It Means
More than 2% (configurable) of requests in the last 200 requests (configurable) returned 5xx errors.

### Severity
**High** - Active service degradation affecting users

### Immediate Actions
1. Check current error rate:
```bash
   docker compose logs alert_watcher --tail=20
   # Look for error rate percentage
```

2. Identify which pool is active:
```bash
   curl -i http://YOUR_IP:8080/version | grep X-App-Pool
```

3. Check application logs:
```bash
   docker compose logs app_blue app_green --tail=50
   # Look for 500 errors and stack traces
```

### Investigation Steps
1. **Analyze error patterns**: Are errors consistent or intermittent?
2. **Check dependencies**: Database connections, external APIs
3. **Resource constraints**: Memory, CPU, disk space
4. **Recent changes**: Code deployments, config changes

### Resolution Options

#### Option 1:
