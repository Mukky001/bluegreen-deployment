# Blue/Green Deployment with Nginx Auto-Failover

A production-ready Blue/Green deployment implementation using Docker Compose and Nginx with automatic failover capabilities.

## 🎯 Overview

This project implements a Blue/Green deployment pattern where:
- Two identical Node.js applications (Blue and Green) run simultaneously
- Nginx acts as a reverse proxy routing traffic to the active pool
- Automatic failover occurs when the active pool fails (returns 5xx or times out)
- Zero downtime and zero client-visible errors during failover
- Manual pool switching capability via configuration

## 🏗️ Architecture
```
Client Request
      ↓
Nginx Proxy (localhost:8080)
      ↓
  ┌───┴───┐
  ↓       ↓
Blue    Green
:8081   :8082
(primary) (backup)
```

### Key Components

1. **Blue Instance** (`app_blue`) - Primary application on port 8081
2. **Green Instance** (`app_green`) - Backup application on port 8082  
3. **Nginx Proxy** (`nginx_proxy`) - Load balancer on port 8080

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Ports 8080, 8081, 8082 available

### Setup

1. **Clone the repository**
```bash
   git clone <your-repo-url>
   cd bluegreen-deployment
```

2. **Configure environment variables**
```bash
   cp .env.example .env
   nano .env
```
   
   Update with your actual image URLs:
```bash
   BLUE_IMAGE=yimikaade/wonderful:devops-stage-two
   GREEN_IMAGE=yimikaade/wonderful:devops-stage-two
```

3. **Start the services**
```bash
   docker compose up -d
```

4. **Verify deployment**
```bash
   docker compose ps
   curl -i http://localhost:8080/version
```

## 📋 Available Endpoints

### Public Endpoints (via Nginx - port 8080)

- `GET /version` - Returns version info with pool and release headers
- `GET /healthz` - Health check endpoint

### Direct Instance Access (for testing)

- **Blue**: `http://localhost:8081/*`
- **Green**: `http://localhost:8082/*`

### Chaos Testing Endpoints (direct access only)

- `POST /chaos/start?mode=error` - Make instance return 500 errors
- `POST /chaos/start?mode=timeout` - Make instance timeout
- `POST /chaos/stop` - Restore normal operation

## 🧪 Testing Failover

### Test 1: Verify Blue is Active
```bash
curl -i http://localhost:8080/version
```

Expected headers:
```
X-App-Pool: blue
X-Release-Id: blue-v1.0.0
```

### Test 2: Trigger Failover
```bash
# Break Blue instance
curl -X POST http://localhost:8081/chaos/start?mode=error

# Verify traffic switches to Green with no errors
for i in {1..10}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" http://localhost:8080/version
done
```

**Expected:** All requests return `200 OK`

### Test 3: Verify Green is Active
```bash
curl -i http://localhost:8080/version
```

Expected headers:
```
X-App-Pool: green
X-Release-Id: green-v1.0.0
```

### Test 4: Restore Blue
```bash
# Stop chaos
curl -X POST http://localhost:8081/chaos/stop

# Wait for Blue to recover
sleep 6

# Verify Blue is active again
curl -i http://localhost:8080/version
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BLUE_IMAGE` | Docker image for Blue instance | `registry/app:blue` |
| `GREEN_IMAGE` | Docker image for Green instance | `registry/app:green` |
| `ACTIVE_POOL` | Primary pool (`blue` or `green`) | `blue` |
| `RELEASE_ID_BLUE` | Release identifier for Blue | `blue-v1.0.0` |
| `RELEASE_ID_GREEN` | Release identifier for Green | `green-v1.0.0` |
| `PORT` | Internal application port | `3000` |

### Nginx Failover Configuration

The Nginx configuration in `nginx/default.conf` includes:

- **Fast failure detection**: 2-second timeouts
- **Immediate failover**: `max_fails=1` 
- **Backup directive**: Green only receives traffic when Blue fails
- **Retry on errors**: `proxy_next_upstream` handles 5xx, timeout, errors
- **Header forwarding**: Preserves `X-App-Pool` and `X-Release-Id`

Key settings:
```nginx
proxy_connect_timeout 2s;
proxy_send_timeout 2s;
proxy_read_timeout 2s;
proxy_next_upstream error timeout http_500 http_502 http_503 http_504;
proxy_next_upstream_tries 2;
```

## 🔄 Manual Pool Switching

To switch Green to primary and Blue to backup:

1. Edit `nginx/default.conf`:
```nginx
   upstream backend {
       server app_blue:3000 backup max_fails=1 fail_timeout=5s;
       server app_green:3000 max_fails=1 fail_timeout=5s;
   }
```

2. Reload Nginx:
```bash
   docker compose restart nginx
```

3. Update `.env`:
```bash
   ACTIVE_POOL=green
```

## 🐛 Troubleshooting

### Containers won't start
```bash
# Check logs
docker compose logs

# Check specific service
docker compose logs nginx
docker compose logs app_blue
```

### Port conflicts
```bash
# Find what's using port 8080
sudo lsof -i :8080

# Stop the conflicting service
sudo systemctl stop <service-name>
```

### Nginx config errors
```bash
# View generated config
docker compose exec nginx cat /etc/nginx/conf.d/default.conf

# Test config syntax
docker compose exec nginx nginx -t
```

### Health checks failing
```bash
# Test health endpoint directly
curl http://localhost:8081/healthz
curl http://localhost:8082/healthz
```

## 📊 Success Criteria

✅ All traffic goes to Blue by default  
✅ Zero failed requests during Blue failure  
✅ Automatic failover to Green within 2-5 seconds  
✅ Headers correctly identify active pool  
✅ Total request time < 10 seconds  
✅ Blue automatically recovers after chaos stops  

## 🛑 Stopping the Deployment
```bash
# Stop all containers
docker compose down

# Stop and remove volumes
docker compose down -v
```

## 📁 Project Structure
```
bluegreen-deployment/
├── docker-compose.yml       # Service orchestration
├── .env                     # Environment variables (not in repo)
├── .env.example            # Environment template
├── README.md               # This file
├── DECISION.md             # Implementation decisions
└── nginx/
    └── default.conf        # Nginx configuration
```

## 🔒 Security Notes

- `.env` file is git-ignored to prevent exposing sensitive data
- Use `.env.example` as a template
- Update image URLs before deploying
- Ensure firewall rules allow required ports

## 📝 CI/CD Integration

This setup is designed to work with automated grading systems:

1. Set environment variables via `.env`
2. Run `docker compose up -d`
3. Test endpoints automatically
4. Verify failover behavior
5. Check for zero error

## 👤 Author

Muktar Akinola

# Slack_ID
MK
