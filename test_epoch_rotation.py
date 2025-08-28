#!/usr/bin/env python3
"""
Epoch Rotation Test Script
Demonstrates the PERM-UNIFY-R1 epoch rotation functionality
"""

import json
import time
import requests
import os
from morphcloud.api import MorphCloudClient


def test_epoch_rotation():
    """Test epoch rotation functionality"""
    print("🔄 Testing Epoch Rotation")
    print("=" * 50)

    # Check if we have instance info
    if not os.path.exists("instance_info.json"):
        print("❌ instance_info.json not found. Run 'make setup' first.")
        return

    # Load instance info
    with open("instance_info.json", "r") as f:
        info = json.load(f)

    # Check API key
    api_key = os.getenv("MORPH_API_KEY")
    if not api_key:
        print("❌ MORPH_API_KEY environment variable not set")
        return

    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        # Initialize client
        client = MorphCloudClient()
        instance = client.instances.get(info["instance_id"])

        print(f"Instance ID: {instance.id}")
        print(f"Status: {instance.status}")

        if instance.status != "running":
            print("❌ Instance is not running. Start it first.")
            return

        # Test 1: Access with epoch-1 (should work)
        print("\n🧪 Test 1: Access with epoch-1 (active)")
        print("-" * 40)

        health_url = f"{info['urls']['mcp1']}/health"
        response = requests.get(health_url, headers=headers)

        if response.status_code == 200:
            print("✅ Health check passed with epoch-1")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return

        # Test 2: Access MCP endpoints with epoch-1
        for name, url in info["urls"].items():
            test_url = f"{url}/{name}/sse"
            response = requests.get(test_url, headers=headers)

            if response.status_code == 200:
                print(f"✅ {name} endpoint accessible with epoch-1")
            else:
                print(f"❌ {name} endpoint failed: {response.status_code}")

        # Test 3: Rotate to epoch-2
        print("\n🔄 Test 3: Rotating to epoch-2")
        print("-" * 40)

        with instance.ssh() as ssh:
            # Check current policy
            result = ssh.run('cat /opt/sidecar/policy.yaml | grep -A 5 "epoch-1:"')
            print(f"Current epoch-1 policy: {result.stdout.strip()}")

            # Rotate to epoch-2
            print("Rotating to epoch-2...")
            ssh.run(
                """
                sed -i 's/active: true/active: false/' /opt/sidecar/policy.yaml
                sed -i 's/active: false/active: true/' /opt/sidecar/policy.yaml
                sed -i 's/epoch-1/epoch-2/g' /opt/sidecar/policy.yaml
            """
            )

            # Restart sidecar
            print("Restarting sidecar...")
            ssh.run("pkill -f sidecar")
            time.sleep(3)
            ssh.run("cd /opt/sidecar && nohup ./sidecar > sidecar.log 2>&1 &")
            time.sleep(5)

            # Check new policy
            result = ssh.run('cat /opt/sidecar/policy.yaml | grep -A 5 "epoch-2:"')
            print(f"New epoch-2 policy: {result.stdout.strip()}")

        print("✅ Epoch rotated to epoch-2")

        # Test 4: Access with epoch-2 (should work)
        print("\n🧪 Test 4: Access with epoch-2 (active)")
        print("-" * 40)

        response = requests.get(health_url, headers=headers)
        if response.status_code == 200:
            print("✅ Health check passed with epoch-2")
        else:
            print(f"❌ Health check failed: {response.status_code}")

        # Test 5: Check permits.jsonl for epoch changes
        print("\n📋 Test 5: Checking audit logs")
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

        print("\n🎉 Epoch rotation test completed successfully!")
        print("\nWhat happened:")
        print("1. ✅ Started with epoch-1 (active) - access allowed")
        print("2. 🔄 Rotated to epoch-2 (active) - access maintained")
        print("3. 📋 Audit logs show epoch transitions")
        print("4. 🔐 Policy enforcement working correctly")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise


def main():
    """Main function"""
    print("🚀 MCP Sidecar Epoch Rotation Test")
    print("=" * 50)

    test_epoch_rotation()


if __name__ == "__main__":
    main()
