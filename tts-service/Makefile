# TTS Microservice Makefile

.PHONY: help install dev test lint format build run docker-build docker-run clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install     Install dependencies"
	@echo "  dev         Run in development mode"
	@echo "  test        Run tests"
	@echo "  lint        Run linting"
	@echo "  format      Format code"
	@echo "  build       Build Docker image"
	@echo "  run         Run the application"
	@echo "  docker-run  Run with Docker Compose"
	@echo "  clean       Clean up"

# Install dependencies
install:
	pip install -r requirements.txt

# Run in development mode
dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info

# Run tests
test:
	pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# Run linting
lint:
	flake8 app/ tests/
	mypy app/

# Format code
format:
	black app/ tests/
	isort app/ tests/

# Build Docker image
build:
	docker build -t tts-service:latest .

# Run the application
run:
	python -m app.main

# Run with Docker Compose (includes monitoring)
docker-run:
	docker-compose up --build

# Clean up
clean:
	docker-compose down
	docker system prune -f
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .mypy_cache

# Setup development environment
setup-dev:
	cp .env.example .env
	@echo "Please edit .env file with your ElevenLabs API key"

# Load test
load-test:
	python tests/load_test.py

# Check health
health:
	curl -f http://localhost:8000/v1/tts/health || exit 1

# View logs
logs:
	docker-compose logs -f tts-service

# Restart service
restart:
	docker-compose restart tts-service