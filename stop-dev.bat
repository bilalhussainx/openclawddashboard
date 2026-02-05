@echo off
echo Stopping OpenClaw Dashboard containers...
cd docker
docker-compose -f docker-compose.dev.yml down
echo Done!
pause
