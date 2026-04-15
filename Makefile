.PHONY: help setup test clean logs epoch-rotate smoke-test lint typecheck unit race ci

help: ## Show this help message
	@echo "MCP Sidecar Demo - Available Commands:"
	@echo "======================================"
	@echo "  setup          - Set up the complete MCP sidecar demo"
	@echo "  test           - Run smoke tests to verify the setup"
	@echo "  smoke-test     - Alias for test target"
	@echo "  epoch-rotate   - Demonstrate epoch rotation"
	@echo "  logs           - Show recent sidecar logs and permits"
	@echo "  status         - Show current instance status"
	@echo "  clean          - Clean up local files and stop instance"
	@echo "  install-deps   - Install required dependencies"
	@echo "  demo           - Complete demo: setup + test"

setup: ## Set up the complete MCP sidecar demo
	@echo "Setting up MCP sidecar demo..."
	@python3 setup/setup_mcp.py

test: ## Run smoke tests to verify the setup
	@echo "Running smoke tests..."
	@python3 smoke_test.py

smoke-test: test ## Alias for test target

epoch-rotate: ## Demonstrate epoch rotation (deny → update epoch → allow)
	@echo "Running epoch rotation validation..."
	@python3 test_epoch_rotation.py

logs: ## Show recent sidecar logs and permits
	@echo "Showing sidecar logs..."
	@python3 -c "import json; from setup.setup_mcp import collect_logs; info = json.load(open('instance_info.json')); print(collect_logs(info['instance_id']))"

clean: ## Clean up local files and stop instance
	@echo "Cleaning up..."
	@python3 -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Cleaning up...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; client = MorphCloudClient() if info else None; instance = client.instances.get(info['instance_id']) if client and info else None; instance.stop() if instance else None; print('Cleanup completed')"

status: ## Show current instance status
	@echo "Checking instance status..."
	@python3 -c "import json; import os; from morphcloud.api import MorphCloudClient; print('Checking status...'); info = json.load(open('instance_info.json')) if os.path.exists('instance_info.json') else None; print('Instance info:', info) if info else print('No instance found')"

install-deps: ## Install required dependencies
	@echo "Installing dependencies..."
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt
	@echo "Dependencies installed"
	@echo "Ensure Node.js and MORPH_API_KEY are configured"

lint: ## Run static analysis
	@ruff check .

typecheck: ## Run static typing checks
	@mypy setup smoke_test.py test_epoch_rotation.py

unit: ## Run unit tests
	@python3 -m pytest -q
	@cd sidecar && go test ./...

race: ## Run Go tests with the race detector (requires a C toolchain on some platforms)
	@cd sidecar && go test -race ./...

ci: lint typecheck unit ## Run all local quality gates

demo: setup test ## Complete demo: setup + test
	@echo "Demo completed successfully."
	@echo "Use the generated configs in Claude Desktop or Cursor"
	@echo "Run 'make logs' to see sidecar activity"
	@echo "Run 'make epoch-rotate' to see epoch rotation demo"
