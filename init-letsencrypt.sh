#!/bin/bash

# Let's Encrypt SSL Certificate Setup for Production
# Run this script on your Hetzner server to set up SSL certificates

if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Error: docker-compose is not installed.' >&2
  exit 1
fi

domain="mcp.gojjoapps.com"
email="admin@gojjoapps.com" # Replace with your email
staging=0 # Set to 1 if you want to test with Let's Encrypt staging server

echo "### Starting Let's Encrypt certificate setup for $domain..."

# Create necessary directories
echo "Creating certificate directories..."
mkdir -p "./certbot/www"
mkdir -p "./certbot/conf"
mkdir -p "./logs/nginx"

# Download recommended TLS parameters
echo "Downloading recommended TLS parameters..."
if [ ! -e "./certbot/conf/options-ssl-nginx.conf" ]; then
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "./certbot/conf/options-ssl-nginx.conf"
fi

if [ ! -e "./certbot/conf/ssl-dhparams.pem" ]; then
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "./certbot/conf/ssl-dhparams.pem"
fi

# Create temporary nginx config for initial certificate request
echo "Creating temporary nginx config..."
cat > ./nginx/nginx.temp.conf << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $domain;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 301 https://\$server_name\$request_uri;
        }
    }
}
EOF

# Start nginx with temporary config
echo "Starting nginx for certificate generation..."
docker-compose -f docker-compose.prod.yml run --rm --service-ports -d --name nginx-temp nginx nginx -g 'daemon off;' -c /etc/nginx/nginx.temp.conf

# Wait a bit for nginx to start
sleep 5

# Select appropriate server URL
if [ $staging != "0" ]; then
  echo "Using Let's Encrypt staging server..."
  staging_arg="--staging"
else
  staging_arg=""
fi

# Request certificate
echo "Requesting certificate for $domain..."
docker-compose -f docker-compose.prod.yml run --rm certbot \
  certbot certonly --webroot \
  --webroot-path=/var/www/certbot \
  --email $email \
  --agree-tos \
  --no-eff-email \
  $staging_arg \
  -d $domain

# Stop temporary nginx
echo "Stopping temporary nginx..."
docker stop nginx-temp
docker rm nginx-temp

# Check if certificate was created
if [ -d "./certbot/conf/live/$domain" ]; then
  echo "Certificate successfully created!"
  
  # Replace temporary config with production config
  rm ./nginx/nginx.temp.conf
  
  echo "Starting production services..."
  docker-compose -f docker-compose.prod.yml up -d
  
  echo "### SSL setup complete! Your site should now be available at https://$domain"
else
  echo "Certificate creation failed. Please check the logs above."
  exit 1
fi