# Django Vue MCP Server - Makefile

.PHONY: help build test run dev clean install lint format

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install Python dependencies"
	@echo "  build      - Build Docker images"
	@echo "  run        - Run MCP server locally"
	@echo "  dev        - Run development environment with Docker Compose"
	@echo "  test       - Run test suite"
	@echo "  test-local - Test server without Docker"
	@echo "  lint       - Run code linting"
	@echo "  format     - Format code with black and isort"
	@echo "  clean      - Clean up Docker containers and images"
	@echo "  logs       - Show Docker logs"

# Installation
install:
	pip install -r requirements.txt

# Docker commands
build:
	docker compose build

run:
	docker compose up

dev:
	docker compose up -d
	@echo "Development environment started. Use 'make logs' to view logs."

clean:
	docker compose down -v
	docker system prune -f

logs:
	docker compose logs -f mcp-server

# Testing
test:
	docker compose run --rm mcp-server python -m pytest tests/ -v

test-local:
	python src/test_server.py

# Code quality
lint:
	python -m pylint src/ --disable=C0114,C0116
	python -m mypy src/ --ignore-missing-imports

format:
	python -m black src/ tests/
	python -m isort src/ tests/

# Development helpers
shell:
	docker compose run --rm mcp-server /bin/bash

redis-cli:
	docker compose exec redis redis-cli

# Production deployment
deploy-prod:
	docker compose -f docker-compose.prod.yml up -d

stop-prod:
	docker compose -f docker-compose.prod.yml down

# Environment setup
setup-env:
	cp .env.example .env
	@echo "Environment file created. Please edit .env with your settings."

# Git helpers
git-init:
	git add .
	git commit -m "Initial commit: Django Vue MCP Server setup"

# Health check
health:
	curl -f http://localhost:8000/health || echo "Server not responding"