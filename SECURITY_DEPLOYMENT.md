# 🔐 Secure Django Vue MCP Server - Production Deployment Guide

## 🚀 Overview

This guide provides step-by-step instructions for securely deploying the Django Vue MCP Documentation Server to production. The server now includes comprehensive security measures to protect against common vulnerabilities and attacks.

## 🛡️ Security Features Implemented

### ✅ **Authentication & Authorization**

- **API Key Authentication**: Role-based access control (Anonymous, Basic, Premium, Developer, Admin)
- **JWT Token Support**: Secure token-based authentication
- **IP Whitelisting**: Restrict API keys to specific IP addresses
- **Role-based Rate Limiting**: Different limits based on user access level

### ✅ **Rate Limiting & DDoS Protection**

- **Multi-layer Rate Limiting**: Per-second, per-minute, per-hour limits
- **Token Bucket Algorithm**: Handles traffic bursts gracefully
- **Circuit Breakers**: Protects external API calls
- **Cost-based Limiting**: Expensive operations have higher costs
- **DDoS Detection**: Automatic IP blocking for suspicious behavior

### ✅ **Input Validation & SSRF Protection**

- **URL Validation**: Prevents SSRF attacks on internal networks
- **Package Name Validation**: Sanitizes library names
- **HTML Sanitization**: Prevents XSS attacks
- **Request Validation**: Validates headers, query parameters, and body

### ✅ **Container Security**

- **Non-root User**: Runs as `mcpuser` (UID 1000)
- **Read-only Filesystem**: Prevents runtime modifications
- **Minimal Base Image**: Reduced attack surface
- **Security Scanning**: Built-in Trivy vulnerability scanning
- **Dropped Capabilities**: Removes unnecessary Linux capabilities

### ✅ **Network Security**

- **Nginx Reverse Proxy**: With security headers and rate limiting
- **SSL/TLS Encryption**: HTTPS with modern cipher suites
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Request Filtering**: Blocks malicious requests and bots

## 🔧 Pre-deployment Setup

### 1. **Server Requirements**

```bash
# Minimum specifications for Hetzner server:
# - 2 CPU cores
# - 4GB RAM  
# - 40GB SSD storage
# - Ubuntu 22.04 LTS
# - Docker and Docker Compose installed
```

### 2. **Domain Setup**

