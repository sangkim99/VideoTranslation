.PHONY: setup run proto deploy

# 기본 Python 버전
PYTHON_VERSION := python3

PROTO_SRC_DIR := proto
PROTO_GEN_DIR := gen

SERVICE_NAME := videotransation-server
SERVICE_FILE := /etc/systemd/system/$(SERVICE_NAME).service
WORK_DIR := /home/ubuntu/VideoTranslation
PYTHON_PATH := $(WORK_DIR)/venv/bin/python3


setup:
	@echo "🛠 Setting up Python environment on Ubuntu..."
	sudo apt update -y
	sudo apt install -y make build-essential $(PYTHON_VERSION) $(PYTHON_VERSION)-dev $(PYTHON_VERSION)-venv
	sudo apt install -y libgl1 libglu1-mesa libxext6 libxrender1 libxtst6 libxi6
	$(PYTHON_VERSION) -m venv venv
	. venv/bin/activate && pip install --upgrade pip
	. venv/bin/activate && pip install --upgrade protobuf
	. venv/bin/activate && pip install --upgrade grpcio grpcio-tools
	. venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Setup completed successfully!"

proto:
	@echo "📦 Generating gRPC + Protobuf files..."
	mkdir -p $(PROTO_GEN_DIR)
	. venv/bin/activate && python -m grpc_tools.protoc \
		--proto_path=$(PROTO_SRC_DIR) \
		--python_out=$(PROTO_GEN_DIR) \
		--grpc_python_out=$(PROTO_GEN_DIR) \
		$(PROTO_SRC_DIR)/*.proto
	@echo "✅ Proto files generated in $(PROTO_GEN_DIR)/"

run:
	@echo "🚀 Starting the server..."
	. venv/bin/activate && python main.py

deploy: setup proto run
	@echo "🚀 Deployment completed!" 

systemd:
	@echo "🔧 Registering systemd service ($(SERVICE_NAME))..."
	echo "[Unit]" | sudo tee $(SERVICE_FILE) > /dev/null
	echo "Description=Mediapipe Python gRPC Server" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "After=network.target" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "[Service]" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "User=$$USER" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "WorkingDirectory=$(WORK_DIR)" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "ExecStart=$(PYTHON_PATH) main.py" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "Restart=always" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "RestartSec=3" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "Environment=PYTHONUNBUFFERED=1" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "[Install]" | sudo tee -a $(SERVICE_FILE) > /dev/null
	echo "WantedBy=multi-user.target" | sudo tee -a $(SERVICE_FILE) > /dev/null

	sudo systemctl daemon-reexec
	sudo systemctl daemon-reload
	sudo systemctl enable $(SERVICE_NAME)
	sudo systemctl restart $(SERVICE_NAME)
	@echo "✅ systemd 등록 및 서비스 시작 완료"