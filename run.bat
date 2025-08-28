@echo off
setlocal enabledelayedexpansion

echo 🚀 MCP Sidecar Demo - Windows Runner
echo ======================================

if "%1"=="help" goto help
if "%1"=="setup" goto setup
if "%1"=="test" goto test
if "%1"=="smoke-test" goto test
if "%1"=="epoch-rotate" goto epoch-rotate
if "%1"=="logs" goto logs
if "%1"=="status" goto status
if "%1"=="clean" goto clean
if "%1"=="install-deps" goto install-deps
if "%1"=="demo" goto demo

:help
echo Available Commands:
echo   setup          - Set up the complete MCP sidecar demo
echo   test           - Run smoke tests to verify the setup
echo   smoke-test     - Alias for test target
echo   epoch-rotate   - Demonstrate epoch rotation
echo   logs           - Show recent sidecar logs and permits
echo   status         - Show current instance status
echo   clean          - Clean up local files and stop instance
echo   install-deps   - Install required dependencies
echo   demo           - Complete demo: setup + test
echo.
echo Usage: run.bat [command]
echo Example: run.bat setup
goto end

:install-deps
echo 📦 Installing dependencies...
pip install morphcloud
echo ✅ Dependencies installed
echo ⚠️  Make sure you have Node.js installed for npx
echo ⚠️  Set MORPH_API_KEY environment variable
goto end

:setup
echo 🚀 Setting up MCP Sidecar Demo...
python setup/setup_mcp.py
goto end

:test
echo 🧪 Running smoke tests...
python smoke_test.py
goto end

:epoch-rotate
echo 🔄 Demonstrating epoch rotation...
python test_epoch_rotation.py
goto end

:logs
echo 📋 Showing recent logs and permits...
python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('=== Fetching logs ==='); info = json.load(open('instance_info.json')); client = MorphCloudClient(); instance = client.instances.get(info['instance_id']); print('Instance:', instance.id)"
goto end

:status
echo 📊 Checking instance status...
python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Checking status...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; print('Instance info:', info) if info else print('No instance found')"
goto end

:clean
echo 🧹 Cleaning up...
python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Cleaning up...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; client = MorphCloudClient() if info else None; instance = client.instances.get(info['instance_id']) if client and info else None; instance.stop() if instance else None; print('Cleanup completed')"
goto end

:demo
echo 🎉 Running complete demo...
call :setup
if errorlevel 1 (
    echo ❌ Setup failed
    goto end
)
call :test
if errorlevel 1 (
    echo ❌ Test failed
    goto end
)
echo 🎉 Demo completed successfully!
echo Use the generated configs in Claude Desktop or Cursor
echo Run 'run.bat logs' to see sidecar activity
echo Run 'run.bat epoch-rotate' to see epoch rotation demo
goto end

:end
echo.
echo Done! Use 'run.bat help' to see available commands.