- Point your domain to the server IP
- Obtain SSL certificates (Let's Encrypt recommended)
- Configure DNS A records for your domain

### 3. **Security Preparation**

```bash
# Create data directories with proper permissions
sudo mkdir -p /opt/mcp-server/{data,logs,ssl}
sudo chown -R 1000:1000 /opt/mcp-server/
sudo chmod 750 /opt/mcp-server/data
sudo chmod 770 /opt/mcp-server/logs
```

## 🚀 Production Deployment

### Step 1: Clone and Configure

```bash
# Clone the repository
cd /opt
sudo git clone https://github.com/hmesfin/gojjo-mcp.git mcp-server
cd mcp-server

# Set proper ownership
sudo chown -R 1000:1000 /opt/mcp-server/
```

### Step 2: Security Configuration

```bash
# Copy and customize the production environment file
cp .env.production.secure .env.production

# ⚠️  CRITICAL: Edit the environment file
nano .env.production

# Change these immediately:
# - JWT_SECRET (generate 32+ character random string)
# - REDIS_PASSWORD (generate secure password)  
# - Update domain names
# - Configure rate limits
# - Set notification emails
```

### Step 3: SSL Certificate Setup

```bash
# Install certbot for Let's Encrypt
sudo apt update
sudo apt install certbot

# Obtain SSL certificates (replace with your domain)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates to application directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /opt/mcp-server/ssl/domain.crt
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /opt/mcp-server/ssl/domain.key
sudo chown 1000:1000 /opt/mcp-server/ssl/*
sudo chmod 600 /opt/mcp-server/ssl/*
```

### Step 4: Build and Deploy

```bash
# Build the secure Docker image
docker build -f Dockerfile.secure -t secure-mcp-server:latest .

# Start the secure production environment
docker-compose -f docker-compose.secure.yml up -d

# Verify deployment
docker-compose -f docker-compose.secure.yml ps
docker-compose -f docker-compose.secure.yml logs -f
```

### Step 5: Initial Admin Setup

```bash
# Get the admin API key from container logs
docker logs secure-django-vue-mcp-server | grep "Admin API key created"

# Save the admin key securely - you'll need it for management
# Example output:
# 🔑 Admin API key created:
#     API Key: gojjo_mcp_AbCd123_xyz789...
```

## 🧪 Security Testing

### Step 1: Health Check Verification

```bash
# Test health endpoints
curl -f https://yourdomain.com/health
curl -f https://yourdomain.com/health/detailed
curl -f https://yourdomain.com/metrics  # Should be restricted

# Verify security headers
curl -I https://yourdomain.com/
```

### Step 2: Authentication Testing

```bash
# Test anonymous access (should be limited)
curl -s "https://yourdomain.com/api/resources" | jq

# Test with API key
curl -H "X-API-Key: your-api-key" \
     -s "https://yourdomain.com/api/resources" | jq

# Test rate limiting (should get 429 after limits)
for i in {1..20}; do
  curl -s "https://yourdomain.com/api/resources" &
done
wait
```

### Step 3: Security Validation

```bash
# Test SSRF protection (should be blocked)
curl -X POST "https://yourdomain.com/api/package" \
     -H "Content-Type: application/json" \
     -d '{"url": "http://169.254.169.254/metadata"}' 

# Test XSS protection
curl "https://yourdomain.com/api/resources?param=<script>alert('xss')</script>"

# Test invalid package names
curl "https://yourdomain.com/api/django/../../../etc/passwd"
```

## 📊 Monitoring & Maintenance

### Security Monitoring

```bash
# Monitor security logs
tail -f logs/nginx/access.log | grep " 429 \| 444 \| 403 "

# Check for blocked IPs
docker exec secure-django-vue-mcp-server python -c "
from security.rate_limiter import DDoSProtection
ddos = DDoSProtection()
print('Blocked IPs:', ddos.blocked_ips)
"

# Monitor Redis for rate limiting
docker exec secure-django-vue-mcp-redis redis-cli --scan --pattern "*rate*"
```

### Performance Monitoring

```bash
# Check container health
docker-compose -f docker-compose.secure.yml ps

# Monitor resource usage
docker stats secure-django-vue-mcp-server

# Check rate limit usage
curl -H "X-API-Key: your-api-key" \
     -i "https://yourdomain.com/health" | grep -i rate
```

### Log Analysis

```bash
# Analyze access patterns
awk '{print $1}' logs/nginx/access.log | sort | uniq -c | sort -nr | head -20

# Monitor API usage by endpoint
grep "GET\|POST" logs/nginx/api.log | awk '{print $7}' | sort | uniq -c | sort -nr

# Check for security events
grep -E "429|403|444" logs/nginx/access.log | tail -20
```

## 🚨 Security Incident Response

### Immediate Actions

```bash
# Block suspicious IP immediately
docker exec secure-django-vue-mcp-nginx nginx -s reload

# Check current connections
ss -tuln | grep :80
ss -tuln | grep :443

# Emergency shutdown (if needed)
docker-compose -f docker-compose.secure.yml down
```

### API Key Management

```bash
# Create new API keys
docker exec -it secure-django-vue-mcp-server python -c "
import asyncio
from security.auth import AuthManager, UserRole, APIKeyType
import redis.asyncio as redis

async def create_key():
    redis_client = redis.from_url('redis://redis:6379')
    auth = AuthManager(redis_client)
    key, api_key = await auth.generate_api_key(
        user_id='new_user',
        role=UserRole.BASIC,
        key_type=APIKeyType.STANDARD
    )
    print(f'New API Key: {key}')
    await redis_client.close()

asyncio.run(create_key())
"

# Revoke compromised API key
docker exec -it secure-django-vue-mcp-server python -c "
import asyncio
from security.auth import AuthManager
import redis.asyncio as redis

async def revoke_key():
    redis_client = redis.from_url('redis://redis:6379')
    auth = AuthManager(redis_client)
    success = await auth.revoke_api_key('key-id-to-revoke')
    print(f'Key revoked: {success}')
    await redis_client.close()

asyncio.run(revoke_key())
"
```

## 🔄 Updates and Maintenance

### Security Updates

```bash
# Update container images
docker-compose -f docker-compose.secure.yml pull
docker-compose -f docker-compose.secure.yml up -d

# Update SSL certificates (every 90 days)
sudo certbot renew
sudo cp /etc/letsencrypt/live/yourdomain.com/* /opt/mcp-server/ssl/
docker-compose -f docker-compose.secure.yml restart nginx

# Security scan
docker run --rm -v /opt/mcp-server:/app aquasec/trivy fs /app
```

### Performance Tuning

```bash
# Adjust rate limits based on usage patterns
# Edit .env.production and restart:
docker-compose -f docker-compose.secure.yml restart mcp-server

# Redis memory optimization
docker exec secure-django-vue-mcp-redis redis-cli MEMORY USAGE "*"
```

## 📋 Security Checklist

### Pre-deployment ✅

- [ ] Changed all default passwords and secrets
- [ ] Configured proper domain names
- [ ] Obtained valid SSL certificates
- [ ] Set appropriate rate limits
- [ ] Configured monitoring and alerting
- [ ] Tested security measures

### Post-deployment ✅

- [ ] Verified HTTPS is working
- [ ] Confirmed security headers are present
- [ ] Tested API key authentication
- [ ] Verified rate limiting is active
- [ ] Checked health endpoints
- [ ] Monitored logs for errors

### Ongoing Maintenance ✅

- [ ] Monitor security logs daily
- [ ] Update SSL certificates every 90 days
- [ ] Review API usage patterns weekly
- [ ] Update container images monthly
- [ ] Security audit quarterly
- [ ] Backup configuration and keys

## 🆘 Emergency Contacts

### Security Issues

- **Email**: <security@yourdomain.com>
- **Phone**: +1-555-SECURITY
- **Incident Response**: <https://yourdomain.com/incident>

### Monitoring Alerts

- **Slack**: #security-alerts
- **PagerDuty**: security-team
- **Email**: <alerts@yourdomain.com>

## 📚 Additional Resources

- [OWASP Security Guidelines](https://owasp.org/)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)
- [Nginx Security Configuration](https://nginx.org/en/docs/http/securing_web_traffic.html)
- [Redis Security](https://redis.io/topics/security)

---

**⚠️  IMPORTANT**: This is a production system. Always test changes in a staging environment first. Keep backups of your configuration and SSL certificates. Monitor security logs actively.

**🚀 Ready for Production!** With these security measures in place, your MCP server is ready to serve the Django/Vue community safely and reliably.
