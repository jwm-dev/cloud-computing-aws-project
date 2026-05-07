#!/usr/bin/env bash
set -e
# Usage: ./deploy_ec2.sh <instance-ip> <path-to-key.pem>
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <instance-ip> <key.pem>"; exit 1
fi
HOST=$1
KEY=$2
REPO=hidden-agenda
ssh -o StrictHostKeyChecking=no -i "$KEY" ubuntu@${HOST} <<'SSH'
  sudo apt update
  sudo apt install -y docker.io git
  mkdir -p ~/app
  cd ~/app
  # Assume repo is copied via scp
  # Build and run
  docker build -t hidden-agenda:latest .
  docker run -d --restart unless-stopped -p 8000:8000 --name hidden-agenda hidden-agenda:latest
SSH

echo "Deployed to ${HOST}."
