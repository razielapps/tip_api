# 🎯 Tip API - Advanced Match Prediction API

A production-ready Django REST API for fetching football match tips with money flow analysis.

## 🌟 Features

- **🏆 Single Endpoint**: Handle both normal and underdog tips in one function
- **💰 Credit System**: 100 credits with proxy, 200 without proxy (new users get 1000 free credits)
- **🔐 Secure Authentication**: Token-based authentication with API keys
- **🌐 Proxy Support**: Built-in proxy rotation and management
- **⚡ Real-time Scanning**: Live match data from multiple sources
- **📊 Comprehensive Logging**: Track all API requests and credit usage
- **📈 Rate Limiting**: 100 requests per minute per user
- **🐳 Docker Ready**: Full Docker and Docker Compose setup
- **📚 Swagger Docs**: Auto-generated API documentation
- **🔍 Advanced Filtering**: Multiple parameters for precise match queries

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (optional)

### Installation

#### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/tip-api.git
cd tip-api

# Copy environment variables
cp .env.example .env
# Edit .env with your configuration
nano .env

# Start with Docker Compose
docker-compose up -d

# Run migrations
docker-compose exec web python manage.py migrate
```

#### Option 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/tip-api.git
cd tip-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your credentials
nano .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

### Environment Variables

Create a `.env` file with:

```env
# Django
DEBUG=False
DJANGO_SECRET_KEY=your-super-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DB_NAME=tip_api
DB_USER=postgres
DB_PASSWORD=your-strong-password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# API Settings
DEFAULT_USER_CREDITS=1000
API_REQUEST_COST_WITH_PROXY=100
API_REQUEST_COST_WITHOUT_PROXY=200
```

## 🛠 API Usage

### Authentication

#### Register User
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yourusername",
    "email": "your@email.com",
    "password": "securepassword123"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "yourusername",
    "password": "securepassword123"
  }'
```

Response includes your API token for all future requests.

### Fetch Match Tips

#### Basic Query (Normal Tips with Proxy - 100 credits)
```bash
curl -X GET http://localhost:8000/api/matches/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tip_type": "normal",
    "mode": "normal",
    "live_only": false,
    "exclude_major": false,
    "time_order": false,
    "limit": 10,
    "use_proxy": true
  }'
```

#### Underdog Tips (Without Proxy - 200 credits)
```bash
curl -X GET http://localhost:8000/api/matches/ \
  -H "Authorization: Token YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tip_type": "underdog",
    "mode": "safe",
    "live_only": false,
    "exclude_major": true,
    "time_order": true,
    "limit": 5,
    "use_proxy": false
  }'
```

### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `tip_type` | string | `normal` | `normal` or `underdog` tips |
| `mode` | string | `normal` | `normal` (69%+ confidence) or `safe` (75%+ confidence) |
| `live_only` | boolean | `false` | Return only live matches |
| `exclude_major` | boolean | `false` | Exclude major leagues (EPL, La Liga, etc.) |
| `time_order` | boolean | `false` | Order matches by kickoff time |
| `limit` | integer | `10` | Number of matches (1-100) |
| `use_proxy` | boolean | `false` | Use proxy for request (cheaper: 100 credits) |

## 📊 API Response Format

```json
{
  "success": true,
  "count": 10,
  "credits_used": 100,
  "credits_remaining": 900,
  "matches": [
    {
      "league": "Premier League",
      "match": "Arsenal vs Chelsea",
      "match_kickoff": "2024-01-15T20:00:00",
      "pick": "Arsenal",
      "odds": 2.10,
      "percentage": 82.5,
      "market": "1X2",
      "is_hot": true,
      "total_money": 15000.00,
      "dominant_money": 12375.00
    }
  ]
}
```

## 🏗 Architecture

```
Client → Nginx → Django API → Scanner → Betwatch API
           ↓           ↓           ↓
        Redis     PostgreSQL    Proxy Pool
```

## 🔧 Advanced Configuration

### Proxy Setup

