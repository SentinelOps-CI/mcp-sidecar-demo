#!/usr/bin/env pwsh

param(
    [string]$Command = "help"
)

Write-Host "🚀 MCP Sidecar Demo - PowerShell Runner" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

switch ($Command.ToLower()) {
    "help" {
        Write-Host "Available Commands:" -ForegroundColor Yellow
        Write-Host "  setup          - Set up the complete MCP sidecar demo" -ForegroundColor Cyan
        Write-Host "  test           - Run smoke tests to verify the setup" -ForegroundColor Cyan
        Write-Host "  smoke-test     - Alias for test target" -ForegroundColor Cyan
        Write-Host "  epoch-rotate   - Demonstrate epoch rotation" -ForegroundColor Cyan
        Write-Host "  logs           - Show recent sidecar logs and permits" -ForegroundColor Cyan
        Write-Host "  status         - Show current instance status" -ForegroundColor Cyan
        Write-Host "  clean          - Clean up local files and stop instance" -ForegroundColor Cyan
        Write-Host "  install-deps   - Install required dependencies" -ForegroundColor Cyan
        Write-Host "  demo           - Complete demo: setup + test" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Usage: .\run.ps1 [command]" -ForegroundColor White
        Write-Host "Example: .\run.ps1 setup" -ForegroundColor White
        break
    }
    
    "install-deps" {
        Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
        pip install morphcloud
        Write-Host "✅ Dependencies installed" -ForegroundColor Green
        Write-Host "⚠️  Make sure you have Node.js installed for npx" -ForegroundColor Yellow
        Write-Host "⚠️  Set MORPH_API_KEY environment variable" -ForegroundColor Yellow
        break
    }
    
    "setup" {
        Write-Host "🚀 Setting up MCP Sidecar Demo..." -ForegroundColor Yellow
        python setup/setup_mcp.py
        break
    }
    
    "test" {
        Write-Host "🧪 Running smoke tests..." -ForegroundColor Yellow
        python smoke_test.py
        break
    }
    
    "smoke-test" {
        Write-Host "🧪 Running smoke tests..." -ForegroundColor Yellow
        python smoke_test.py
        break
    }
    
    "epoch-rotate" {
        Write-Host "🔄 Demonstrating epoch rotation..." -ForegroundColor Yellow
        python test_epoch_rotation.py
        break
    }
    
    "logs" {
        Write-Host "📋 Showing recent logs and permits..." -ForegroundColor Yellow
        python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('=== Fetching logs ==='); info = json.load(open('instance_info.json')); client = MorphCloudClient(); instance = client.instances.get(info['instance_id']); print('Instance:', instance.id)"
        break
    }
    
    "status" {
        Write-Host "📊 Checking instance status..." -ForegroundColor Yellow
        python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Checking status...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; print('Instance info:', info) if info else print('No instance found')"
        break
    }
    
    "clean" {
        Write-Host "🧹 Cleaning up..." -ForegroundColor Yellow
        python -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Cleaning up...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; client = MorphCloudClient() if info else None; instance = client.instances.get(info['instance_id']) if client and info else None; instance.stop() if instance else None; print('Cleanup completed')"
        break
    }
    
    "demo" {
        Write-Host "🎉 Running complete demo..." -ForegroundColor Yellow
        Write-Host "Step 1: Setting up..." -ForegroundColor Cyan
        & $PSCommandPath "setup"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Setup failed" -ForegroundColor Red
            break
        }
        Write-Host "Step 2: Testing..." -ForegroundColor Cyan
        & $PSCommandPath "test"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "❌ Test failed" -ForegroundColor Red
            break
        }
        Write-Host "🎉 Demo completed successfully!" -ForegroundColor Green
        Write-Host "Use the generated configs in Claude Desktop or Cursor" -ForegroundColor White
        Write-Host "Run '.\run.ps1 logs' to see sidecar activity" -ForegroundColor White
        Write-Host "Run '.\run.ps1 epoch-rotate' to see epoch rotation demo" -ForegroundColor White
        break
    }
    
    default {
        Write-Host "❌ Unknown command: $Command" -ForegroundColor Red
        Write-Host "Use '.\run.ps1 help' to see available commands" -ForegroundColor Yellow
        break
    }
}

Write-Host ""
Write-Host "Done! Use '.\run.ps1 help' to see available commands." -ForegroundColor Gray
