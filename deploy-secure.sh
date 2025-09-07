#!/bin/bash

# Secure Deployment Script for Django Vue MCP Documentation Server
# This script implements security best practices for production deployment

set -euo pipefail
IFS=$'\n\t'

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DEPLOYMENT_ENV="${1:-production}"
BACKUP_DIR="/var/backups/mcp-server"
LOG_FILE="/var/log/mcp-deployment.log"

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# Check if running as root (required for some operations)
check_permissions() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root for security configurations"
    fi
}

# Verify environment file exists and has secure permissions
check_env_file() {
    local env_file=".env.${DEPLOYMENT_ENV}"
    
    if [[ ! -f "$env_file" ]]; then
        error "Environment file $env_file not found. Copy .env.production.example and configure it."
    fi
    
    # Check file permissions (should be 600)
    local perms=$(stat -c "%a" "$env_file")
    if [[ "$perms" != "600" ]]; then
        warning "Fixing insecure permissions on $env_file"
        chmod 600 "$env_file"
    fi
    
    # Verify required variables are set
    local required_vars=(
        "SECRET_KEY"
        "REDIS_URL"
        "GITHUB_TOKEN"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$env_file"; then
            error "Required variable $var not set in $env_file"
        fi
        
        # Check for default values
        if grep -q "^${var}=CHANGE_THIS" "$env_file"; then
            error "Variable $var still has default value. Please update it."
        fi
    done
    
    log "Environment file validated"
}

# Generate secure random passwords
generate_passwords() {
    log "Generating secure passwords..."
    
    # Generate Redis password if not set
    if grep -q "YOUR_STRONG_REDIS_PASSWORD" ".env.${DEPLOYMENT_ENV}"; then
        local redis_pass=$(openssl rand -base64 32)
        sed -i "s/YOUR_STRONG_REDIS_PASSWORD/${redis_pass}/g" ".env.${DEPLOYMENT_ENV}"
        log "Generated Redis password"
    fi
    
    # Generate secret key if not set
    if grep -q "CHANGE_THIS_TO_A_RANDOM_64_CHARACTER_STRING" ".env.${DEPLOYMENT_ENV}"; then
        local secret_key=$(openssl rand -base64 48)
        sed -i "s/CHANGE_THIS_TO_A_RANDOM_64_CHARACTER_STRING/${secret_key}/g" ".env.${DEPLOYMENT_ENV}"
        log "Generated secret key"
    fi
    
    # Generate API encryption key
    if grep -q "CHANGE_THIS_TO_A_RANDOM_32_CHARACTER_STRING" ".env.${DEPLOYMENT_ENV}"; then
        local api_key=$(openssl rand -base64 24)
        sed -i "s/CHANGE_THIS_TO_A_RANDOM_32_CHARACTER_STRING/${api_key}/g" ".env.${DEPLOYMENT_ENV}"
        log "Generated API encryption key"
    fi
}

# Set up SSL certificates
setup_ssl() {
    log "Setting up SSL certificates..."
    
    local cert_dir="/etc/ssl/certs"
    local domain="mcp.gojjoapps.com"
    
    # Check if certificates exist
    if [[ ! -f "${cert_dir}/${domain}.crt" ]]; then
        warning "SSL certificate not found. Setting up Let's Encrypt..."
        
        # Install certbot if not present
        if ! command -v certbot &> /dev/null; then
            apt-get update && apt-get install -y certbot
        fi
        
        # Obtain certificate
        certbot certonly --standalone \
            --non-interactive \
            --agree-tos \
            --email security@gojjoapps.com \
            -d "$domain" \
            --pre-hook "docker-compose down" \
            --post-hook "docker-compose up -d"
        
        # Link certificates
        ln -sf "/etc/letsencrypt/live/${domain}/fullchain.pem" "${cert_dir}/${domain}.crt"
        ln -sf "/etc/letsencrypt/live/${domain}/privkey.pem" "${cert_dir}/${domain}.key"
    fi
    
    # Set secure permissions
    chmod 644 "${cert_dir}/${domain}.crt"
    chmod 600 "${cert_dir}/${domain}.key"
    
    log "SSL certificates configured"
}

# Configure firewall
setup_firewall() {
    log "Configuring firewall..."
    
    # Install ufw if not present
    if ! command -v ufw &> /dev/null; then
        apt-get update && apt-get install -y ufw
    fi
    
    # Reset firewall rules
    ufw --force reset
    
    # Default policies
    ufw default deny incoming
    ufw default allow outgoing
    
    # Allow SSH (adjust port as needed)
    ufw allow 22/tcp comment "SSH"
    
    # Allow HTTP and HTTPS
    ufw allow 80/tcp comment "HTTP"
    ufw allow 443/tcp comment "HTTPS"
    
    # Allow monitoring from specific IPs only (optional)
    # ufw allow from 10.0.0.0/8 to any port 9090 comment "Prometheus"
    
    # Enable firewall
    ufw --force enable
    
    log "Firewall configured"
}

# Set up fail2ban for DDoS protection
setup_fail2ban() {
    log "Setting up fail2ban..."
    
    # Install fail2ban if not present
    if ! command -v fail2ban-client &> /dev/null; then
        apt-get update && apt-get install -y fail2ban
    fi
    
    # Create jail configuration
    cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
action = iptables-multiport[name=ReqLimit, port="http,https"]
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-badbots]
enabled = true
port = http,https
filter = nginx-badbots
logpath = /var/log/nginx/access.log
maxretry = 2

[nginx-noproxy]
enabled = true
port = http,https
filter = nginx-noproxy
logpath = /var/log/nginx/error.log
maxretry = 2
EOF
    
    # Create filter for rate limiting
    cat > /etc/fail2ban/filter.d/nginx-limit-req.conf <<EOF
[Definition]
failregex = limiting requests, excess: [\d\.]+ by zone "(?:[\w]+)", client: <HOST>
ignoreregex =
EOF
    
    # Restart fail2ban
    systemctl restart fail2ban
    
    log "fail2ban configured"
}

