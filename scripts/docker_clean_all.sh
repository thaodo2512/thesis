#!/bin/bash

# This script cleans up Docker resources to free up storage space.
# It stops and removes all containers, removes all images, prunes build cache,
# volumes, networks, and performs a full system prune.
# WARNING: This will delete ALL Docker data, including images and containers.
# Use with caution! Run as root or with sudo if necessary.

echo "WARNING: This script will remove ALL Docker containers, images, volumes, networks, and build cache."
echo "Press Ctrl+C to cancel, or Enter to continue."
read -p ""

# Stop all running containers
echo "Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

# Remove all containers (stopped or not)
echo "Removing all containers..."
docker rm -f $(docker ps -aq) 2>/dev/null || true

# Remove all images
echo "Removing all images..."
docker rmi -f $(docker images -aq) 2>/dev/null || true

# Prune build cache
echo "Pruning build cache..."
docker builder prune -a -f 2>/dev/null || true

# Prune volumes
echo "Pruning volumes..."
docker volume prune -a -f 2>/dev/null || true

# Prune networks
echo "Pruning networks..."
docker network prune -f 2>/dev/null || true

# Full system prune (for anything missed)
echo "Performing full system prune..."
docker system prune -a -f --volumes 2>/dev/null || true

echo "Cleanup complete. Check disk space with 'df -h'."
