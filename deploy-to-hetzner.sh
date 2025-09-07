#!/bin/bash

# Deploy MCP OAuth Server to Hetzner Production
# Run this script to deploy the application to your Hetzner server

set -e

echo "🚀 Deploying MCP OAuth Server to Hetzner Production..."

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="mcp.gojjoapps.com"
EMAIL="admin@gojjoapps.com"
SERVER_USER="root"  # Change this to your server user
SERVER_IP="178.156.186.160"  # Replace with your server IP
PROJECT_DIR="/opt/mcp-server"

echo -e "${BLUE}Configuration:${NC}"
echo "Domain: $DOMAIN"
echo "Server: $SERVER_USER@$SERVER_IP"
echo "Project Directory: $PROJECT_DIR"
echo

# Check if we have the server IP configured
if [ "$SERVER_IP" = "178.156.186.160" ]; then
    echo -e "${RED}ERROR: Please update SERVER_IP in this script with your actual Hetzner server IP${NC}"
    exit 1
fi

# Check if we can connect to the server
echo -e "${BLUE}Testing server connection...${NC}"
if ! ssh -o ConnectTimeout=10 $SERVER_USER@$SERVER_IP "echo 'Connection successful'"; then
    echo -e "${RED}ERROR: Cannot connect to server. Please check your SSH configuration.${NC}"
    exit 1
fi

# Create project directory on server
echo -e "${BLUE}Creating project directory on server...${NC}"
ssh $SERVER_USER@$SERVER_IP "mkdir -p $PROJECT_DIR"

# Copy files to server
echo -e "${BLUE}Copying files to server...${NC}"
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
    ./ $SERVER_USER@$SERVER_IP:$PROJECT_DIR/

# Install Docker and Docker Compose on server if not present
echo -e "${BLUE}Setting up Docker on server...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'EOF'
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        systemctl enable docker
        systemctl start docker
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
    fi
EOF

# Update production environment variables
echo -e "${BLUE}Configuring production environment...${NC}"
ssh $SERVER_USER@$SERVER_IP << EOF
    cd $PROJECT_DIR
    
    # Update the production environment file with actual domain
    sed -i 's/BASE_URL=.*/BASE_URL=https://$DOMAIN/' .env.production
    sed -i 's/ALLOWED_HOSTS=.*/ALLOWED_HOSTS=$DOMAIN,localhost/' .env.production
    sed -i 's/CORS_ALLOWED_ORIGINS=.*/CORS_ALLOWED_ORIGINS=https:\/\/$DOMAIN/' .env.production
    
    # Generate a secure JWT secret if not already set
    if grep -q "change-this-to-something-very-secure" .env.production; then
        JWT_SECRET=\$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-64)
        sed -i "s/JWT_SECRET=.*/JWT_SECRET=\$JWT_SECRET/" .env.production
        echo "Generated new JWT secret"
    fi
    
    # Set correct permissions
    chmod 600 .env.production
    
    echo "Production environment configured"
EOF

# Set up SSL certificates
echo -e "${BLUE}Setting up SSL certificates...${NC}"
ssh $SERVER_USER@$SERVER_IP << EOF
    cd $PROJECT_DIR
    
    # Make sure the init script is executable
    chmod +x ./init-letsencrypt.sh
    
    # Update email in the SSL setup script
    sed -i 's/email=.*/email="$EMAIL"/' ./init-letsencrypt.sh
    
    echo "SSL setup script configured"
EOF

# Deploy the application
echo -e "${BLUE}Deploying application...${NC}"
ssh $SERVER_USER@$SERVER_IP << EOF
    cd $PROJECT_DIR
    
    # Build and start services
    echo "Building Docker images..."
    docker-compose -f docker-compose.prod.yml build
    
    # Initialize SSL certificates
    echo "Setting up SSL certificates..."
    if [ ! -d "./certbot/conf/live/$DOMAIN" ]; then
        ./init-letsencrypt.sh
    else
        echo "SSL certificates already exist, starting services..."
        docker-compose -f docker-compose.prod.yml up -d
    fi
    
    echo "Deployment complete!"
EOF

# Final checks
echo -e "${BLUE}Running post-deployment checks...${NC}"
sleep 10  # Wait for services to start

# Check if services are running
echo -e "${YELLOW}Checking service health...${NC}"
if curl -f -k https://$DOMAIN/health; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

# Check if OAuth login is working
echo -e "${YELLOW}Testing OAuth login page...${NC}"
if curl -f -k https://$DOMAIN/login | grep -q "Continue with GitHub"; then
    echo -e "${GREEN}✅ OAuth login page is working!${NC}"
else
    echo -e "${RED}❌ OAuth login page is not working${NC}"
fi

echo
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo
echo -e "${BLUE}Your MCP OAuth Server is now running at:${NC}"
echo -e "🌐 ${GREEN}https://$DOMAIN${NC}"
echo -e "❤️  Health: ${GREEN}https://$DOMAIN/health${NC}"
echo -e "📚 Docs: ${GREEN}https://$DOMAIN/docs${NC}"
echo
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Test the OAuth flow by visiting the login page"
echo "2. Set up monitoring and alerts"
echo "3. Configure backups"
echo "4. Update DNS if needed"
echo
echo -e "${BLUE}Log monitoring:${NC}"
echo "ssh $SERVER_USER@$SERVER_IP 'docker-compose -f $PROJECT_DIR/docker-compose.prod.yml logs -f'"
echo