# Security hardening for the host system
harden_system() {
    log "Applying system hardening..."
    
    # Disable unnecessary services
    local services=(
        "bluetooth"
        "cups"
        "avahi-daemon"
    )
    
    for service in "${services[@]}"; do
        if systemctl is-enabled "$service" &>/dev/null; then
            systemctl disable "$service"
            systemctl stop "$service"
            log "Disabled $service"
        fi
    done
    
    # Kernel hardening via sysctl
    cat > /etc/sysctl.d/99-security.conf <<EOF
# IP Spoofing protection
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Ignore ICMP redirects
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0

# Ignore send redirects
net.ipv4.conf.all.send_redirects = 0

# Disable source packet routing
net.ipv4.conf.all.accept_source_route = 0
net.ipv6.conf.all.accept_source_route = 0

# Log Martians
net.ipv4.conf.all.log_martians = 1

# Ignore ICMP ping requests
net.ipv4.icmp_echo_ignore_broadcasts = 1

# Ignore Directed pings
net.ipv4.icmp_ignore_bogus_error_responses = 1

# Enable TCP/IP SYN cookies
net.ipv4.tcp_syncookies = 1

# Increase TCP backlog
net.core.netdev_max_backlog = 5000

# Enable ExecShield (if available)
kernel.exec-shield = 1
kernel.randomize_va_space = 2

# Increase file descriptor limits
fs.file-max = 65535
EOF
    
    sysctl -p /etc/sysctl.d/99-security.conf
    
    log "System hardening applied"
}

