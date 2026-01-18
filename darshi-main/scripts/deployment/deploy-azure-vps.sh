#!/bin/bash
# Quick deployment script for Azure VPS
# Run this on your VPS after SSH'ing in

set -e

echo "=========================================="
echo "Darshi Azure VPS Deployment Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Please do not run as root. Run as a regular user with sudo privileges.${NC}"
    exit 1
fi

# Variables
PROJECT_DIR="/opt/darshi"
REPO_URL="https://github.com/yourusername/darshi.git"  # Update this

echo -e "${YELLOW}Step 1: Installing Docker and Docker Compose${NC}"
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Installing additional tools${NC}"
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx git htop ncdu
echo -e "${GREEN}✓ Tools installed${NC}"

echo ""
echo -e "${YELLOW}Step 3: Setting up project directory${NC}"
if [ ! -d "$PROJECT_DIR" ]; then
    sudo mkdir -p $PROJECT_DIR
    sudo chown $USER:$USER $PROJECT_DIR
    echo -e "${GREEN}✓ Project directory created: $PROJECT_DIR${NC}"
else
    echo -e "${GREEN}✓ Project directory exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 4: Cloning repository${NC}"
cd $PROJECT_DIR
if [ ! -d ".git" ]; then
    echo "Enter your GitHub repository URL (or press Enter to use default):"
    read -r repo_input
    if [ -n "$repo_input" ]; then
        REPO_URL="$repo_input"
    fi
    git clone $REPO_URL .
    echo -e "${GREEN}✓ Repository cloned${NC}"
else
    echo "Repository already cloned. Pulling latest changes..."
    git pull origin main
    echo -e "${GREEN}✓ Repository updated${NC}"
fi

echo ""
echo -e "${YELLOW}Step 5: Setting up environment variables${NC}"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${YELLOW}⚠ .env file created from .env.example${NC}"
        echo -e "${YELLOW}⚠ Please edit .env with your actual values before continuing${NC}"
        echo ""
        echo "Press Enter when you've updated .env file..."
        read -r
    else
        echo -e "${RED}✗ No .env.example found. Please create .env manually.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi

echo ""
echo -e "${YELLOW}Step 6: Creating required directories${NC}"
mkdir -p logs ssl data
echo -e "${GREEN}✓ Directories created${NC}"

echo ""
echo -e "${YELLOW}Step 7: Setting up SSL certificates${NC}"
echo "Enter your domain name (e.g., darshi.app):"
read -r domain

if [ -n "$domain" ]; then
    echo "Setting up Let's Encrypt SSL certificate..."
    sudo certbot certonly --nginx -d $domain -d www.$domain --non-interactive --agree-tos --email admin@$domain || true

    # Copy certificates to project directory
    if [ -d "/etc/letsencrypt/live/$domain" ]; then
        sudo cp /etc/letsencrypt/live/$domain/fullchain.pem ssl/
        sudo cp /etc/letsencrypt/live/$domain/privkey.pem ssl/
        sudo chown $USER:$USER ssl/*.pem
        echo -e "${GREEN}✓ SSL certificates configured${NC}"
    else
        echo -e "${YELLOW}⚠ SSL certificate generation failed or was skipped${NC}"
        echo -e "${YELLOW}⚠ You can set it up manually later${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Domain not provided. Skipping SSL setup.${NC}"
fi

echo ""
echo -e "${YELLOW}Step 8: Building and starting Docker containers${NC}"
docker-compose -f docker-compose.azure.yml build
docker-compose -f docker-compose.azure.yml up -d

echo "Waiting for services to start..."
sleep 15

echo ""
echo -e "${YELLOW}Step 9: Checking service status${NC}"
docker-compose -f docker-compose.azure.yml ps

echo ""
echo -e "${YELLOW}Step 10: Setting up Nginx${NC}"
if [ -f "nginx.conf" ]; then
    sudo cp nginx.conf /etc/nginx/nginx.conf
    sudo nginx -t
    sudo systemctl restart nginx
    echo -e "${GREEN}✓ Nginx configured and restarted${NC}"
else
    echo -e "${YELLOW}⚠ nginx.conf not found. Please configure Nginx manually.${NC}"
fi

echo ""
echo -e "${YELLOW}Step 11: Setting up auto-renewal for SSL${NC}"
if command -v certbot &> /dev/null && [ -n "$domain" ]; then
    echo "0 0 * * * certbot renew --quiet && systemctl reload nginx" | sudo tee -a /etc/crontab > /dev/null
    echo -e "${GREEN}✓ SSL auto-renewal configured${NC}"
else
    echo -e "${YELLOW}⚠ Skipping SSL auto-renewal setup${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Verify all services are running:"
echo "   docker-compose -f docker-compose.azure.yml ps"
echo ""
echo "2. Check logs:"
echo "   docker-compose -f docker-compose.azure.yml logs -f"
echo ""
echo "3. Test the API:"
echo "   curl http://localhost:8080/health"
echo ""
echo "4. Access your site:"
if [ -n "$domain" ]; then
    echo "   https://$domain"
else
    echo "   http://YOUR_VPS_IP"
fi
echo ""
echo "=========================================="
echo ""
echo -e "${YELLOW}Important: Remember to:${NC}"
echo "  - Update DNS records to point to this VPS"
echo "  - Configure firewall (ufw) if needed"
echo "  - Set up monitoring and backups"
echo "  - Review and secure .env file permissions"
echo ""
