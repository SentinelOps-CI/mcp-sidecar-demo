#!/usr/bin/env python3
"""Smoke tests for the deployed MCP sidecar demo."""

import json
import os

import requests
from morphcloud.api import MorphCloudClient


def run_smoke_test():
    """Run basic smoke tests"""
    print("Running smoke tests")
    print("=" * 40)

    # Check prerequisites
    print("1. Checking prerequisites...")

    if not os.path.exists("instance_info.json"):
        print("instance_info.json not found")
        print("   Run 'make setup' first")
        return False

    api_key = os.getenv("MORPH_API_KEY")
    if not api_key:
        print("MORPH_API_KEY not set")
        print("   Set with: export MORPH_API_KEY='your-key'")
        return False

    print("Prerequisites met")

    # Load instance info
    with open("instance_info.json") as f:
        info = json.load(f)

    print(f"2. Instance ID: {info['instance_id']}")

    # Test instance status
    print("3. Checking instance status...")
    try:
        client = MorphCloudClient()
        instance = client.instances.get(info["instance_id"])

        if instance.status == "running":
            print("Instance is running")
        else:
            print(f"Instance status: {instance.status}")
            return False
    except Exception as e:
        print(f"Failed to get instance: {e}")
        return False

    # Test HTTP endpoints
    print("4. Testing HTTP endpoints...")
    headers = {"Authorization": f"Bearer {api_key}"}

    # Test health endpoint
    health_url = f"{info['urls']['mcp1']}/health"
    try:
        response = requests.get(health_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("Health endpoint accessible")
        else:
            print(f"Health endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Health check failed: {e}")
        return False

    ready_url = f"{info['urls']['mcp1']}/ready"
    try:
        response = requests.get(ready_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("Readiness endpoint accessible")
        else:
            print(f"Readiness endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"Readiness check failed: {e}")
        return False

    # Test MCP endpoints
    for name, url in info["urls"].items():
        test_url = f"{url}/{name}/sse"
        try:
            response = requests.get(test_url, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"{name} endpoint accessible")
            else:
                print(f"{name} endpoint failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"{name} test failed: {e}")
            return False

    print("\nAll smoke tests passed")
    print("\nYour MCP sidecar is ready")
    print("Use these URLs in your MCP clients:")
    for name, url in info["urls"].items():
        print(f"  {name}: {url}/{name}/sse")

    return True


def main():
    """Main function"""
    print("MCP Sidecar Smoke Test")
    print("=" * 40)

    success = run_smoke_test()

    if success:
        print("\nReady to use")
        print("Copy the client configs to Claude Desktop or Cursor")
    else:
        print("\nSetup incomplete")
        print("Run 'make setup' to create the infrastructure")


if __name__ == "__main__":
    main()