# Set up monitoring and alerting
setup_monitoring() {
    log "Setting up monitoring..."
    
    # Create monitoring script
    cat > /usr/local/bin/mcp-monitor.sh <<'EOF'
#!/bin/bash

# Check if services are running
check_service() {
    local service=$1
    if ! docker-compose ps | grep -q "$service.*Up"; then
        echo "Service $service is down!" | mail -s "MCP Alert: Service Down" security@gojjoapps.com
    fi
}

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "Disk usage is ${DISK_USAGE}%" | mail -s "MCP Alert: High Disk Usage" security@gojjoapps.com
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{print int($3/$2 * 100)}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "Memory usage is ${MEM_USAGE}%" | mail -s "MCP Alert: High Memory Usage" security@gojjoapps.com
fi

# Check services
check_service "mcp-server"
check_service "redis"
check_service "nginx"

# Check for failed login attempts
FAILED_LOGINS=$(grep "Failed password" /var/log/auth.log | wc -l)
if [ "$FAILED_LOGINS" -gt 10 ]; then
    echo "Detected $FAILED_LOGINS failed login attempts" | mail -s "MCP Alert: Failed Logins" security@gojjoapps.com
fi
EOF
    
    chmod +x /usr/local/bin/mcp-monitor.sh
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/mcp-monitor.sh") | crontab -
    
    log "Monitoring configured"
}

# Create backup
create_backup() {
    log "Creating backup..."
    
    # Create backup directory
    mkdir -p "$BACKUP_DIR"
    
    # Backup timestamp
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="${BACKUP_DIR}/mcp-backup-${timestamp}.tar.gz"
    
    # Create backup
    tar -czf "$backup_file" \
        --exclude=".git" \
        --exclude="__pycache__" \
        --exclude="*.pyc" \
        --exclude="logs/*" \
        --exclude="cache/*" \
        .
    
    # Keep only last 7 backups
    ls -t "${BACKUP_DIR}"/mcp-backup-*.tar.gz | tail -n +8 | xargs -r rm
    
    log "Backup created: $backup_file"
}

# Deploy the application
deploy_application() {
    log "Deploying application..."
    
    # Pull latest changes (if using git)
    if [[ -d .git ]]; then
        git pull origin main
    fi
    
    # Build containers with security Dockerfile
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Stop existing containers
    docker-compose -f docker-compose.prod.yml down
    
    # Update Redis configuration
    if [[ -f redis-secure.conf ]]; then
        # Get Redis password from env file
        local redis_pass=$(grep "REDIS_URL" ".env.${DEPLOYMENT_ENV}" | sed 's/.*://:/' | sed 's/@.*//')
        sed -i "s/CHANGE_THIS_STRONG_PASSWORD/${redis_pass}/g" redis-secure.conf
    fi
    
    # Start containers
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services to be healthy
    log "Waiting for services to be healthy..."
    sleep 10
    
    # Verify services are running
    if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log "Services are running"
    else
        error "Services failed to start"
    fi
}

# Run security audit
run_security_audit() {
    log "Running security audit..."
    
    # Check for known vulnerabilities in dependencies
    docker run --rm -v "$(pwd):/app" aquasec/trivy fs /app
    
    # Check Docker images for vulnerabilities
    docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
        aquasec/trivy image django-vue-mcp-server-prod
    
    # Check for exposed secrets
    docker run --rm -v "$(pwd):/app" trufflesecurity/trufflehog:latest \
        filesystem /app --no-verification
    
    log "Security audit completed"
}

# Main deployment flow
main() {
    log "Starting secure deployment for environment: $DEPLOYMENT_ENV"
    
    check_permissions
    check_env_file
    generate_passwords
    create_backup
    setup_ssl
    setup_firewall
    setup_fail2ban
    harden_system
    setup_monitoring
    deploy_application
    run_security_audit
    
    log "Deployment completed successfully!"
    
    # Print important information
    echo -e "\n${GREEN}=== Deployment Summary ===${NC}"
    echo "Environment: $DEPLOYMENT_ENV"
    echo "SSL Status: Configured"
    echo "Firewall: Enabled"
    echo "Monitoring: Active"
    echo "Backup Location: $BACKUP_DIR"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Test the service: curl https://mcp.gojjoapps.com/health"
    echo "2. Monitor logs: docker-compose logs -f"
    echo "3. Check security alerts in your email"
    echo "4. Review the security audit results above"
}

# Run main function
main "$@"