#!/usr/bin/env bash
set -e

echo "Pulling latest from main..."
git pull origin main

echo "Rebuilding and restarting containers..."
docker compose up --build -d

echo "Done. Services:"
docker compose ps
