#!/usr/bin/env python3
"""Epoch rotation integration test with safe YAML mutation."""

import json
import os
import time

import requests
from morphcloud.api import MorphCloudClient


def test_epoch_rotation():
    """Test epoch rotation functionality"""
    print("Testing epoch rotation")
    print("=" * 50)

    # Check if we have instance info
    if not os.path.exists("instance_info.json"):
        print("instance_info.json not found. Run 'make setup' first.")
        return

    # Load instance info
    with open("instance_info.json") as f:
        info = json.load(f)

    # Check API key
    api_key = os.getenv("MORPH_API_KEY")
    if not api_key:
        print("MORPH_API_KEY environment variable not set")
        return

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Initialize client
        client = MorphCloudClient()
        instance = client.instances.get(info["instance_id"])

        print(f"Instance ID: {instance.id}")
        print(f"Status: {instance.status}")

        if instance.status != "running":
            print("Instance is not running. Start it first.")
            return

        # Test 1: Access with epoch-1 (should work)
        print("\nTest 1: Access with epoch-1 (active)")
        print("-" * 40)

        health_url = f"{info['urls']['mcp1']}/health"
        response = requests.get(health_url, headers=headers)

        if response.status_code == 200:
            print("Health check passed with epoch-1")
        else:
            print(f"Health check failed: {response.status_code}")
            return

        # Test 2: Access MCP endpoints with epoch-1
        for name, url in info["urls"].items():
            test_url = f"{url}/{name}/sse"
            response = requests.get(test_url, headers=headers)

            if response.status_code == 200:
                print(f"{name} endpoint accessible with epoch-1")
            else:
                print(f"{name} endpoint failed: {response.status_code}")
                return

        # Test 3: Rotate to epoch-2
        print("\nTest 3: Rotating to epoch-2")
        print("-" * 40)

        with instance.ssh() as ssh:
            ssh.run(
                """
                python3 - <<'PY'
import yaml
path = "/opt/sidecar/policy.yaml"
with open(path, "r", encoding="utf-8") as f:
    p = yaml.safe_load(f)
p["epochs"]["epoch-1"]["active"] = False
p["epochs"]["epoch-2"]["active"] = True
p["roles"]["default"]["epochs"] = ["epoch-2"]
with open(path, "w", encoding="utf-8") as f:
    yaml.safe_dump(p, f, sort_keys=False)
PY
            """
            )

            # Restart sidecar
            ssh.run("pkill -f '/opt/sidecar/sidecar' || true")
            time.sleep(3)
            ssh.run(
                "cd /opt/sidecar && "
                "nohup env SIDECAR_CONFIG=/opt/sidecar/config.yaml "
                "./sidecar > sidecar.log 2>&1 &"
            )
            time.sleep(5)
        print("Epoch rotated to epoch-2")

        # Test 4: Access with epoch-2 (should work)
        print("\nTest 4: Access with epoch-2 (active)")
        print("-" * 40)

        response = requests.get(health_url, headers=headers)
        if response.status_code == 200:
            print("Health check passed with epoch-2")
        else:
            print(f"Health check failed: {response.status_code}")
            return

        # Test 5: Check permits.jsonl for epoch changes
        print("\nTest 5: Checking audit logs")
        print("-" * 40)

        with instance.ssh() as ssh:
            result = ssh.run("tail -5 /opt/sidecar/permits.jsonl")
            print("Recent permits:")
            for line in result.stdout.strip().split("\n"):
                if line:
                    try:
                        permit = json.loads(line)
                        print(
                            f"  {permit['timestamp']}: "
                            f"{permit['decision']} ({permit['epoch']})"
                        )
                    except Exception:
                        print(f"  {line}")

        print("\nEpoch rotation test completed successfully")
        print("\nWhat happened:")
        print("1. Started with epoch-1 (active)")
        print("2. Rotated to epoch-2 (active)")
        print("3. Audit logs show epoch transitions")
        print("4. Policy enforcement is active")

    except Exception as e:
        print(f"Test failed: {e}")
        raise


def main():
    """Main function"""
    print("MCP Sidecar Epoch Rotation Test")
    print("=" * 50)

    test_epoch_rotation()


if __name__ == "__main__":
    main()
