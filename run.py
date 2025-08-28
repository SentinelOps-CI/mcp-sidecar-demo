#!/usr/bin/env python3
"""
MCP Sidecar Demo - Python Runner
Alternative to Makefile and batch files
"""

import sys
import subprocess
import os


def run_command(cmd, description):
    """Run a command and show progress"""
    print(f"\n🔄 {description}")
    print(f"Running: {cmd}")

    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True
        )
        print("✅ Completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed: {e}")
        if e.stderr:
            print(f"Error output: {e.stderr}")
        return False


def show_help():
    """Show available commands"""
    print("🚀 MCP Sidecar Demo - Python Runner")
    print("=====================================")
    print("Available Commands:")
    print("  setup          - Set up the complete MCP sidecar demo")
    print("  test           - Run smoke tests to verify the setup")
    print("  smoke-test     - Alias for test target")
    print("  epoch-rotate   - Demonstrate epoch rotation")
    print("  logs           - Show recent sidecar logs and permits")
    print("  status         - Show current instance status")
    print("  clean          - Clean up local files and stop instance")
    print("  install-deps   - Install required dependencies")
    print("  demo           - Complete demo: setup + test")
    print("")
    print("Usage: python run.py [command]")
    print("Example: python run.py setup")


def install_deps():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    return run_command("pip install morphcloud", "Installing Python dependencies")


def setup():
    """Set up the MCP demo"""
    print("🚀 Setting up MCP Sidecar Demo...")
    return run_command(
        "python setup/setup_mcp.py", "Setting up Morph VM and MCP servers"
    )


def test():
    """Run smoke tests"""
    print("🧪 Running smoke tests...")
    return run_command("python smoke_test.py", "Running smoke tests")


def epoch_rotate():
    """Demonstrate epoch rotation"""
    print("🔄 Demonstrating epoch rotation...")
    return run_command("python test_epoch_rotation.py", "Running epoch rotation demo")


def logs():
    """Show sidecar logs"""
    print("📋 Showing recent logs and permits...")
    cmd = '''python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('=== Fetching logs ==='); info = json.load(open('instance_info.json')); client = MorphCloudClient(); instance = client.instances.get(info['instance_id']); print('Instance:', instance.id)"'''
    return run_command(cmd, "Fetching sidecar logs")


def status():
    """Show instance status"""
    print("📊 Checking instance status...")
    cmd = '''python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Checking status...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; print('Instance info:', info) if info else print('No instance found')"'''
    return run_command(cmd, "Checking instance status")


def clean():
    """Clean up"""
    print("🧹 Cleaning up...")
    cmd = '''python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Cleaning up...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; client = MorphCloudClient() if info else None; instance = client.instances.get(info['instance_id']) if client and info else None; instance.stop() if instance else None; print('Cleanup completed')"'''
    return run_command(cmd, "Cleaning up instance and files")


def demo():
    """Run complete demo"""
    print("🎉 Running complete demo...")

    print("Step 1: Setting up...")
    if not setup():
        print("❌ Setup failed")
        return False

    print("Step 2: Testing...")
    if not test():
        print("❌ Test failed")
        return False

    print("🎉 Demo completed successfully!")
    print("Use the generated configs in Claude Desktop or Cursor")
    print("Run 'python run.py logs' to see sidecar activity")
    print("Run 'python run.py epoch-rotate' to see epoch rotation demo")
    return True


def main():
    """Main function"""
    if len(sys.argv) < 2:
        show_help()
        return

    command = sys.argv[1].lower()

    commands = {
        "help": show_help,
        "install-deps": install_deps,
        "setup": setup,
        "test": test,
        "smoke-test": test,
        "epoch-rotate": epoch_rotate,
        "logs": logs,
        "status": status,
        "clean": clean,
        "demo": demo,
    }

    if command in commands:
        commands[command]()
    else:
        print(f"❌ Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()
