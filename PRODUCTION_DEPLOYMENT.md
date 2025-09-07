# 🚀 Production Deployment to Hetzner

This guide will help you deploy the MCP OAuth Server to your Hetzner production server with SSL, OAuth authentication, and all the bells and whistles!

## 🛠️ Prerequisites

### Local Machine
- Docker and Docker Compose
- SSH access to your Hetzner server
- Domain configured (mcp.gojjoapps.com)

### Hetzner Server
- Ubuntu 20.04+ or Debian 11+
- At least 2GB RAM, 20GB storage
- Root or sudo access
- Domain pointing to server IP

### DNS Configuration
Make sure `mcp.gojjoapps.com` points to your Hetzner server IP:
```bash
# Check DNS resolution
nslookup mcp.gojjoapps.com
```

## 🔧 Configuration Steps

### 1. Create Production Environment File
Copy the example and update with your values:
```bash
cp .env.production.example .env.production
nano .env.production
```

Update these critical values in `.env.production`:
```bash
# Deployment Configuration
DOMAIN=mcp.gojjoapps.com                    # Your domain
SERVER_IP=YOUR_ACTUAL_HETZNER_SERVER_IP     # Your server IP
SERVER_USER=root                            # SSH user (usually root)
EMAIL=admin@gojjoapps.com                   # For Let's Encrypt notifications
PROJECT_DIR=/opt/mcp-server                 # Server deployment directory

# GitHub OAuth (from your GitHub App)
GITHUB_CLIENT_ID=your_actual_client_id
GITHUB_CLIENT_SECRET=your_actual_client_secret

# Generate secure JWT secret
JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
```

### 2. GitHub OAuth Setup
Create a GitHub OAuth App with these settings:
- **Application name**: MCP Documentation Server
- **Homepage URL**: `https://your-domain.com`
- **Authorization callback URL**: `https://your-domain.com/auth/github/callback`

Copy the Client ID and Client Secret to your `.env.production` file.

### 3. Security Verification
Ensure your `.env.production` file has secure values:
```bash
# Check that sensitive values are not default/example values
grep -E "(CLIENT_ID|CLIENT_SECRET|JWT_SECRET)" .env.production

# Verify file permissions (should not be world-readable)
ls -la .env.production
chmod 600 .env.production  # If needed
```

## 🚀 Deployment Process

### Automated Deployment
The deployment script now reads configuration from `.env.production`:
```bash
# Ensure .env.production exists and is configured
ls -la .env.production

# Run deployment (will load config from .env.production)
./deploy-to-hetzner.sh
```

This script will:
1. ✅ Load configuration from `.env.production`
2. ✅ Test server connection
3. 📦 Copy files to server (excluding sensitive .env.production)
4. 🐳 Install Docker/Docker Compose
5. 🔐 Set up SSL certificates with Let's Encrypt
6. 🏗️ Build and start services
7. ✅ Run health checks

### Manual Deployment Steps
If you prefer manual deployment:

#### 1. Copy Files to Server
```bash
rsync -avz --exclude='.git' \
    ./ root@YOUR_SERVER_IP:/opt/mcp-server/
```

#### 2. SSH to Server and Setup
```bash
ssh root@YOUR_SERVER_IP
cd /opt/mcp-server

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose plugin
apt-get update
apt-get install -y docker-compose-plugin
```

#### 3. Configure Environment
```bash
# Update production settings
nano .env.production

# Set secure permissions
chmod 600 .env.production
```

#### 4. Initialize SSL and Deploy
```bash
# Set up SSL certificates
./init-letsencrypt.sh

# Or if certificates exist, just start services
docker compose -f docker-compose.prod.yml up -d
```

## 🔍 Post-Deployment Verification

### Health Checks
```bash
# Application health
curl https://mcp.gojjoapps.com/health

# Service status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

### OAuth Flow Test
1. Visit `https://mcp.gojjoapps.com`
2. Should redirect to login page
3. Click "Continue with GitHub"
4. Authorize the application
5. Should receive API key on success page
6. Click "View Dashboard" - should work without redirect

