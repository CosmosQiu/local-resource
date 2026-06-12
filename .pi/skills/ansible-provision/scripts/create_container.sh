#!/bin/bash
# =============================================================================
# create_container.sh — Ansible-based Docker container provisioner
#
# Usage:
#   HOST=192.168.1.100 SSH_USER=root SSH_PASSWORD=xxx CONTAINER_NAME=dev-01
#   IMAGE=nvidia/cuda:12.4-devel CPU=4 MEM=8 DISK=40 GPU=0
#   PORTS='{"8888/tcp":30080}' ./create_container.sh
#
# Output: JSON on stdout
# =============================================================================
set -euo pipefail

HOST="${HOST:?required}"
SSH_USER="${SSH_USER:?required}"
SSH_PASSWORD="${SSH_PASSWORD:?required}"
CONTAINER_NAME="${CONTAINER_NAME:?required}"
IMAGE="${IMAGE:-ubuntu:22.04}"
CPU="${CPU:-2}"
MEM="${MEM:-4}"
DISK="${DISK:-20}"
GPU="${GPU:-0}"
PORTS="${PORTS:-{}}"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10"

# ---- SSH helper ----
run_ssh() {
    sshpass -p "$SSH_PASSWORD" ssh $SSH_OPTS "$SSH_USER@$HOST" "$@"
}

# ---- 1. Verify SSH ----
if ! run_ssh 'echo OK' > /dev/null 2>&1; then
    echo '{"status":"error","error":"SSH connection failed"}'
    exit 1
fi

# ---- 2. Pull image ----
run_ssh "docker pull $IMAGE" > /dev/null 2>&1 || true

# ---- 3. Build docker run command ----
DOCKER_OPTS="-d --name $CONTAINER_NAME --cpus $CPU --memory ${MEM}g --restart unless-stopped"

# Disk: use tmpfs or volume mount (simplified)
DOCKER_OPTS="$DOCKER_OPTS --tmpfs /tmp:size=${DISK}g"

# GPU
if [ "$GPU" -gt 0 ]; then
    DOCKER_OPTS="$DOCKER_OPTS --gpus \"device=$GPU\""
fi

# Ports: parse JSON, map each
PORT_MAP=""
if command -v python3 &> /dev/null; then
    PORT_MAP=$(echo "$PORTS" | python3 -c "
import json,sys
ports=json.load(sys.stdin)
for k,v in ports.items():
    print(f'-p {v}:{k}')
")
fi
DOCKER_OPTS="$DOCKER_OPTS $PORT_MAP"

# ---- 4. Start container ----
# Stop and remove if exists
run_ssh "docker rm -f $CONTAINER_NAME" > /dev/null 2>&1 || true

CONTAINER_ID=$(run_ssh "docker run $DOCKER_OPTS $IMAGE sleep infinity" 2>&1)
if [ $? -ne 0 ]; then
    echo "{\"status\":\"error\",\"error\":\"Docker run failed: $CONTAINER_ID\"}"
    exit 1
fi
CONTAINER_ID=$(echo "$CONTAINER_ID" | head -1 | cut -c1-12)

# ---- 5. Generate access credential ----
ACCESS_CREDENTIAL=$(openssl rand -base64 12 2>/dev/null || echo "change-me-$(date +%s)")

# ---- 6. Install SSH inside container ----
run_ssh "docker exec $CONTAINER_NAME bash -c 'apt-get update -qq && apt-get install -y -qq openssh-server && mkdir -p /run/sshd && echo \"root:$ACCESS_CREDENTIAL\" | chpasswd'" > /dev/null 2>&1 || true
run_ssh "docker exec $CONTAINER_NAME service ssh start" > /dev/null 2>&1 || true

# ---- 7. Get container IP ----
INTERNAL_IP=$(run_ssh "docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_NAME" 2>&1 || echo "")

# ---- 8. Find SSH port ----
SSH_PORT="22"
# Check if port 22 was mapped
if command -v python3 &> /dev/null; then
    MAPPED=$(echo "$PORTS" | python3 -c "import json,sys; ports=json.load(sys.stdin); print(ports.get('22/tcp','22'))" 2>/dev/null || echo "22")
    SSH_PORT="$MAPPED"
fi

# ---- 9. Output JSON ----
cat <<EOF
{"status":"success","container_id":"$CONTAINER_ID","container_name":"$CONTAINER_NAME","access_url":"$HOST:$SSH_PORT","access_credential":"$ACCESS_CREDENTIAL","ssh_port":$SSH_PORT,"internal_ip":"$INTERNAL_IP","image":"$IMAGE","cpu_cores":$CPU,"memory_gb":$MEM,"disk_gb":$DISK,"gpu_count":$GPU}
EOF
