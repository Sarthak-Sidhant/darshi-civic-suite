#!/bin/bash
set -e

# Darshi Azure Deployment Script
# Run this on your Azure VM (Ubuntu 22.04)
# Usage: ./deploy-azure.sh

echo "=========================================="
echo "Darshi Azure Deployment Script"
echo "=========================================="

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please do not run as root. Run as regular user with sudo access."
    exit 1
fi

# Update system
print_info "Updating system packages..."
sudo apt update
sudo apt upgrade -y
print_success "System updated"

# Install essential packages
print_info "Installing essential packages..."
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    vim \
    htop \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release
print_success "Essential packages installed"

# Install Python 3.11
print_info "Installing Python 3.11..."
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
print_success "Python 3.11 installed"

# Install PostgreSQL 15
print_info "Installing PostgreSQL 15..."
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-15 postgresql-contrib-15 postgresql-15-postgis-3
print_success "PostgreSQL 15 installed"

# Configure PostgreSQL
print_info "Configuring PostgreSQL..."
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Create database and user
sudo -u postgres psql <<EOF
CREATE DATABASE darshi;
CREATE USER darshi_user WITH ENCRYPTED PASSWORD 'darshi_secure_password_change_me';
GRANT ALL PRIVILEGES ON DATABASE darshi TO darshi_user;
\c darshi
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
EOF

# Update PostgreSQL to allow local connections
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = 'localhost'/" /etc/postgresql/15/main/postgresql.conf

# Update pg_hba.conf for local connections
sudo bash -c 'cat >> /etc/postgresql/15/main/pg_hba.conf <<EOF

# Darshi app local connection
host    darshi    darshi_user    127.0.0.1/32    md5
EOF'

sudo systemctl restart postgresql
print_success "PostgreSQL configured"

# Install Redis
print_info "Installing Redis..."
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Configure Redis for production
sudo sed -i 's/^bind 127.0.0.1/bind 127.0.0.1/' /etc/redis/redis.conf
sudo sed -i 's/^# maxmemory <bytes>/maxmemory 2gb/' /etc/redis/redis.conf
sudo sed -i 's/^# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

sudo systemctl restart redis-server
print_success "Redis installed and configured"

# Install Nginx
print_info "Installing Nginx..."
sudo apt install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
print_success "Nginx installed"

# Install Certbot for SSL
print_info "Installing Certbot..."
sudo snap install core; sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot
print_success "Certbot installed"

# Create application directory
print_info "Setting up application directory..."
APP_DIR="/home/$USER/darshi"
if [ -d "$APP_DIR" ]; then
    print_info "Application directory exists, backing up..."
    mv "$APP_DIR" "$APP_DIR.backup.$(date +%Y%m%d_%H%M%S)"
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"
print_success "Application directory created: $APP_DIR"

# Clone repository (if not already present)
print_info "Cloning Darshi repository..."
if [ ! -d ".git" ]; then
    # Assuming repo is already on server, otherwise clone
    print_info "Please clone your repository manually or copy files to $APP_DIR"
    print_info "Run: git clone https://github.com/yourusername/darshi.git $APP_DIR"
fi

# Create Python virtual environment
print_info "Creating Python virtual environment..."
python3.11 -m venv venv
source venv/bin/activate
print_success "Virtual environment created"

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    print_info "Installing Python dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Python dependencies installed"
else
    print_info "requirements.txt not found, skipping Python dependencies"
fi

# Create .env file template
print_info "Creating .env file..."
cat > .env <<'ENVEOF'
# Database Configuration
DATABASE_URL=postgresql://darshi_user:darshi_secure_password_change_me@localhost:5432/darshi

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
PROJECT_ID=darshi-azure
ENVIRONMENT=production
LOG_LEVEL=INFO
SECRET_KEY=CHANGE_ME_RUN_SCRIPT_TO_GENERATE

# CORS Configuration
CORS_ORIGINS=https://darshi.app,https://www.darshi.app,https://api.darshi.app
FRONTEND_URL=https://darshi.app

# Cloudflare R2 Configuration (Add after setting up R2)
R2_ENDPOINT=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
R2_ACCESS_KEY=YOUR_R2_ACCESS_KEY
R2_SECRET_KEY=YOUR_R2_SECRET_KEY
R2_BUCKET_NAME=darshi-reports

# Gemini AI Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# Rate Limiting
RATE_LIMIT_ENABLED=true

# Email Configuration (Optional)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# SMS Configuration (Optional)
SMS_ENABLED=false
SMS_BACKEND=firebase

