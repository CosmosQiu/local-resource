#!/bin/bash
# =============================================================================
# detect_specs.sh — SSH into target host and collect hardware specs as JSON
#
# Usage:
#   HOST=192.168.1.100 SSH_USER=root SSH_PASSWORD=xxx ./detect_specs.sh
#
# Output: JSON on stdout
# =============================================================================
set -euo pipefail

HOST="${HOST:?required}"
SSH_USER="${SSH_USER:?required}"
SSH_PASSWORD="${SSH_PASSWORD:?required}"

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

# ---- 2. Detect CPU ----
CPU_CORES=$(run_ssh 'nproc' 2>/dev/null || echo "0")

# ---- 3. Detect Memory (GB, integer) ----
MEM_GB=$(run_ssh 'free -g | awk "/^Mem:/{print \$2}"' 2>/dev/null || echo "0")

# ---- 4. Detect Disk (GB) — root partition ----
DISK_GB=$(run_ssh 'df -BG / | awk "NR==2{print \$2}" | tr -d "G"' 2>/dev/null || echo "0")

# ---- 5. Detect GPU (nvidia-smi) ----
GPU_COUNT=0
GPU_NAMES=""
GPU_MEMORY_MB=0
if run_ssh 'which nvidia-smi' > /dev/null 2>&1; then
    GPU_INFO=$(run_ssh 'nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader,nounits' 2>/dev/null || echo "")
    if [ -n "$GPU_INFO" ]; then
        GPU_COUNT=$(echo "$GPU_INFO" | wc -l)
        GPU_NAMES=$(echo "$GPU_INFO" | awk -F',' '{print $2}' | tr '\n' ';' | sed 's/;$//')
        GPU_MEMORY_MB=$(echo "$GPU_INFO" | awk -F',' '{print $3}' | head -1 | xargs)
    fi
fi

# ---- 6. Detect OS type ----
OS_TYPE=$(run_ssh 'uname -s' 2>/dev/null || echo "Linux")

# ---- 7. Detect hostname ----
HOSTNAME=$(run_ssh 'hostname' 2>/dev/null || echo "$HOST")

# ---- 8. Output JSON ----
cat <<EOF
{"status":"success","hostname":"$HOSTNAME","os_type":"$OS_TYPE","cpu_cores":$CPU_CORES,"memory_gb":$MEM_GB,"disk_gb":$DISK_GB,"gpu_count":$GPU_COUNT,"gpu_names":"$GPU_NAMES","gpu_memory_mb":$GPU_MEMORY_MB}
EOF
