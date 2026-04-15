#!/usr/bin/env python3
"""MCP sidecar setup pipeline backed by committed Go source."""

import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

try:
    from morphcloud.api import MorphCloudClient
except ImportError:  # pragma: no cover - allows offline unit tests
    MorphCloudClient = object  # type: ignore[misc,assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent
SIDECAR_DIR = REPO_ROOT / "sidecar"


def check_dependencies() -> bool:
    try:
        import morphcloud  # noqa: F401
    except ImportError:
        print("morphcloud SDK not found. Install with: pip install -r requirements.txt")
        return False
    try:
        subprocess.run(["npx", "--version"], capture_output=True, check=True, text=True)
    except Exception:
        print("npx not available. Install Node.js.")
        return False
    return True


def create_base_snapshot(client: MorphCloudClient) -> Any:
    return client.snapshots.create(
        image_id="morphvm-minimal",
        vcpus=2,
        memory=2048,
        disk_size=2048,
        metadata={"role": "mcp-demo", "epoch": "1"},
    )


def install_dependencies(snapshot: Any) -> Any:
    return snapshot.exec(
        """
        apt-get update &&
        apt-get install -y python3 python3-pip python3-venv curl git &&
        python3 -m pip install --upgrade pip &&
        python3 -m pip install mcp-server-filesystem mcp-server-git mcp-server-http pyyaml &&
        curl -fsSL https://go.dev/dl/go1.21.0.linux-amd64.tar.gz -o go.tar.gz &&
        tar -C /usr/local -xzf go.tar.gz &&
        mkdir -p /opt/mcp-servers /opt/sidecar
        """
    )


def upload_sidecar_and_build(instance: Any) -> None:
    if not SIDECAR_DIR.exists():
        raise FileNotFoundError(f"sidecar source directory not found: {SIDECAR_DIR}")

    archive_dir = tempfile.mkdtemp(prefix="sidecar-")
    try:
        archive_path = shutil.make_archive(
            str(Path(archive_dir) / "sidecar"), "gztar", root_dir=SIDECAR_DIR
        )
        with instance.ssh() as ssh:
            ssh.copy_to(archive_path, "/tmp/sidecar.tar.gz")
            ssh.run(
                """
                rm -rf /opt/sidecar &&
                mkdir -p /opt/sidecar &&
                tar -xzf /tmp/sidecar.tar.gz -C /opt/sidecar &&
                rm -f /tmp/sidecar.tar.gz &&
                cd /opt/sidecar &&
                export PATH=$PATH:/usr/local/go/bin &&
                go mod tidy &&
                go build -o sidecar .
                """
            )
    finally:
        shutil.rmtree(archive_dir, ignore_errors=True)


def start_services(instance: Any) -> None:
    with instance.ssh() as ssh:
        ssh.run("cd /opt/mcp-servers && nohup python3 -m mcp.server.filesystem "
                "--port 8000 > filesystem.log 2>&1 &")
        ssh.run("cd /opt/mcp-servers && nohup python3 -m mcp.server.git "
                "--port 8001 > git.log 2>&1 &")
        ssh.run("cd /opt/mcp-servers && nohup python3 -m mcp.server.http "
                "--port 8002 > http.log 2>&1 &")
        ssh.run(
            "cd /opt/sidecar && "
            "nohup env SIDECAR_CONFIG=/opt/sidecar/config.yaml ./sidecar > sidecar.log 2>&1 &"
        )
    time.sleep(3)


def expose_services(instance: Any) -> dict[str, str]:
    return {
        "mcp1": instance.expose_http_service("mcp1", 8080, auth_mode="api_key"),
        "mcp2": instance.expose_http_service("mcp2", 8080, auth_mode="api_key"),
        "mcp3": instance.expose_http_service("mcp3", 8080, auth_mode="api_key"),
    }


def create_client_configs(urls: dict[str, str]) -> None:
    Path("clients").mkdir(exist_ok=True)

    def cfg(url: str) -> dict:
        return {
            "command": "npx",
            "args": ["-y", "supergateway", "--sse", url],
        }

    payload = {
        "mcpServers": {
            "filesystem": cfg(f"{urls['mcp1']}/mcp1/sse"),
            "git": cfg(f"{urls['mcp2']}/mcp2/sse"),
            "http": cfg(f"{urls['mcp3']}/mcp3/sse"),
        }
    }
    (REPO_ROOT / "clients" / "claude-desktop.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    (REPO_ROOT / "clients" / "cursor.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def collect_logs(instance_id: str) -> str:
    client = MorphCloudClient()
    instance = client.instances.get(instance_id)
    with instance.ssh() as ssh:
        output = ssh.run(
            "echo '== sidecar.log =='; tail -n 30 /opt/sidecar/sidecar.log || true; "
            "echo '== permits.jsonl =='; tail -n 20 /opt/sidecar/permits.jsonl || true"
        )
    return str(output.stdout)


def main() -> None:
    if not check_dependencies():
        return

    if not os.getenv("MORPH_API_KEY"):
        print("MORPH_API_KEY environment variable not set.")
        return

    client = MorphCloudClient()
    base = create_base_snapshot(client)
    prepared = install_dependencies(base)
    instance = client.instances.start(snapshot_id=prepared.id)
    instance.wait_until_ready()
    upload_sidecar_and_build(instance)
    start_services(instance)
    urls = expose_services(instance)
    create_client_configs(urls)

    info = {
        "instance_id": instance.id,
        "snapshot_id": prepared.id,
        "urls": urls,
        "created_at": time.time(),
    }
    (REPO_ROOT / "instance_info.json").write_text(
        json.dumps(info, indent=2), encoding="utf-8"
    )
    print("Setup complete.")
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    main()
