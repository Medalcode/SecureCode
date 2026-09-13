# SECURECODE — Development Makefile
# Shorthand commands for common development tasks

.PHONY: help setup dev test lint format clean deploy

help:
	@echo "SECURECODE — Development Commands"
	@echo "=================================="
	@echo "make setup       - Initialize development environment"
	@echo "make dev         - Start development server (reload on changes)"
	@echo "make test        - Run all tests with coverage"
	@echo "make test-unit   - Run unit tests only"
	@echo "make test-int    - Run integration tests"
	@echo "make lint        - Run linting (flake8, black check)"
	@echo "make format      - Auto-format code with black"
	@echo "make db-migrate  - Run database migrations"
	@echo "make db-reset    - Reset database (dev only)"
	@echo "make clean       - Clean build artifacts and cache"
	@echo "make install     - Install dependencies"
	@echo "make docs        - Open API documentation"
	@echo ""

setup:
	@bash setup.sh

dev:
	@echo "Starting development server..."
	@uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "Running all tests with coverage..."
	@pytest tests/ -v --cov=app --cov-report=html
	@echo "Coverage report: htmlcov/index.html"

test-unit:
	@pytest tests/unit/ -v

test-int:
	@pytest tests/integration/ -v

test-gt:
	@pytest tests/ground_truth_validation.py -v

lint:
	@echo "Running linters..."
	@flake8 app tests --count --select=E9,F63,F7,F82 --show-source
	@black --check app tests
	@echo "✓ Linting passed"

format:
	@echo "Formatting code..."
	@black app tests
	@isort app tests
	@echo "✓ Formatting complete"

db-migrate:
	@alembic upgrade head
	@echo "✓ Database migrated"

db-reset:
	@echo "⚠️  Resetting database (dev only)..."
	@alembic downgrade base
	@alembic upgrade head
	@python -c "from app.scripts.seed import seed_db; seed_db()"
	@echo "✓ Database reset"

clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -rf .pytest_cache build dist *.egg-info htmlcov .coverage
	@echo "✓ Cleaned"

install:
	@pip install -r requirements.txt -r requirements-dev.txt

docs:
	@echo "Opening API documentation..."
	@python -m webbrowser http://localhost:8000/docs

security-check:
	@echo "Running security checks..."
	@bandit -r app -ll
	@echo "✓ No critical security issues"

load-test:
	@echo "Running load tests (Locust)..."
	@locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 60s

docker-build:
	@docker build -f docker/Dockerfile -t securecode:latest .

docker-run:
	@docker-compose up

all: clean lint test format
	@echo "✅ All checks passed"

