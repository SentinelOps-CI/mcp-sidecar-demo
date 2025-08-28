#!/usr/bin/env python3
"""
MCP Sidecar Demo - Complete Workflow
Shows the entire setup and testing process
"""

import os
import sys
import subprocess
import time


def run_command(cmd, description):
    """Run a command and show progress"""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")

    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print("✅ Completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        print(f"Error output: {e.stderr}")
        return False


def check_prerequisites():
    """Check if all prerequisites are met"""
    print("🔍 Checking Prerequisites")
    print("=" * 40)

    # Check Python
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    print("✅ Python version OK")

    # Check pip
    try:
        import subprocess

        subprocess.run(["pip", "--version"], capture_output=True, check=True)
        print("✅ pip available")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pip not available")
        return False

    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Node.js available")
        else:
            print("❌ Node.js not available")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        return False

    # Check npx
    try:
        result = subprocess.run(["npx", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ npx available")
        else:
            print("❌ npx not available")
            return False
    except FileNotFoundError:
        print("❌ npx not found")
        return False

    # Check MORPH_API_KEY
    api_key = os.getenv("MORPH_API_KEY")
    if not api_key:
        print("❌ MORPH_API_KEY not set")
        print("   Set with: export MORPH_API_KEY='your-api-key'")
        return False
    print("✅ MORPH_API_KEY set")

    return True


def install_dependencies():
    """Install required Python dependencies"""
    print("\n📦 Installing Dependencies")
    print("=" * 40)

    return run_command(
        "pip install -r requirements.txt", "Installing Python dependencies"
    )


def run_setup():
    """Run the MCP setup"""
    print("\n🚀 Running MCP Setup")
    print("=" * 40)

    return run_command(
        "python3 setup/setup_mcp.py", "Setting up Morph VM and MCP servers"
    )


def run_tests():
    """Run smoke tests"""
    print("\n🧪 Running Tests")
    print("=" * 40)

    return run_command("python3 smoke_test.py", "Running smoke tests")


def show_results():
    """Show the final results"""
    print("\n🎉 Demo Results")
    print("=" * 40)

    try:
        with open("instance_info.json", "r") as f:
            import json

            info = json.load(f)

        print("✅ Setup completed successfully!")
        print(f"Instance ID: {info['instance_id']}")
        print(f"Snapshot ID: {info['snapshot_id']}")
        print("\nMCP Endpoints:")
        for name, url in info["urls"].items():
            print(f"  {name}: {url}/{name}/sse")

        print("\nClient Configs:")
        print("  Claude Desktop: clients/claude-desktop.json")
        print("  Cursor: clients/cursor.json")

        print("\nNext Steps:")
        print("1. Copy client configs to your MCP clients")
        print("2. Update MORPH_API_KEY in the configs")
        print("3. Restart your MCP client")
        print("4. Enjoy authenticated MCP access!")

        print("\nManagement Commands:")
        print("  make logs           # View sidecar logs")
        print("  make epoch-rotate   # Test epoch rotation")
        print("  make status         # Check instance status")
        print("  make clean          # Stop and cleanup")

    except FileNotFoundError:
        print("❌ instance_info.json not found")
        print("Setup may have failed")
        return False

    return True


def main():
    """Main demo function"""
    print("🚀 MCP Sidecar Demo - Complete Workflow")
    print("=" * 50)
    print("This demo will:")
    print("1. Check prerequisites")
    print("2. Install dependencies")
    print("3. Set up Morph VM with MCP servers")
    print("4. Run smoke tests")
    print("5. Show results and next steps")

    # Check prerequisites
    if not check_prerequisites():
        print("\n❌ Prerequisites not met. Please fix and try again.")
        return

    # Install dependencies
    if not install_dependencies():
        print("\n❌ Failed to install dependencies.")
        return

    # Run setup
    if not run_setup():
        print("\n❌ Setup failed.")
        return

    # Wait a moment for services to stabilize
    print("\n⏳ Waiting for services to stabilize...")
    time.sleep(5)

    # Run tests
    if not run_tests():
        print("\n❌ Tests failed.")
        return

    # Show results
    show_results()

    print("\n🎉 Demo completed successfully!")
    print("Your MCP sidecar is ready to use!")


if __name__ == "__main__":
    main()
