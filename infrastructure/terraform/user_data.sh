#!/usr/bin/env bash
# EC2 user-data script: bootstraps Docker, pulls the repo, and starts services.
# Template variables: ${s3_bucket_name}, ${aws_region}
set -euo pipefail

# ---- System update & Docker install ----
dnf update -y
dnf install -y docker git

systemctl enable --now docker
usermod -aG docker ec2-user

# ---- Docker Compose (v2 plugin) ----
DOCKER_COMPOSE_VERSION="v2.27.0"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL \
  "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# ---- Clone repository ----
APP_DIR="/opt/hidden-agenda-rl-gym"
git clone https://github.com/jwm-dev/cloud-computing-aws-project.git "$APP_DIR"
cd "$APP_DIR"

# ---- Write environment file ----
cat > .env <<EOF
S3_BUCKET_NAME=${s3_bucket_name}
AWS_REGION=${aws_region}
EOF

# ---- Start services ----
docker compose up -d --build

# ---- Systemd service to restart on reboot ----
cat > /etc/systemd/system/hidden-agenda.service <<'UNIT'
[Unit]
Description=Hidden Agenda RL Gym
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/hidden-agenda-rl-gym
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose up -d
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
UNIT

systemctl enable hidden-agenda.service