# Monitoring (Optional)
ENABLE_SENTRY=false
SENTRY_DSN=

# VAPID Keys (for push notifications)
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
ENVEOF

# Generate SECRET_KEY
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
sed -i "s/SECRET_KEY=CHANGE_ME_RUN_SCRIPT_TO_GENERATE/SECRET_KEY=$SECRET_KEY/" .env

print_success ".env file created (CONFIGURE BEFORE RUNNING)"

# Create systemd service
print_info "Creating systemd service..."
sudo bash -c "cat > /etc/systemd/system/darshi.service <<EOF
[Unit]
Description=Darshi Backend API
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=\"PATH=$APP_DIR/venv/bin\"
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=darshi

[Install]
WantedBy=multi-user.target
EOF"

print_success "Systemd service created"

# Create Nginx configuration
print_info "Creating Nginx configuration..."
sudo bash -c 'cat > /etc/nginx/sites-available/darshi <<EOF
# Rate limiting
limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=100r/m;

server {
    listen 80;
    server_name api.darshi.app;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Client body size
    client_max_body_size 20M;

    # Logging
    access_log /var/log/nginx/darshi_access.log;
    error_log /var/log/nginx/darshi_error.log;

    location / {
        # Rate limiting
        limit_req zone=api_limit burst=20 nodelay;

        # Proxy settings
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (no rate limit)
    location /health {
        proxy_pass http://localhost:8080;
        access_log off;
    }
}
EOF'

# Enable Nginx site
sudo ln -sf /etc/nginx/sites-available/darshi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
sudo nginx -t
sudo systemctl reload nginx
print_success "Nginx configured"

# Setup firewall
print_info "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw status
print_success "Firewall configured"

# Setup log rotation
print_info "Setting up log rotation..."
sudo bash -c 'cat > /etc/logrotate.d/darshi <<EOF
/var/log/nginx/darshi_*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 \$(cat /var/run/nginx.pid)
    endscript
}
EOF'
print_success "Log rotation configured"

# Create database migration script
cat > migrate_to_postgres.py <<'MIGEOF'
"""
Database migration script: Firestore to PostgreSQL
Run this after deploying to Azure to migrate existing data
"""
import os
from google.cloud import firestore
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

