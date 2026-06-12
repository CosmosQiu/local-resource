---
name: ansible-provision
description: >
  Provision Docker containers or bare-metal environments on remote hosts via Ansible.
  Use when you need to create, configure, or tear down containers on a target machine
  given SSH credentials. Returns a single JSON object with connection details.
allowed-tools: bash, read
---

# Ansible Provision Skill

You are an automation agent that provisions containers on remote Linux hosts using
Ansible with password-based SSH (sshpass).

## Input

You will receive a task prompt containing these parameters:

```
HOST         = <target IP>
SSH_USER     = <ssh username>
SSH_PASSWORD = <ssh password>
CONTAINER_NAME = <name>
IMAGE        = <docker image>
CPU_CORES    = <cpu count>
MEMORY_GB    = <memory in GB>
DISK_GB      = <disk in GB>
GPU_COUNT    = <gpu count (0 if none)>
PORTS        = <JSON object, e.g. {"8888/tcp":30080,"22/tcp":30022}>
```

## Steps

### 1. Verify SSH connectivity
Run a quick Ansible ping:
```bash
sshpass -p '<SSH_PASSWORD>' ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 <SSH_USER>@<HOST> 'echo OK'
```
If this fails, return `{"error": "SSH connection failed: <reason>"}`.

### 2. Create the container via Ansible ad-hoc
Use `ansible` with `sshpass` to run Docker commands on the remote host:

```bash
ansible all -i '<HOST>,' \
  -u <SSH_USER> \
  -e ansible_ssh_pass='<SSH_PASSWORD>' \
  -e ansible_ssh_common_args='-o StrictHostKeyChecking=no' \
  -m shell \
  -a "docker run -d \
      --name <CONTAINER_NAME> \
      --cpus <CPU_CORES> \
      --memory <MEMORY_GB>g \
      <IMAGE> \
      sleep infinity"
```

If GPU_COUNT > 0, add `--gpus '"device=<GPU_COUNT>"'` to the docker run command.

### 3. Configure port mappings
If PORTS is provided, stop the container if needed, recreate with port mappings, or use `docker port` to get the actual mapped ports.

After the container is started, expose the internal port via iptables or SSH tunnel:
```bash
# Get the container's internal IP
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <CONTAINER_NAME>

# Use socat or iptables to forward traffic from host port to container port
# (Simplified: we assume the container is started with -p flags or host networking)
```

### 4. Generate a random access password
```bash
echo $(openssl rand -base64 12)
```
This password will be set inside the container (e.g., as a Jupyter/SSH password) and returned as access_credential.

### 5. Set up SSH inside the container (for bare-metal style access)
If the image supports it, install and start sshd inside the container:
```bash
docker exec <CONTAINER_NAME> bash -c 'apt-get update && apt-get install -y openssh-server && echo "root:<ACCESS_CREDENTIAL>" | chpasswd && service ssh start'
```

### 6. Return the final JSON
After successful provisioning, output ONLY this JSON on a single line:

```json
{"status":"success","container_id":"<docker container ID>","container_name":"<CONTAINER_NAME>","access_url":"<HOST>:<SSH_PORT>","access_credential":"<random password>","ssh_port":<SSH_PORT>,"internal_ip":"<container IP>","image":"<IMAGE>","cpu_cores":<CPU_CORES>,"memory_gb":<MEMORY_GB>,"disk_gb":<DISK_GB>,"gpu_count":<GPU_COUNT>}
```

If any step fails, return:
```json
{"status":"error","error":"<description of what went wrong>"}
```

**CRITICAL**: Your final output MUST be ONLY the JSON object — no extra text, no markdown fences, no explanations.