1. **Add Proxies via Admin Panel:**
   - Access `/admin/`
   - Navigate to Proxies
   - Add proxies in format: `http://username:password@host:port`

2. **User-specific Proxies:**
   Users can configure their own proxies in profile settings

### Credit Management

- New users: 1000 credits
- With proxy: 100 credits per request
- Without proxy: 200 credits per request
- Purchase additional credits via API

### Rate Limiting
- 100 requests per minute per user
- Configure in `settings.py`

## 📈 Production Deployment

### Deploy with Docker

```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml up -d --build

# Check logs
docker-compose -f docker-compose.prod.yml logs -f

# Scale workers
docker-compose -f docker-compose.prod.yml up -d --scale celery=4
```

### Deploy on AWS ECS

```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker build -t tip-api .
docker tag tip-api:latest YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/tip-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.REGION.amazonaws.com/tip-api:latest

# Deploy to ECS
aws ecs update-service --cluster tip-api-cluster --service tip-api-service --force-new-deployment
```

### Deploy on Heroku

```bash
# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy
git push heroku main

# Set up database
heroku addons:create heroku-postgresql:hobby-dev
heroku addons:create heroku-redis:hobby-dev

# Run migrations
heroku run python manage.py migrate
```

## 🔍 Finding Internal APIs for Match Tips

### Where to Look:

1. **Sports Betting Websites:**
   - Use browser DevTools (F12)
   - Check Network tab for API calls
   - Look for WebSocket connections
   - Monitor XHR requests

2. **Mobile Apps:**
   - Use Charles Proxy or mitmproxy
   - Decrypt HTTPS traffic
   - Capture API endpoints

3. **Common Patterns:**
   - `/api/matches/`
   - `/api/odds/`
   - `/api/live/`
   - `/v1/events`

4. **Key Headers to Check:**
   - `Authorization: Bearer`
   - `X-API-Key`
   - Custom authentication headers

### Important Notes:

⚠️ **Legal Disclaimer**: Only access public APIs or APIs you have permission to use. Respect rate limits and terms of service.

## 🚨 Troubleshooting

### Common Issues:

1. **Database Connection Failed:**
   ```bash
   # Check PostgreSQL is running
   sudo systemctl status postgresql
   
   # Create database
   sudo -u postgres createdb tip_api
   ```

2. **Redis Connection Issues:**
   ```bash
   # Start Redis
   sudo systemctl start redis-server
   
   # Test connection
   redis-cli ping
   ```

3. **API Token Not Working:**
   ```bash
   # Generate new token
   python manage.py drf_create_token username
   ```

4. **Proxy Errors:**
   - Check proxy format
   - Verify proxy credentials
   - Test proxy connectivity

## 📚 Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/documentation)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Need Help?

Having trouble getting the API running? Need help with configuration or deployment?

### 📩 **DM Me for Special Guidance!**

I can provide:
- Complete setup assistance
- Custom configuration
- Production deployment help
- Advanced API integration
- Proxy setup guidance
- Performance optimization

**Contact Options:**
- 📧 Email: avtxconscience@gmail.com


### What I Can Help With:

1. **Full Setup Assistance**: Walk you through the entire installation
2. **Proxy Configuration**: Help set up and manage proxy rotation
3. **API Integration**: Guide on integrating with your existing systems
4. **Production Deployment**: Assist with Docker, AWS, Heroku deployment
5. **Custom Features**: Add specific features you need
6. **Performance Tuning**: Optimize for high traffic loads

**Quick Help Format:**
```
Subject: Tip API Help Needed

Current Setup: [Docker/Manual/AWS/etc]
Issue: [Brief description]
What I've tried: [Steps taken]
Error Messages: [Copy error logs]
```

Don't struggle alone! Reach out for personalized help to get your API running smoothly. 🚀

---

**Made with ❤️ for the betting analysis community**

*Disclaimer: This API is for educational and analytical purposes only. Always gamble responsibly and within legal boundaries and i do not support or encourage gambling, stricly for analytical, educational and experimental purposes only.*