### SSL Certificate Check
```bash
# Check certificate validity
openssl s_client -connect mcp.gojjoapps.com:443 -servername mcp.gojjoapps.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

## 📊 Monitoring and Maintenance

### View Logs
```bash
# Application logs
docker logs django-vue-mcp-server-prod -f

# Nginx logs
docker logs django-vue-mcp-nginx -f

# Redis logs
docker logs django-vue-mcp-redis-prod -f

# All services
docker compose -f docker compose.prod.yml logs -f
```

### Update Deployment
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker compose -f docker compose.prod.yml build --no-cache
docker compose -f docker compose.prod.yml up -d
```

### SSL Certificate Renewal
Certificates automatically renew via the certbot container. To manually renew:
```bash
docker compose -f docker compose.prod.yml exec certbot certbot renew
docker compose -f docker compose.prod.yml exec nginx nginx -s reload
```

## 🛡️ Security Features

### Rate Limiting
- **OAuth endpoints**: 5 requests/minute
- **API endpoints**: 100 requests/minute  
- **General pages**: 10 requests/second

### Security Headers
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (HSTS)
- Content Security Policy

### Access Control
- API keys based on GitHub profile
- Role-based rate limiting
- IP-based restrictions (configurable)
- HttpOnly session cookies

## 🔧 Troubleshooting

### Common Issues

#### SSL Certificate Failed
```bash
# Check certbot logs
docker compose -f docker compose.prod.yml logs certbot

# Manual certificate request
docker compose -f docker compose.prod.yml run --rm certbot \
  certbot certonly --webroot --webroot-path=/var/www/certbot \
  --email admin@gojjoapps.com --agree-tos --no-eff-email \
  -d mcp.gojjoapps.com
```

#### OAuth Not Working
1. Check GitHub OAuth app settings
2. Verify callback URL matches exactly
3. Check environment variables:
   ```bash
   docker compose -f docker compose.prod.yml exec mcp-server env | grep GITHUB
   ```

#### Service Won't Start
```bash
# Check service status
docker compose -f docker compose.prod.yml ps

# Restart specific service
docker compose -f docker compose.prod.yml restart mcp-server

# View detailed logs
docker compose -f docker compose.prod.yml logs mcp-server
```

#### Redis Connection Issues
```bash
# Test Redis connection
docker compose -f docker compose.prod.yml exec redis redis-cli ping

# Check Redis logs
docker compose -f docker compose.prod.yml logs redis
```

## 📈 Performance Optimization

### Server Resources
Recommended Hetzner server specs:
- **CPU**: 2+ cores
- **RAM**: 4GB+ 
- **Storage**: 40GB+ SSD
- **Network**: 1Gbps

### Docker Resource Limits
Current configuration:
- MCP Server: 512MB memory limit
- Redis: 256MB memory limit
- Nginx: 128MB memory limit

### Scaling Considerations
- Add Redis Cluster for high availability
- Use Docker Swarm or Kubernetes for multi-server
- Implement CDN for static assets
- Add database for persistent storage

## 🎯 Success Checklist

After deployment, verify:
- [ ] HTTPS works without warnings
- [ ] OAuth flow completes successfully  
- [ ] Dashboard shows user information
- [ ] API key generation works
- [ ] Health endpoint returns 200
- [ ] Rate limiting is active
- [ ] Logs are collecting properly
- [ ] SSL auto-renewal is configured
- [ ] Security headers are present
- [ ] Performance is acceptable

## 🆘 Support

If you encounter issues:
1. Check logs first: `docker compose logs -f`
2. Verify environment variables
3. Test each service individually
4. Check GitHub OAuth app configuration
5. Verify DNS and firewall settings

**Your MCP OAuth Server is now ready for the Hetzner wild!** 🌍🚀