.PHONY: setup run

# 기본 Python 버전
PYTHON_VERSION := python3.9

setup:
	@echo "Setting up Python environment..."
	sudo yum update -y
	sudo yum install -y make
	sudo yum install -y $(PYTHON_VERSION) $(PYTHON_VERSION)-devel
	# OpenCV dependencies
	sudo yum install -y mesa-libGL mesa-libGLU
	sudo yum install -y libXext libXrender libXtst libXi
	sudo yum install -y gcc gcc-c++ make
	python3 -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install -r requirements.txt
	@echo "Setup completed successfully!"

run:
	@echo "Starting the server..."
	. venv/bin/activate && python main.py

deploy: setup run
	@echo "Deployment completed!" 