def migrate_firestore_to_postgres():
    # Initialize Firestore
    db = firestore.Client()

    # Connect to PostgreSQL
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    # Create tables
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            email TEXT,
            phone TEXT,
            password_hash TEXT,
            role TEXT DEFAULT 'citizen',
            auth_method TEXT,
            auth_provider TEXT,
            firebase_uid TEXT,
            email_verified BOOLEAN DEFAULT FALSE,
            phone_verified BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            last_login TIMESTAMPTZ,
            report_count INT DEFAULT 0,
            upvote_count INT DEFAULT 0,
            comment_count INT DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS reports (
            id UUID PRIMARY KEY,
            username TEXT REFERENCES users(username),
            title TEXT NOT NULL,
            description TEXT,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            geohash TEXT,
            location GEOGRAPHY(POINT, 4326),
            address TEXT,
            city TEXT,
            state TEXT,
            country TEXT,
            status TEXT DEFAULT 'PENDING_VERIFICATION',
            category TEXT,
            severity INT,
            image_urls TEXT[],
            image_hash TEXT,
            dhash TEXT,
            duplicate_of UUID,
            upvotes TEXT[],
            upvote_count INT DEFAULT 0,
            comment_count INT DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            verified_at TIMESTAMPTZ,
            resolved_at TIMESTAMPTZ,
            timeline JSONB
        );

        CREATE INDEX IF NOT EXISTS idx_reports_geohash ON reports(geohash);
        CREATE INDEX IF NOT EXISTS idx_reports_location ON reports USING GIST(location);
        CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);
        CREATE INDEX IF NOT EXISTS idx_reports_created_at ON reports(created_at DESC);

        CREATE TABLE IF NOT EXISTS comments (
            id UUID PRIMARY KEY,
            report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
            username TEXT REFERENCES users(username),
            text TEXT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            edited_at TIMESTAMPTZ
        );

        CREATE INDEX IF NOT EXISTS idx_comments_report_id ON comments(report_id);
    """)

    conn.commit()
    print("✓ Tables created")

    # Migrate users
    print("Migrating users...")
    users = db.collection('users').stream()
    user_data = []
    for user_doc in users:
        user = user_doc.to_dict()
        user_data.append((
            user_doc.id,
            user.get('email'),
            user.get('phone'),
            user.get('password_hash'),
            user.get('role', 'citizen'),
            user.get('auth_method'),
            user.get('auth_provider'),
            user.get('firebase_uid'),
            user.get('email_verified', False),
            user.get('phone_verified', False),
            user.get('created_at'),
            user.get('last_login'),
            user.get('report_count', 0),
            user.get('upvote_count', 0),
            user.get('comment_count', 0)
        ))

    if user_data:
        execute_values(cur, """
            INSERT INTO users (username, email, phone, password_hash, role, auth_method,
                             auth_provider, firebase_uid, email_verified, phone_verified,
                             created_at, last_login, report_count, upvote_count, comment_count)
            VALUES %s
            ON CONFLICT (username) DO NOTHING
        """, user_data)
        conn.commit()
        print(f"✓ Migrated {len(user_data)} users")

    # Migrate reports
    print("Migrating reports...")
    reports = db.collection('reports').stream()
    report_data = []
    for report_doc in reports:
        report = report_doc.to_dict()
        report_data.append((
            report_doc.id,
            report.get('username'),
            report.get('title'),
            report.get('description'),
            report.get('latitude'),
            report.get('longitude'),
            report.get('geohash'),
            f"POINT({report.get('longitude')} {report.get('latitude')})",
            report.get('address'),
            report.get('city'),
            report.get('state'),
            report.get('country'),
            report.get('status'),
            report.get('category'),
            report.get('severity'),
            report.get('image_urls', []),
            report.get('image_hash'),
            report.get('dhash'),
            report.get('duplicate_of'),
            report.get('upvotes', []),
            report.get('upvote_count', 0),
            report.get('comment_count', 0),
            report.get('created_at'),
            report.get('updated_at'),
            report.get('verified_at'),
            report.get('resolved_at'),
            report.get('timeline')
        ))

    if report_data:
        execute_values(cur, """
            INSERT INTO reports (id, username, title, description, latitude, longitude,
                               geohash, location, address, city, state, country, status,
                               category, severity, image_urls, image_hash, dhash, duplicate_of,
                               upvotes, upvote_count, comment_count, created_at, updated_at,
                               verified_at, resolved_at, timeline)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
        """, report_data)
        conn.commit()
        print(f"✓ Migrated {len(report_data)} reports")

    # Migrate comments
    print("Migrating comments...")
    comment_count = 0
    for report_doc in db.collection('reports').stream():
        comments = db.collection('reports').document(report_doc.id).collection('comments').stream()
        comment_data = []
        for comment_doc in comments:
            comment = comment_doc.to_dict()
            comment_data.append((
                comment_doc.id,
                report_doc.id,
                comment.get('username'),
                comment.get('text'),
                comment.get('created_at'),
                comment.get('edited_at')
            ))

        if comment_data:
            execute_values(cur, """
                INSERT INTO comments (id, report_id, username, text, created_at, edited_at)
                VALUES %s
                ON CONFLICT (id) DO NOTHING
            """, comment_data)
            comment_count += len(comment_data)

    conn.commit()
    print(f"✓ Migrated {comment_count} comments")

    cur.close()
    conn.close()
    print("\n✓ Migration complete!")

if __name__ == '__main__':
    migrate_firestore_to_postgres()
MIGEOF

chmod +x migrate_to_postgres.py
print_success "Migration script created: migrate_to_postgres.py"

print_info ""
print_info "=========================================="
print_info "Deployment Complete!"
print_info "=========================================="
print_info ""
print_info "Next Steps:"
print_info "1. Copy your application code to: $APP_DIR"
print_info "2. Configure .env file with:"
print_info "   - Cloudflare R2 credentials"
print_info "   - Gemini API key"
print_info "   - VAPID keys"
print_info "3. Run database migration: python migrate_to_postgres.py"
print_info "4. Start services:"
print_info "   sudo systemctl start darshi"
print_info "   sudo systemctl enable darshi"
print_info "5. Check status: sudo systemctl status darshi"
print_info "6. View logs: sudo journalctl -u darshi -f"
print_info "7. Setup SSL: sudo certbot --nginx -d api.darshi.app"
print_info ""
print_info "Database credentials:"
print_info "   Database: darshi"
print_info "   User: darshi_user"
print_info "   Password: darshi_secure_password_change_me (CHANGE THIS!)"
print_info ""
print_info "Verify installation:"
print_info "   curl http://localhost:8080/health"
print_info ""
