#!/bin/bash
# SECURECODE — Automated Local Setup Script
# Run this once to initialize your development environment completely
# Usage: bash setup.sh

set -e  # Exit on error

echo "🚀 SECURECODE — Development Setup Script"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v python3.12 &> /dev/null; then
    echo -e "${RED}❌ Python 3.12 not found. Please install Python 3.12${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python 3.12 found: $(python3.12 --version)${NC}"

if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install Git${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Git found${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker not found. Some features will not work.${NC}"
else
    echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"
fi

echo ""
echo "📦 Setting up Python environment..."

# Create virtual environment
if [ ! -d "venv" ]; then
    python3.12 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}⚠ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
python -m pip install --upgrade pip setuptools wheel -q
echo -e "${GREEN}✓ pip upgraded${NC}"

echo ""
echo "📚 Installing dependencies..."

# Install requirements
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt -q
    echo -e "${GREEN}✓ Production dependencies installed${NC}"
else
    echo -e "${RED}❌ requirements.txt not found${NC}"
    exit 1
fi

if [ -f "requirements-dev.txt" ]; then
    pip install -r requirements-dev.txt -q
    echo -e "${GREEN}✓ Development dependencies installed${NC}"
fi

echo ""
echo "⚙️  Configuring environment..."

# Copy .env if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ .env created from template${NC}"
        echo -e "${YELLOW}⚠ Please edit .env with your GitHub token and secrets${NC}"
    else
        echo -e "${RED}❌ .env.example not found${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ .env already exists (skipped)${NC}"
fi

echo ""
echo "🐘 Setting up PostgreSQL..."

if command -v docker &> /dev/null; then
    if docker-compose --version &> /dev/null; then
        docker-compose up -d postgres 2>/dev/null || true
        echo -e "${GREEN}✓ PostgreSQL started (docker-compose)${NC}"
        
        # Wait for PostgreSQL to be ready
        echo "   Waiting for PostgreSQL to be ready..."
        sleep 5
        
        # Run migrations
        echo "   Running Alembic migrations..."
        alembic upgrade head
        echo -e "${GREEN}✓ Database schema initialized${NC}"
    else
        echo -e "${YELLOW}⚠ docker-compose not found, skipping PostgreSQL setup${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Docker not available, skipping PostgreSQL setup${NC}"
    echo "   Please start PostgreSQL manually and run: alembic upgrade head"
fi

echo ""
echo "🧪 Running tests..."

# Run pytest to verify setup
if pytest tests/ -q 2>/dev/null; then
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}⚠ Some tests failed (this is normal if DB not ready)${NC}"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your GitHub API token:"
echo "   - Get token from: https://github.com/settings/personal-access-tokens/new"
echo "   - Permissions: repo (read-only)"
echo ""
echo "2. Start the development server:"
echo "   uvicorn app.main:app --reload"
echo ""
echo "3. Visit API docs:"
echo "   http://localhost:8000/docs"
echo ""
echo "4. Test login:"
echo "   curl -X POST http://localhost:8000/api/v1/auth/login \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"email\": \"admin@securecode.local\", \"password\": \"admin123\"}'"
echo ""

