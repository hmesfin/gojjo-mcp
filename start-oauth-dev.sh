#!/bin/bash
# Start MCP Server with OAuth in development mode

set -e

echo "🚀 Starting Django Vue MCP Server with GitHub OAuth..."

# Check for required environment file
if [ ! -f ".env.oauth" ]; then
    echo "❌ OAuth environment file not found!"
    echo "Please copy .env.oauth.example to .env.oauth and configure it:"
    echo "   cp .env.oauth.example .env.oauth"
    echo "   nano .env.oauth"
    exit 1
fi

# Load environment variables
export $(cat .env.oauth | grep -v '^#' | grep -v '^$' | xargs)

# Validate required variables
required_vars=("GITHUB_CLIENT_ID" "GITHUB_CLIENT_SECRET" "BASE_URL")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ Missing required environment variables:"
    printf '   %s\n' "${missing_vars[@]}"
    echo ""
    echo "Please configure these in .env.oauth file"
    exit 1
fi

# Ensure Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis not running. Starting Redis with Docker..."
    docker run -d --name redis-mcp-dev \
        -p 6379:6379 \
        redis:alpine \
        redis-server --requirepass "${REDIS_PASSWORD:-devpassword}"
    echo "✅ Redis started"
    sleep 2
fi

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Set environment for development
export PYTHONPATH="${PWD}/src"
export HTTP_MODE=true
export WEB_PORT=${WEB_PORT:-8000}
export HEALTH_PORT=${HEALTH_PORT:-8080}

echo "🔧 Configuration:"
echo "   GitHub Client ID: ${GITHUB_CLIENT_ID:0:8}..."
echo "   Base URL: ${BASE_URL}"
echo "   Web Port: ${WEB_PORT}"
echo "   Health Port: ${HEALTH_PORT}"
echo "   Redis URL: ${REDIS_URL:-redis://localhost:6379}"

echo ""
echo "🌐 Starting OAuth-enabled web server..."
echo "   Web Interface: ${BASE_URL}"
echo "   Health Checks: http://localhost:${HEALTH_PORT}"
echo ""
echo "📝 Next steps:"
echo "   1. Visit ${BASE_URL} to test OAuth login"
echo "   2. Authenticate with GitHub to get API key"
echo "   3. Use API key with Claude Code MCP client"
echo ""

# Start the server
python src/web_mcp_server.py