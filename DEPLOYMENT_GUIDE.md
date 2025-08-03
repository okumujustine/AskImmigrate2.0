# AskImmigrate2.0 Deployment Guide
**Author**: Hillary Arinda  
**Version**: 1.0  
**Date**: August 2025

## 📋 Overview

This guide provides comprehensive instructions for deploying AskImmigrate2.0 in production environments. The system is a multi-agent AI immigration assistant with session management, tool orchestration, and comprehensive security measures.

## 🏗️ System Architecture

### Core Components
- **Manager Agent**: Strategic analysis and tool orchestration
- **Synthesis Agent**: Session-aware response generation
- **Reviewer Agent**: Quality control and validation
- **Session Manager**: SQLite-based conversation persistence
- **Input Validation**: Security and sanitization layer
- **Retry Logic**: Resilience for LLM and tool calls

### Data Flow
```
User Input → Input Validation → Manager Agent → Tool Execution → Synthesis Agent → Reviewer Agent → Response
                    ↓
              Session Manager (SQLite Database)
```

## 🔧 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: 2GB available space (including models)
- **Network**: Internet connection for LLM APIs and web search

### Required Services
- **LLM Provider**: OpenAI, Groq, or HuggingFace
- **Vector Database**: ChromaDB (included)
- **Session Storage**: SQLite (included)

## 📦 Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/okumujustine/AskImmigrate2.0.git
cd AskImmigrate2.0
```

### 2. Set Up Python Environment
```bash
# Create virtual environment
python -m venv askimmigrate_env

# Activate environment
# On Windows:
askimmigrate_env\Scripts\activate
# On macOS/Linux:
source askimmigrate_env/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

### 3. Install Dependencies
```bash
# Install runtime dependencies
pip install -r requirements.txt

# Install testing dependencies (optional)
pip install -r requirements-test.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# LLM Configuration (choose one)
OPENAI_API_KEY=your_openai_api_key_here
GROQ_API_KEY=your_groq_api_key_here
HUGGINGFACE_API_TOKEN=your_hf_token_here

# Web Search Configuration (required)
TAVILY_API_KEY=your_tavily_api_key_here

# Optional: LangSmith Tracing and Monitoring
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your_langsmith_api_key_here
LANGSMITH_PROJECT="AksImmigrate2.0"

# Application Configuration
APP_ENV=production
LOG_LEVEL=INFO
SESSION_TIMEOUT=3600

# Database Configuration
DATABASE_PATH=backend/outputs/sessions.db

# Security Configuration
MAX_QUERY_LENGTH=5000
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60

# Performance Configuration
LLM_TIMEOUT=30
TOOL_TIMEOUT=15
MAX_RETRIES=3
```

#### Environment Variables Explained

