# 🚀 Production Deployment Guide

This guide helps you deploy Paper Agent to serve many users in production.

## Quick Start

1. **Run Production Setup**:
   ```bash
   python scripts/setup_production.py
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start Production Server**:
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## ⚡ Production-Ready Features

✅ **Rate Limiting**: 30 searches/min, 5 feedback/hour per IP
✅ **Input Validation**: XSS protection, category validation
✅ **Error Monitoring**: Comprehensive logging & health checks
✅ **Database Optimization**: WAL mode, indexes, caching
✅ **CORS Security**: Environment-based origin control
✅ **Performance Monitoring**: Slow query detection

## 🔧 Environment Configuration

Key `.env` variables for production:

```bash
# Required for production
ENVIRONMENT=production
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Rate limiting (optional, has defaults)
RATE_LIMIT_SEARCH=30
RATE_LIMIT_GRAPH=10
RATE_LIMIT_FEEDBACK=5

# External APIs (optional but recommended)
HUGGINGFACE_API_KEY=your_key_here
GITHUB_TOKEN=your_token_here
```

## 🔐 Security Checklist

- [x] **Rate Limiting**: Prevents API abuse
- [x] **Input Sanitization**: Removes HTML/script tags
- [x] **CORS Configuration**: Restricts allowed origins
- [x] **Error Handling**: No internal details leaked
- [ ] **HTTPS/SSL**: Set up reverse proxy (nginx)
- [ ] **Authentication**: Add for admin features
- [ ] **Monitoring**: Set up external health checks

## 📊 Current Scalability Limits

### SQLite (Current)
- **Max concurrent users**: ~50-100
- **Database size limit**: ~500MB for good performance
- **Search response time**: <1 second with current dataset

### Recommended Upgrades for 1000+ Users

1. **Database**: Migrate to PostgreSQL
2. **Caching**: Add Redis layer
3. **User System**: Add authentication
4. **Infrastructure**: Load balancer + multiple instances

## 🖥️ Deployment Options

### Option 1: Simple VPS (Recommended for Start)

```bash
# Install dependencies
sudo apt update && sudo apt install nginx python3-pip

# Clone and setup
git clone your-repo
cd paper-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/setup_production.py

# Configure nginx (see nginx.conf example below)
sudo systemctl enable nginx
sudo systemctl start nginx
```

### Option 2: Docker Container

```dockerfile
# Dockerfile included in repo
docker build -t paper-agent .
docker run -p 8000:8000 --env-file .env paper-agent
```

### Option 3: Cloud Platform (Heroku, Railway, etc.)

Use the included `Procfile` and `runtime.txt`.

## 🌐 Nginx Configuration

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration (use Let's Encrypt)
    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;

    # API and static files
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for slow operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static assets with caching
    location /assets {
        alias /path/to/paper-agent/frontend/dist/assets;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## 📈 Monitoring

### Health Check Endpoint

```bash
curl https://yourdomain.com/api/health
```

Returns system metrics:
- Database size and performance
- Memory/CPU usage
- Recent activity
- Warnings for critical issues

### Log Monitoring

```bash
# Application logs
tail -f logs/app.log

# Check for errors
grep ERROR logs/app.log

# Monitor slow requests
grep "Slow request" logs/app.log
```

### Automated Monitoring

Set up external monitoring (UptimeRobot, Pingdom) for:
- `/api/health` endpoint
- Response time alerts
- Database size monitoring

## 🔄 Maintenance

### Daily Tasks (Automated)

- arXiv paper collection (5:00 AM UTC)
- Database optimization (weekly)
- Log rotation

### Manual Tasks

```bash
# Check system status
python scripts/setup_production.py

# Backup database
cp data/papers.db backups/papers_$(date +%Y%m%d).db

# Update papers (manual trigger)
source .venv/bin/activate
python src/collector/daily_collect.py
```

## 🚨 Troubleshooting

### High Memory Usage

1. Check database size: May need PostgreSQL migration
2. Restart application server
3. Add swap if needed

### Slow Response Times

1. Check `/api/health` for system metrics
2. Consider adding Redis caching
3. Optimize database queries

### Rate Limiting Issues

1. Check logs for blocked IPs
2. Adjust limits in `.env` if needed
3. Consider IP whitelist for trusted users

## 📞 Support

- Check health endpoint: `/api/health`
- Review logs in `logs/` directory
- Use production setup script for diagnostics

## 🎯 Performance Targets

- **Response time**: <2 seconds for search
- **Uptime**: >99.5%
- **Concurrent users**: 100+ (current), 1000+ (with PostgreSQL)
- **Search accuracy**: Maintained with production optimizations