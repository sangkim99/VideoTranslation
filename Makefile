.PHONY: setup run proto deploy

# 기본 Python 버전
PYTHON_VERSION := python3.10

PROTO_SRC_DIR := proto
PROTO_GEN_DIR := gen

setup:
	@echo "🛠 Setting up Python environment on Ubuntu..."
	sudo apt update -y
	sudo apt install -y make build-essential python3.10 python3.10-dev python3.10-venv
	sudo apt install -y libgl1-mesa-glx libglu1-mesa libxext6 libxrender1 libxtst6 libxi6
	python3.10 -m venv venv
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