**Required Variables:**
- `GROQ_API_KEY` or `OPENAI_API_KEY`: Choose one LLM provider
  - Groq: Fast, free tier available - Get from [console.groq.com](https://console.groq.com/keys)
  - OpenAI: Requires billing - Get from [platform.openai.com](https://platform.openai.com/api-keys)
- `TAVILY_API_KEY`: Web search functionality - Get from [tavily.com](https://tavily.com)

**Optional Variables:**
- `LANGSMITH_*`: LangChain tracing and monitoring
  - `LANGSMITH_TRACING`: Enable/disable tracing (true/false)
  - `LANGSMITH_ENDPOINT`: LangSmith API endpoint
  - `LANGSMITH_API_KEY`: Your LangSmith API key
  - `LANGSMITH_PROJECT`: Project name for organizing traces

**System Configuration:**
- `APP_ENV`: Application environment (development/production)
- `LOG_LEVEL`: Logging verbosity (DEBUG/INFO/WARNING/ERROR)
- `SESSION_TIMEOUT`: Session expiration time in seconds
- `MAX_QUERY_LENGTH`: Maximum input query length
- `RATE_LIMIT_*`: API rate limiting configuration

### 5. Initialize Data and Models

```bash
# Download spaCy model (if not already included)
python -m spacy download en_core_web_trf

# Initialize vector database
python -c "from backend.code.embed_documents import main; main()"

# Test database connection
python -c "from backend.code.session_manager import test_connection; test_connection()"
```

## 🚀 Deployment Options

### Option 1: Local Development
```bash
# Start CLI interface
python main.py

# Or start web interface
python -m backend.code.api
```

### Option 2: FastAPI Production Server
```bash
# Install production server
pip install uvicorn[standard] gunicorn

# Start with uvicorn
uvicorn backend.code.api:app --host 0.0.0.0 --port 8000 --workers 4

# Or with gunicorn (recommended for production)
gunicorn backend.code.api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Option 3: Docker Deployment

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Download spaCy model
RUN python -m spacy download en_core_web_trf

# Create logs directory
RUN mkdir -p backend/outputs/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["uvicorn", "backend.code.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  askimmigrate:
    build: .
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
    env_file:
      - .env
    volumes:
      - ./backend/outputs:/app/backend/outputs
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - askimmigrate
    restart: unless-stopped
```

Deploy with Docker:
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Scale application
docker-compose up -d --scale askimmigrate=3
```

## ⚙️ Configuration

### Application Configuration (`backend/config/config.yaml`)
```yaml
llm: "gpt-4o-mini"
max_conversation_turns: 10
session_timeout_hours: 24
enable_web_search: true
enable_fee_calculator: true
log_level: "INFO"

retry_config:
  max_attempts: 3
  base_delay: 1.0
  max_delay: 30.0

validation_config:
  max_query_length: 5000
  min_query_length: 3
  rate_limit_per_minute: 60
```

### Prompt Configuration (`backend/config/prompt_config.yaml`)
```yaml
manager_agent_prompt:
  system_message: |
    You are an expert immigration manager agent responsible for strategic analysis
    of user immigration queries and tool orchestration decisions.
  
  analysis_framework: |
    Analyze the query for:
    1. Question type (factual, procedural, advisory)
    2. Visa categories involved
    3. Required tools (RAG, web search, fee calculator)
    4. Complexity level (simple, moderate, complex)
```

## 🔒 Security Configuration

### Input Validation Settings
- **Maximum query length**: 5000 characters
- **Rate limiting**: 60 requests per minute per session
- **Injection protection**: XSS, SQL injection detection
- **Content sanitization**: HTML escaping, control character removal

### API Security
```bash
# Generate secure session keys
python -c "import secrets; print(secrets.token_hex(32))"

# Set in environment
export SESSION_SECRET_KEY=your_generated_key_here
```

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

## 📊 Monitoring and Logging

### Log Configuration
Logs are written to `backend/outputs/logs/askimmigrate.jsonl` in JSON Lines format.

### Health Checks
The system provides health check endpoints:
- `/health` - Basic health status
- `/health/detailed` - Detailed component status
- `/metrics` - Performance metrics

### Monitoring Setup
```python
# Example monitoring script
import requests
import time
import logging

def monitor_health():
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            logging.info("Health check passed")
        else:
            logging.error(f"Health check failed: {response.status_code}")
    except Exception as e:
        logging.error(f"Health check error: {e}")

# Run every 30 seconds
while True:
    monitor_health()
    time.sleep(30)
```

## 🔧 Maintenance

### Database Maintenance
```bash
# Backup sessions database
cp backend/outputs/sessions.db backend/outputs/sessions_backup_$(date +%Y%m%d).db

# Clean old sessions (older than 30 days)
python -c "
from backend.code.session_manager import cleanup_old_sessions
cleanup_old_sessions(days=30)
"
```

### Log Rotation
```bash
# Setup logrotate for application logs
cat > /etc/logrotate.d/askimmigrate << EOF
/app/backend/outputs/logs/*.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

### Updates and Patches
```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade

# Restart application
sudo systemctl restart askimmigrate
```

## 🧪 Testing Deployment

### Basic Functionality Test
```bash
# Test CLI interface
echo "How do I apply for H-1B visa?" | python main.py

# Test API endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the H-1B filing fee?", "session_id": "test-123"}'
```

### Load Testing
```bash
# Install testing tools
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

### Integration Testing
```bash
# Run full test suite
python -m pytest backend/code/tests/ -v --cov=backend/code
```

## 📈 Performance Optimization

### Database Optimization
```sql
-- Create indexes for better query performance
CREATE INDEX idx_sessions_session_id ON conversations(session_id);
CREATE INDEX idx_sessions_timestamp ON conversations(timestamp);
```

### Caching Configuration
```python
# Redis caching (optional)
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=300  # 5 minutes
```

### Resource Limits
```bash
# Set resource limits in systemd service
[Service]
LimitNOFILE=65536
LimitNPROC=4096
MemoryMax=2G
CPUQuota=200%
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Import Errors
```bash
# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Install missing dependencies
pip install -r requirements.txt
```

#### 2. Database Connection Issues
```bash
# Check database file permissions
ls -la backend/outputs/sessions.db

# Reset database
rm backend/outputs/sessions.db
python -c "from backend.code.session_manager import create_tables; create_tables()"
```

#### 3. LLM API Issues
```bash
# Test API connectivity
python -c "
from backend.code.llm import get_llm
llm = get_llm('gpt-4o-mini')
print('LLM connection successful')
"
```

#### 4. Memory Issues
```bash
# Check memory usage
ps aux | grep python
free -h

# Restart application
sudo systemctl restart askimmigrate
```

### Log Analysis
```bash
# Check recent errors
tail -f backend/outputs/logs/askimmigrate.jsonl | grep '"level":"ERROR"'

# Parse JSON logs
cat backend/outputs/logs/askimmigrate.jsonl | jq '.message'
```

## 🔄 Backup and Recovery

### Backup Script
```bash
#!/bin/bash
# backup_askimmigrate.sh

BACKUP_DIR="/backups/askimmigrate"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp backend/outputs/sessions.db $BACKUP_DIR/sessions_$DATE.db

# Backup configuration
tar -czf $BACKUP_DIR/config_$DATE.tar.gz backend/config/

# Backup logs (last 7 days)
find backend/outputs/logs/ -name "*.jsonl" -mtime -7 -exec cp {} $BACKUP_DIR/ \;

echo "Backup completed: $BACKUP_DIR"
```

### Recovery Process
```bash
# Restore database
cp /backups/askimmigrate/sessions_YYYYMMDD_HHMMSS.db backend/outputs/sessions.db

# Restore configuration
tar -xzf /backups/askimmigrate/config_YYYYMMDD_HHMMSS.tar.gz

# Restart services
sudo systemctl restart askimmigrate
```

## 📞 Support and Maintenance

### Health Monitoring
- Monitor health endpoints every 30 seconds
- Set up alerts for failed health checks
- Track response times and error rates

### Regular Maintenance Tasks
- **Daily**: Check logs for errors
- **Weekly**: Backup database and configurations
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Performance review and optimization

### Contact Information
- **Technical Lead**: Hillary Arinda
- **Repository**: https://github.com/okumujustine/AskImmigrate2.0
- **Documentation**: See README.md and project guidelines

---

**Note**: This deployment guide assumes familiarity with basic system administration. For production deployments, consider consulting with a DevOps engineer for infrastructure-specific optimizations.
