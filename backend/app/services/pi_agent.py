"""
Pi Agent wrapper — spawns the pi CLI (or fallback script) to provision containers
via Ansible, then parses the JSON result.
"""
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger("uvicorn")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SKILL_PATH = PROJECT_ROOT / ".pi" / "skills" / "ansible-provision"
FALLBACK_SCRIPT = SKILL_PATH / "scripts" / "create_container.sh"


def _build_prompt(params: dict) -> str:
    """Build the Pi prompt from provision parameters."""
    return (
        f"Provision a Docker container with these parameters:\n\n"
        f"HOST         = {params['host_ip']}\n"
        f"SSH_USER     = {params['ssh_username']}\n"
        f"SSH_PASSWORD = {params['ssh_password']}\n"
        f"CONTAINER_NAME = {params['container_name']}\n"
        f"IMAGE        = {params.get('image_name', 'ubuntu:22.04')}\n"
        f"CPU_CORES    = {params.get('cpu_cores', 2)}\n"
        f"MEMORY_GB    = {params.get('memory_gb', 4)}\n"
        f"DISK_GB      = {params.get('disk_gb', 20)}\n"
        f"GPU_COUNT    = {params.get('gpu_count', 0)}\n"
        f"PORTS        = {params.get('ports', '{}')}\n\n"
        f"Use the ansible-provision skill to set up the container. "
        f"Return ONLY a single JSON line. No markdown, no extra text."
    )


def _call_pi_agent(prompt: str, skill_name: str | None = None) -> str:
    """Spawn `pi -p` in print mode with the provision skill. Returns stdout."""
    pi_cmd = settings.PI_COMMAND
    skill_path = str(SKILL_PATH)

    cmd = [
        pi_cmd, "-p", prompt,
        "--skill", skill_path,
        "--no-extensions", "--no-skills",
        "--no-session",
        "--approve",
    ]

    # Configure DeepSeek as the LLM backend (OpenAI-compatible)
    env = os.environ.copy()
    if settings.DEEPSEEK_API_KEY:
        env["OPENAI_API_KEY"] = settings.DEEPSEEK_API_KEY
        env["OPENAI_BASE_URL"] = settings.DEEPSEEK_BASE_URL
        cmd.extend(["--provider", "openai", "--model", settings.DEEPSEEK_MODEL])

    logger.info("Spawning Pi agent: %s", " ".join(cmd))
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=settings.PI_TIMEOUT,
        cwd=str(PROJECT_ROOT),
        env=env,
    )

    if result.returncode != 0:
        logger.error("Pi agent exit code %d: %s", result.returncode, result.stderr)
        raise RuntimeError(f"Pi agent failed: {result.stderr.strip()}")

    # Parse the output — extract the last JSON line
    output = result.stdout.strip()
    return output


def _call_fallback_script(params: dict) -> str:
    """Call the create_container.sh script directly as a fallback."""
    script = str(FALLBACK_SCRIPT)

    ports_json = params.get("exposed_ports")
    ports_str = json.dumps(ports_json) if ports_json else "{}"

    env = {
        **os.environ,
        "HOST": params["host_ip"],
        "SSH_USER": params["ssh_username"],
        "SSH_PASSWORD": params["ssh_password"],
        "CONTAINER_NAME": params["container_name"],
        "IMAGE": params.get("image_name", "ubuntu:22.04"),
        "CPU": str(params.get("cpu_cores", 2)),
        "MEM": str(params.get("memory_gb", 4)),
        "DISK": str(params.get("disk_gb", 20)),
        "GPU": str(params.get("gpu_count", 0)),
        "PORTS": ports_str,
    }

    logger.info("Running fallback provision script: %s", script)
    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        timeout=settings.PI_TIMEOUT,
        env=env,
        cwd=str(SKILL_PATH.parent),
    )

    if result.returncode != 0:
        logger.error("Fallback script exit code %d: %s", result.returncode, result.stderr)
        raise RuntimeError(f"Provision script failed: {result.stderr.strip()}")

    return result.stdout.strip()


def execute_provision(params: dict) -> dict:
    """
    Execute container provisioning via Pi agent or fallback script.

    Returns the parsed JSON result dict.
    """
    # Try Pi agent first; fall back to the direct script
    output = None
    errors = []

    try:
        prompt = _build_prompt(params)
        output = _call_pi_agent(prompt)
    except Exception as exc:
        errors.append(f"Pi agent: {exc}")
        logger.warning("Pi agent failed, trying fallback script...")

    if output is None:
        try:
            output = _call_fallback_script(params)
        except Exception as exc:
            errors.append(f"Fallback script: {exc}")
            return {"status": "error", "error": "; ".join(errors)}

    # Parse JSON from output
    return _parse_output(output)


DETECT_SCRIPT = SKILL_PATH / "scripts" / "detect_specs.sh"


def detect_hardware_specs(host_ip: str, ssh_username: str, ssh_password: str) -> dict:
    """
    Detect hardware specs on a target host via SSH.

    Runs the detect_specs.sh fallback script directly (Pi agent not needed
    for simple hardware detection). Returns parsed JSON.
    """
    script = str(DETECT_SCRIPT)
    env = {
        **os.environ,
        "HOST": host_ip,
        "SSH_USER": ssh_username,
        "SSH_PASSWORD": ssh_password,
    }

    logger.info("Detecting hardware on %s@%s", ssh_username, host_ip)
    result = subprocess.run(
        ["bash", script],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
        cwd=str(SKILL_PATH.parent),
    )

    if result.returncode != 0:
        logger.error("Detect script exit code %d: %s", result.returncode, result.stderr)
        return {"status": "error", "error": f"Detection failed: {result.stderr.strip()}"}

    return _parse_output(result.stdout)


def _parse_output(raw: str) -> dict:
    """Extract and parse JSON from agent output."""
    lines = raw.strip().splitlines()
    # Try each line as JSON, starting from the last
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        # Strip markdown fences if present
        if line.startswith("```"):
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    # Try to extract JSON from the whole text
    import re
    match = re.search(r'\{.*"status".*\}', raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    logger.error("Could not parse JSON from output: %s", raw[:500])
    return {"status": "error", "error": "Could not parse provision result"}
