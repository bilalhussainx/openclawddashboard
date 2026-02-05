#!/bin/bash

echo "========================================"
echo "OpenClaw Dashboard - Development Setup"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "ERROR: Docker is not running. Please start Docker first."
    exit 1
fi

echo "Starting Docker containers (PostgreSQL, Redis, Backend, Celery)..."
cd docker
docker-compose -f docker-compose.dev.yml up -d --build

echo ""
echo "Waiting for services to be ready..."
sleep 10

echo ""
echo "Running database migrations and seeding data..."
docker-compose -f docker-compose.dev.yml exec backend python manage.py migrate --noinput
docker-compose -f docker-compose.dev.yml exec backend python manage.py seed_data

echo ""
echo "========================================"
echo "Backend is running at: http://localhost:8000"
echo "Admin panel: http://localhost:8000/admin"
echo ""
echo "Test user credentials:"
echo "  Email: test@example.com"
echo "  Password: testpass123"
echo "========================================"
echo ""

# Start frontend in background
echo "Starting the frontend..."
cd ../frontend
npm install
npm run dev &

echo ""
echo "========================================"
echo "Frontend is running at: http://localhost:3000"
echo "========================================"
echo ""
echo "Press Ctrl+C to stop all services"

# Follow docker logs
cd ../docker
docker-compose -f docker-compose.dev.yml logs -f
