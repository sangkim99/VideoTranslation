.PHONY: setup run

# 기본 Python 버전
PYTHON_VERSION := python3.10

setup:
	@echo "Setting up Python environment..."
	sudo apt-get update
	sudo apt-get install -y $(PYTHON_VERSION) $(PYTHON_VERSION)-venv $(PYTHON_VERSION)-pip
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Setup completed successfully!"

run:
	@echo "Starting the server..."
	. venv/bin/activate && python main.py

deploy: setup run
	@echo "Deployment completed!" 