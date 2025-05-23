.PHONY: all setup submodules env force-env download-model build-bot-image build up down clean ps logs test

# Default target: Sets up everything and starts the services
all: setup build up

# Target to set up only the environment without Docker
setup-env: submodules env download-model
	@echo "Environment setup complete."
	@echo "To specify a target for .env generation (cpu or gpu), run 'make env TARGET=cpu' or 'make env TARGET=gpu' first, then 'make setup-env'."
	@echo "If no TARGET is specified, it defaults to 'make env TARGET=cpu'."
	@echo "NOTE: If your .env file already exists, it will be preserved. To force recreation, use 'make force-env TARGET=cpu/gpu'."

# Target to perform all initial setup steps
setup: setup-env build-bot-image
	@echo "Setup complete."

# Initialize and update Git submodules
submodules:
	@echo "---> Initializing and updating Git submodules..."
	@git submodule update --init --recursive

# Default bot image tag if not specified in .env
BOT_IMAGE_NAME ?= vexa-bot:dev

# Check if Docker daemon is running
check_docker:
	@echo "---> Checking if Docker is running..."
	@if ! docker info > /dev/null 2>&1; then \
		echo "ERROR: Docker is not running. Please start Docker Desktop or Docker daemon first."; \
		exit 1; \
	fi
	@echo "---> Docker is running."

# Include .env file if it exists for environment variables 
-include .env

# Create .env file from example
env:
ifndef TARGET
	$(info TARGET not set. Defaulting to cpu. Use 'make env TARGET=cpu' or 'make env TARGET=gpu')
	$(eval TARGET := cpu)
endif
	@echo "---> Checking .env file for TARGET=$(TARGET)..."
	@if [ -f .env ]; then \
		echo "*** .env file already exists. Keeping existing file. ***"; \
		echo "*** To force recreation, delete .env first or use 'make force-env TARGET=$(TARGET)'. ***"; \
	elif [ "$(TARGET)" = "cpu" ]; then \
		if [ ! -f env-example.cpu ]; then \
			echo "env-example.cpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.cpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.cpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.cpu; \
			echo "WHISPER_MODEL_SIZE=tiny" >> env-example.cpu; \
			echo "DEVICE_TYPE=cpu" >> env-example.cpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.cpu; \
			echo "# Exposed Host Ports" >> env-example.cpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.cpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.cpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.cpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.cpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.cpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.cpu; \
		fi; \
		cp env-example.cpu .env; \
		echo "*** .env file created from env-example.cpu. Please review it. ***"; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		if [ ! -f env-example.gpu ]; then \
			echo "env-example.gpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.gpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.gpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.gpu; \
			echo "WHISPER_MODEL_SIZE=medium" >> env-example.gpu; \
			echo "DEVICE_TYPE=cuda" >> env-example.gpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.gpu; \
			echo "# Exposed Host Ports" >> env-example.gpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.gpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.gpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.gpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.gpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.gpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.gpu; \
		fi; \
		cp env-example.gpu .env; \
		echo "*** .env file created from env-example.gpu. Please review it. ***"; \
	else \
		echo "Error: TARGET must be 'cpu' or 'gpu'. Usage: make env TARGET=<cpu|gpu>"; \
		exit 1; \
	fi

# Force create .env file from example (overwrite existing)
force-env:
ifndef TARGET
	$(info TARGET not set. Defaulting to cpu. Use 'make force-env TARGET=cpu' or 'make force-env TARGET=gpu')
	$(eval TARGET := cpu)
endif
	@echo "---> Creating .env file for TARGET=$(TARGET) (forcing overwrite)..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		if [ ! -f env-example.cpu ]; then \
			echo "env-example.cpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.cpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.cpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.cpu; \
			echo "WHISPER_MODEL_SIZE=tiny" >> env-example.cpu; \
			echo "DEVICE_TYPE=cpu" >> env-example.cpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.cpu; \
			echo "# Exposed Host Ports" >> env-example.cpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.cpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.cpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.cpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.cpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.cpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.cpu; \
		fi; \
		cp env-example.cpu .env; \
		echo "*** .env file created from env-example.cpu. Please review it. ***"; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		if [ ! -f env-example.gpu ]; then \
			echo "env-example.gpu not found. Creating default one."; \
			echo "ADMIN_API_TOKEN=token" > env-example.gpu; \
			echo "LANGUAGE_DETECTION_SEGMENTS=10" >> env-example.gpu; \
			echo "VAD_FILTER_THRESHOLD=0.5" >> env-example.gpu; \
			echo "WHISPER_MODEL_SIZE=medium" >> env-example.gpu; \
			echo "DEVICE_TYPE=cuda" >> env-example.gpu; \
			echo "BOT_IMAGE_NAME=vexa-bot:dev" >> env-example.gpu; \
			echo "# Exposed Host Ports" >> env-example.gpu; \
			echo "API_GATEWAY_HOST_PORT=8056" >> env-example.gpu; \
			echo "ADMIN_API_HOST_PORT=8057" >> env-example.gpu; \
			echo "TRAEFIK_WEB_HOST_PORT=9090" >> env-example.gpu; \
			echo "TRAEFIK_DASHBOARD_HOST_PORT=8085" >> env-example.gpu; \
			echo "TRANSCRIPTION_COLLECTOR_HOST_PORT=8123" >> env-example.gpu; \
			echo "POSTGRES_HOST_PORT=5438" >> env-example.gpu; \
		fi; \
		cp env-example.gpu .env; \
		echo "*** .env file created from env-example.gpu. Please review it. ***"; \
	else \
		echo "Error: TARGET must be 'cpu' or 'gpu'. Usage: make force-env TARGET=<cpu|gpu>"; \
		exit 1; \
	fi

# Download the Whisper model
download-model:
	@echo "---> Creating ./hub directory if it doesn't exist..."
	@mkdir -p ./hub
	@echo "---> Ensuring ./hub directory is writable..."
	@chmod u+w ./hub
	@echo "---> Downloading Whisper model (this may take a while)..."
	@python download_model.py

# Build the standalone vexa-bot image
# Uses BOT_IMAGE_NAME from .env if available, otherwise falls back to default
build-bot-image: check_docker
	@if [ -f .env ]; then \
		ENV_BOT_IMAGE_NAME=$$(grep BOT_IMAGE_NAME .env | cut -d= -f2); \
		if [ -n "$$ENV_BOT_IMAGE_NAME" ]; then \
			echo "---> Building $$ENV_BOT_IMAGE_NAME image (from .env)..."; \
			docker build -t $$ENV_BOT_IMAGE_NAME -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
		else \
			echo "---> Building $(BOT_IMAGE_NAME) image (BOT_IMAGE_NAME not found in .env)..."; \
			docker build -t $(BOT_IMAGE_NAME) -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
		fi; \
	else \
		echo "---> Building $(BOT_IMAGE_NAME) image (.env file not found)..."; \
		docker build -t $(BOT_IMAGE_NAME) -f services/vexa-bot/core/Dockerfile ./services/vexa-bot/core; \
	fi

# Build Docker Compose service images
build: check_docker
ifndef TARGET
	$(info TARGET not set for build. Defaulting to cpu. Run 'make build TARGET=cpu/gpu' or ensure .env is configured via 'make env TARGET=cpu/gpu')
	$(eval TARGET := cpu)
endif
	@echo "---> Building Docker Compose services..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		echo "---> Building with 'cpu' profile (includes whisperlive-cpu)..."; \
		PROFILE_ARG="--profile cpu"; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		echo "---> Building with 'gpu' profile (includes whisperlive-gpu)..."; \
		PROFILE_ARG="--profile gpu"; \
	else \
		echo "---> Building with default profile (TARGET=$(TARGET) not cpu or gpu)..."; \
		PROFILE_ARG=""; \
	fi
	@docker compose $$PROFILE_ARG build \
		--build-arg SHARED_MODELS_VERSION=$(SHARED_MODELS_VERSION) \
		--build-arg ADMIN_API_IMAGE_TAG=dev \
		--build-arg API_GATEWAY_IMAGE_TAG=dev \
		--build-arg BOT_MANAGER_IMAGE_TAG=dev \
		--build-arg TRANSCRIPTION_COLLECTOR_IMAGE_TAG=dev \
		$(EXTRA_ARGS)
	@echo "---> Docker images built (as :latest by default from compose file)."
	@echo "---> Retagging Vexa services to :dev for Kubernetes..."
	@docker tag vexa-admin-api:latest vexa-admin-api:dev
	@docker tag vexa-api-gateway:latest vexa-api-gateway:dev
	@docker tag vexa-bot-manager:latest vexa-bot-manager:dev
	@docker tag vexa-transcription-collector:latest vexa-transcription-collector:dev
	@if [ "$(TARGET)" = "cpu" ]; then docker tag vexa-whisperlive-cpu:latest vexa-whisperlive-cpu:dev; fi
	@if [ "$(TARGET)" = "gpu" ]; then docker tag vexa-whisperlive:latest vexa-whisperlive:dev; fi
	@echo "---> Vexa services retagged to :dev."

# Start services in detached mode
up: check_docker
	@echo "---> Starting Docker Compose services..."
	@if [ "$(TARGET)" = "cpu" ]; then \
		echo "---> Activating 'cpu' profile to start whisperlive-cpu along with other services..."; \
		docker compose --profile cpu up -d; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		echo "---> Starting services for GPU. This will start 'whisperlive' (for GPU) and other default services. 'whisperlive-cpu' (profile=cpu) will not be started."; \
		docker compose --profile gpu up -d; \
	else \
		echo "---> TARGET not explicitly set, defaulting to CPU mode. 'whisperlive' (GPU) will not be started."; \
		docker compose --profile cpu up -d; \
	fi

# Stop services
down: check_docker
	@echo "---> Stopping Docker Compose services..."
	@docker compose down

# Stop services and remove volumes
clean: check_docker
	@echo "---> Stopping Docker Compose services and removing volumes..."
	@docker compose down -v

# Show container status
ps: check_docker
	@docker compose ps

# Tail logs for all services
logs:
	@docker compose logs -f

# Run the interaction test script
test: check_docker
	@echo "---> Running test script..."
	@echo "---> API Documentation URLs:"
	@if [ -f .env ]; then \
		API_PORT=$$(grep -E '^[[:space:]]*API_GATEWAY_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		ADMIN_PORT=$$(grep -E '^[[:space:]]*ADMIN_API_HOST_PORT=' .env | cut -d= -f2- | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$$//'); \
		[ -z "$$API_PORT" ] && API_PORT=8056; \
		[ -z "$$ADMIN_PORT" ] && ADMIN_PORT=8057; \
		echo "    Main API:  http://localhost:$$API_PORT/docs"; \
		echo "    Admin API: http://localhost:$$ADMIN_PORT/docs"; \
	else \
		echo "    Main API:  http://localhost:8056/docs"; \
		echo "    Admin API: http://localhost:8057/docs"; \
	fi
	@chmod +x run_vexa_interaction.sh
	@./run_vexa_interaction.sh

# -----------------------------------------------------------------------------
# Kubernetes (kind) helper targets – zero-host-clutter local cluster
# -----------------------------------------------------------------------------

# Namespace / cluster settings (override in your shell if you like)
K8S_NS          ?= vexa
KIND_NAME       ?= vexa
KUBECONFIG      ?= $(HOME)/.kube/config

# Ports – read from .env if present, otherwise fall back to the same safe high-port range we ship in the
# env-example.* files we just updated above.
API_GATEWAY_HOST_PORT          ?= 18056
ADMIN_API_HOST_PORT            ?= 18057
TRANSCRIPTION_COLLECTOR_HOST_PORT ?= 18123
POSTGRES_HOST_PORT             ?= 15432
REDIS_HOST_PORT                ?= 16379
TRAEFIK_WEB_HOST_PORT          ?= 19090
TRAEFIK_DASHBOARD_HOST_PORT    ?= 18085

# -----------------------------------------------------------------------------
# Create / start a kind cluster if it doesn't exist
k8s-kind:
	@echo "---> Ensuring kind cluster '$(KIND_NAME)' exists ..."
	@if ! kind get clusters | grep -q "^$(KIND_NAME)$$" ; then \
		echo "Cluster $(KIND_NAME) not found. Creating..."; \
		kind create cluster --name $(KIND_NAME) --image kindest/node:v1.30.0; \
	else \
		echo "kind cluster $(KIND_NAME) already up"; \
	fi
	@echo "---> Setting KUBECONFIG for this session..."
	@export KUBECONFIG=$(KUBECONFIG)

# Make sure .env exists, copy from example if not
k8s-env:
ifndef TARGET
	$(info TARGET not set for k8s-env. Defaulting to cpu.)
	$(eval TARGET := cpu)
endif
	@if [ ! -f .env ]; then \
		echo "---> .env not found, creating from env-example.$(TARGET)..."; \
		make env TARGET=$(TARGET); \
	else \
		echo "---> .env found."; \
	fi

# Build all docker images needed for k8s
k8s-build: build build-bot-image
	@echo "---> Docker images built for k8s."

# Load images into kind
# Note: BOT_IMAGE_NAME must be resolvable from .env or Makefile default for k8s-load and k8s-apply to work.
k8s-load: check_docker k8s-kind
	@echo "---> Loading freshly built images into kind node ..."
	@kind load docker-image vexa-api-gateway:dev --name $(KIND_NAME)
	@kind load docker-image vexa-admin-api:dev --name $(KIND_NAME)
	@kind load docker-image vexa-transcription-collector:dev --name $(KIND_NAME)
	@kind load docker-image vexa-bot-manager:dev --name $(KIND_NAME)
	@kind load docker-image vexa-whisperlive-cpu:dev --name $(KIND_NAME)
	@$(eval LOAD_BOT_IMAGE_NAME := $(shell grep BOT_IMAGE_NAME .env | cut -d= -f2 || echo "$(BOT_IMAGE_NAME)"))
	@echo "---> Will load bot image: $(LOAD_BOT_IMAGE_NAME)"
	@kind load docker-image $(LOAD_BOT_IMAGE_NAME) --name $(KIND_NAME)
	@echo "---> Pulling and loading base images for Kompose..."
	@docker pull postgres:13
	@kind load docker-image postgres:13 --name $(KIND_NAME)
	@docker pull redis:latest
	@kind load docker-image redis:latest --name $(KIND_NAME)
	@docker pull traefik:v2.5
	@kind load docker-image traefik:v2.5 --name $(KIND_NAME)

# Generate k8s manifests using kompose, then tweak them
k8s-generate: k8s-env
	@echo "---> Generating k8s manifests from docker-compose.yml into k8s/ directory for TARGET=$(TARGET)..."
	@mkdir -p k8s # Ensure k8s directory exists
	@rm -rf k8s/*
	@if [ "$(TARGET)" = "cpu" ]; then \
		PROFILE_ARG="--profile cpu"; \
		KOMPOSE_ENV_ARGS="DEVICE_TYPE=cpu"; \
		echo "---> Using Kompose profile: cpu (for whisperlive-cpu) with DEVICE_TYPE=cpu"; \
		echo "DEBUG: Running simplified kompose command for CPU target"; \
		kompose convert --profile cpu -f docker-compose.yml -o k8s/; \
	elif [ "$(TARGET)" = "gpu" ]; then \
		PROFILE_ARG="--profile gpu"; \
		KOMPOSE_ENV_ARGS="DEVICE_TYPE=cuda"; \
		echo "---> Using Kompose profile: gpu (for whisperlive-gpu) with DEVICE_TYPE=cuda"; \
		$(KOMPOSE_ENV_ARGS) KOMPOSE_IMAGE_PULL_POLICY=IfNotPresent kompose convert --with-kompose-annotation=false $$PROFILE_ARG -f docker-compose.yml -o k8s/; \
	else \
		PROFILE_ARG=""; \
		KOMPOSE_ENV_ARGS=""; \
		echo "---> No specific TARGET (cpu/gpu) for Kompose profile, only default services will be converted."; \
		$(KOMPOSE_ENV_ARGS) KOMPOSE_IMAGE_PULL_POLICY=IfNotPresent kompose convert --with-kompose-annotation=false $$PROFILE_ARG -f docker-compose.yml -o k8s/; \
	fi
	# @$(KOMPOSE_ENV_ARGS) KOMPOSE_IMAGE_PULL_POLICY=IfNotPresent kompose convert --with-kompose-annotation=false $$PROFILE_ARG -f docker-compose.yml -o k8s/ # Original line commented out
	@echo "---> Modifying generated k8s manifests..."

	@echo "Removing hostPort from deployments..."
	@find k8s -name "*-deployment.yaml" -print0 | xargs -0 --no-run-if-empty sed -i '/hostPort:/d'

	@echo "Deleting separate *persistentvolumeclaim.yaml files..."
	@find k8s -name "*persistentvolumeclaim.yaml" -print0 | xargs -0 --no-run-if-empty rm -f

	@echo "Modifying deployments to handle volumes and volumeMounts with yq..."
	@# For bot-manager: remove the docker.sock volumeMount and its volume definition
	@if [ -f k8s/bot-manager-deployment.yaml ]; then \
		echo "Processing k8s/bot-manager-deployment.yaml for volume/volumeMount removal..."; \
		yq e 'del(.spec.template.spec.containers[].volumeMounts[] | select(.name == "bot-manager-claim0"))' -i k8s/bot-manager-deployment.yaml; \
		yq e 'del(.spec.template.spec.volumes[] | select(.name == "bot-manager-claim0"))' -i k8s/bot-manager-deployment.yaml; \
	fi

	@# For postgres: convert postgres-data PVC to emptyDir
	@if [ -f k8s/postgres-deployment.yaml ]; then \
		echo "Processing k8s/postgres-deployment.yaml to convert PVC to emptyDir..."; \
		yq e '(.spec.template.spec.volumes[] | select(.name == "postgres-data") | .emptyDir) = {}' -i k8s/postgres-deployment.yaml; \
		yq e 'del(.spec.template.spec.volumes[] | select(.name == "postgres-data") | .persistentVolumeClaim)' -i k8s/postgres-deployment.yaml; \
	fi

	@# For redis: convert redis-data PVC to emptyDir
	@if [ -f k8s/redis-deployment.yaml ]; then \
		echo "Processing k8s/redis-deployment.yaml to convert PVC to emptyDir..."; \
		yq e '(.spec.template.spec.volumes[] | select(.name == "redis-data") | .emptyDir) = {}' -i k8s/redis-deployment.yaml; \
		yq e 'del(.spec.template.spec.volumes[] | select(.name == "redis-data") | .persistentVolumeClaim)' -i k8s/redis-deployment.yaml; \
	fi
	@echo "Finished processing volumes and volumeMounts."

	@echo "Updating DB_PORT in ConfigMap for admin-api to use service port..."
	@if [ -f k8s/home-dima-prod-vexa-cpu--env-configmap.yaml ]; then \
		yq e '.data.DB_PORT = "5438"' -i k8s/home-dima-prod-vexa-cpu--env-configmap.yaml; \
	fi

	@echo "Updating DB_PORT directly in admin-api-deployment.yaml..."
	@if [ -f k8s/admin-api-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "admin-api") | .env[] | select(.name == "DB_PORT") | .value) = "5438"' -i k8s/admin-api-deployment.yaml; \
	fi

	@echo "Updating DB_PORT directly in bot-manager-deployment.yaml..."
	@if [ -f k8s/bot-manager-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "bot-manager") | .env[] | select(.name == "DB_PORT") | .value) = "5438"' -i k8s/bot-manager-deployment.yaml; \
	fi

	@echo "Updating TRANSCRIPTION_COLLECTOR_URL in api-gateway-deployment.yaml to use service port..."
	@if [ -f k8s/api-gateway-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "api-gateway") | .env[] | select(.name == "TRANSCRIPTION_COLLECTOR_URL") | .value) = "http://transcription-collector:8123"' -i k8s/api-gateway-deployment.yaml; \
	fi

	@echo "Updating BOT_MANAGER_URL in api-gateway-deployment.yaml to use service port 18080..."
	@if [ -f k8s/api-gateway-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "api-gateway") | .env[] | select(.name == "BOT_MANAGER_URL") | .value) = "http://bot-manager:18080"' -i k8s/api-gateway-deployment.yaml; \
	fi

	@echo "Updating ADMIN_API_URL in api-gateway-deployment.yaml to use service port..."
	@if [ -f k8s/api-gateway-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "api-gateway") | .env[] | select(.name == "ADMIN_API_URL") | .value) = "http://admin-api:8057"' -i k8s/api-gateway-deployment.yaml; \
	fi

	@echo "Correcting image names in deployments..."
	@# Directly target known deployment files for image name correction
	@if [ -f k8s/admin-api-deployment.yaml ]; then sed -i 's|image: admin-api|image: docker.io/library/vexa-admin-api:dev|g' k8s/admin-api-deployment.yaml; fi
	@if [ -f k8s/api-gateway-deployment.yaml ]; then sed -i 's|image: api-gateway|image: docker.io/library/vexa-api-gateway:dev|g' k8s/api-gateway-deployment.yaml; fi
	@if [ -f k8s/bot-manager-deployment.yaml ]; then sed -i 's|image: bot-manager|image: docker.io/library/vexa-bot-manager:dev|g' k8s/bot-manager-deployment.yaml; fi
	@if [ -f k8s/transcription-collector-deployment.yaml ]; then sed -i 's|image: transcription-collector|image: docker.io/library/vexa-transcription-collector:dev|g' k8s/transcription-collector-deployment.yaml; fi
	@echo "Corrected image names in deployments to use 'docker.io/library/vexa-*' prefix and ':dev' tag."

	@echo "Setting imagePullPolicy: IfNotPresent for all containers using yq..."
	@# Directly target known deployment/statefulset files for imagePullPolicy update
	@for FILE in k8s/*-deployment.yaml k8s/*-statefulset.yaml; do \
		if [ -f "$$FILE" ]; then \
			echo "Processing $$FILE with yq to set imagePullPolicy: IfNotPresent..."; \
			yq e '.spec.template.spec.containers[].imagePullPolicy = "IfNotPresent"' -i "$$FILE"; \
		fi; \
	done
	@echo "Set imagePullPolicy: IfNotPresent using yq."

	@echo "--- Content of k8s/whisperlive-cpu-deployment.yaml before DEVICE_TYPE yq mod ---"
	@if [ -f k8s/whisperlive-cpu-deployment.yaml ]; then \
		(yq e '.spec.template.spec.containers[] | select(.name == "whisperlive-cpu") | .env[] | select(.name == "DEVICE_TYPE")' k8s/whisperlive-cpu-deployment.yaml || echo "DEVICE_TYPE env var not found before yq.") || true; \
	fi

	@echo "Setting/Updating DEVICE_TYPE=cpu in whisperlive-cpu-deployment.yaml..."
	@if [ -f k8s/whisperlive-cpu-deployment.yaml ]; then \
		yq e '(.spec.template.spec.containers[] | select(.name == "whisperlive-cpu") | .env) |= (map(select(.name != "DEVICE_TYPE")) + [{"name": "DEVICE_TYPE", "value": "cpu"}])' -i k8s/whisperlive-cpu-deployment.yaml; \
	fi

	@echo "--- Content of k8s/whisperlive-cpu-deployment.yaml after DEVICE_TYPE yq mod ---"
	@if [ -f k8s/whisperlive-cpu-deployment.yaml ]; then \
		(yq e '.spec.template.spec.containers[] | select(.name == "whisperlive-cpu") | .env[] | select(.name == "DEVICE_TYPE")' k8s/whisperlive-cpu-deployment.yaml || echo "DEVICE_TYPE env var not found after yq.") || true; \
	fi

	@echo "Correcting script arguments in whisperlive-cpu deployment using sed..."
	@if [ -f k8s/whisperlive-cpu-deployment.yaml ]; then \
		echo "--- Args before script correction (sed) ---"; \
		(yq e '.spec.template.spec.containers[] | select(.name == "whisperlive-cpu") | .args[1]' k8s/whisperlive-cpu-deployment.yaml) || true; \
		sed -i 's|\$$(){DEVICE_TYPE}|$${DEVICE_TYPE}|g' k8s/whisperlive-cpu-deployment.yaml; \
		echo "--- Args after script correction (sed) ---"; \
		(yq e '.spec.template.spec.containers[] | select(.name == "whisperlive-cpu") | .args[1]' k8s/whisperlive-cpu-deployment.yaml) || true; \
	fi

	@echo "Creating k8s/bot-manager-service.yaml..."
	@echo "apiVersion: v1" > k8s/bot-manager-service.yaml
	@echo "kind: Service" >> k8s/bot-manager-service.yaml
	@echo "metadata:" >> k8s/bot-manager-service.yaml
	@echo "  annotations:" >> k8s/bot-manager-service.yaml
	@echo "    kompose.generated.by: \\"manual-addition-for-internal-service\\"" >> k8s/bot-manager-service.yaml
	@echo "  labels:" >> k8s/bot-manager-service.yaml
	@echo "    io.kompose.service: bot-manager" >> k8s/bot-manager-service.yaml
	@echo "  name: bot-manager" >> k8s/bot-manager-service.yaml
	@echo "  namespace: $(K8S_NS)" >> k8s/bot-manager-service.yaml
	@echo "spec:" >> k8s/bot-manager-service.yaml
	@echo "  ports:" >> k8s/bot-manager-service.yaml
	@echo "    - name: http-bot-manager" >> k8s/bot-manager-service.yaml
	@echo "      port: 18080" >> k8s/bot-manager-service.yaml
	@echo "      targetPort: 8080" >> k8s/bot-manager-service.yaml
	@echo "  selector:" >> k8s/bot-manager-service.yaml
	@echo "    io.kompose.service: bot-manager" >> k8s/bot-manager-service.yaml
	@echo "Created k8s/bot-manager-service.yaml."

# Apply k8s manifests
k8s-apply: k8s-kind
	@echo "---> Applying manifests to namespace $(K8S_NS) (excluding traefik)..."
	@KUBECONFIG=$(KUBECONFIG) kubectl create namespace $(K8S_NS) --dry-run=client -o yaml | KUBECONFIG=$(KUBECONFIG) kubectl apply -f -
	@# Apply all YAML files except for traefik-deployment.yaml and traefik-service.yaml
	@KUBECONFIG=$(KUBECONFIG) kubectl apply -n $(K8S_NS) $(foreach file,$(filter-out k8s/traefik-deployment.yaml k8s/traefik-service.yaml, $(wildcard k8s/*.yaml)),-f $(file))
	@$(eval APPLY_BOT_IMAGE_NAME := $(shell grep BOT_IMAGE_NAME .env | cut -d= -f2 || echo "$(BOT_IMAGE_NAME)"))
	@echo "---> Setting BOT_IMAGE for bot-manager deployment to: $(APPLY_BOT_IMAGE_NAME)"
	@KUBECONFIG=$(KUBECONFIG) kubectl set env deployment/bot-manager -n $(K8S_NS) BOT_BACKEND=k8s NAMESPACE=$(K8S_NS) BOT_IMAGE=$(APPLY_BOT_IMAGE_NAME) TRANSCRIPTION_SERVICE=http://transcription-collector.$(K8S_NS).svc.cluster.local:8123
	@echo "# Grant broad permissions for development (cluster-admin). Remove or tighten in production."
	@KUBECONFIG=$(KUBECONFIG) kubectl create clusterrolebinding vexa-bot-manager-binding --clusterrole=cluster-admin --serviceaccount=$(K8S_NS):default -n $(K8S_NS) --dry-run=client -o yaml | KUBECONFIG=$(KUBECONFIG) kubectl apply -f -

	@echo "---> Triggering rollout of deployments to pick up ConfigMap changes..."
	@KUBECONFIG=$(KUBECONFIG) kubectl rollout restart deployment/admin-api -n $(K8S_NS)
	@KUBECONFIG=$(KUBECONFIG) kubectl rollout restart deployment/api-gateway -n $(K8S_NS)
	@KUBECONFIG=$(KUBECONFIG) kubectl rollout restart deployment/bot-manager -n $(K8S_NS)
	@KUBECONFIG=$(KUBECONFIG) kubectl rollout restart deployment/transcription-collector -n $(K8S_NS)

	@echo "---> Deploy complete (traefik excluded). Run 'make k8s-status' to watch pods."

# Full pipeline: kind cluster, build, load images, generate manifests, apply
k8s-deploy: k8s-kind k8s-build k8s-load k8s-generate k8s-apply

# Show pod status
k8s-status:
	@KUBECONFIG=$(KUBECONFIG) kubectl get pods -n $(K8S_NS) -o wide

# Port forward essential services for local development access
k8s-port-forward: check_docker k8s-kind
	@echo "---> Starting port-forwarding (in background)..."
	@KUBECONFIG=$(KUBECONFIG) kubectl port-forward -n $(K8S_NS) --address 0.0.0.0 svc/api-gateway $(API_GATEWAY_HOST_PORT):8056 > /tmp/pf-api-gateway-$(API_GATEWAY_HOST_PORT).log 2>&1 & echo "API Gateway: localhost:$(API_GATEWAY_HOST_PORT) -> api-gateway (svc port 8056 -> pod port 8000)"
	@KUBECONFIG=$(KUBECONFIG) kubectl port-forward -n $(K8S_NS) --address 0.0.0.0 svc/admin-api $(ADMIN_API_HOST_PORT):8057 > /tmp/pf-admin-api-$(ADMIN_API_HOST_PORT).log 2>&1 & echo "Admin API: localhost:$(ADMIN_API_HOST_PORT) -> admin-api (svc port 8057 -> pod port 8001)"
	@KUBECONFIG=$(KUBECONFIG) kubectl port-forward -n $(K8S_NS) --address 0.0.0.0 svc/transcription-collector $(TRANSCRIPTION_COLLECTOR_HOST_PORT):8123 > /tmp/pf-transcription-collector-$(TRANSCRIPTION_COLLECTOR_HOST_PORT).log 2>&1 & echo "Transcription Collector: localhost:$(TRANSCRIPTION_COLLECTOR_HOST_PORT) -> transcription-collector (svc port 8123 -> pod port 8000)"
	@echo "Port forwarding started. Check /tmp/pf-*.log for errors. Use 'make k8s-port-forward-stop' to stop."

k8s-port-forward-stop:
	@echo "---> Stopping port-forwarding..."
	-@pkill -f "kubectl port-forward -n $(K8S_NS) .* svc/api-gateway $(API_GATEWAY_HOST_PORT):"
	-@pkill -f "kubectl port-forward -n $(K8S_NS) .* svc/admin-api $(ADMIN_API_HOST_PORT):"
	-@pkill -f "kubectl port-forward -n $(K8S_NS) .* svc/transcription-collector $(TRANSCRIPTION_COLLECTOR_HOST_PORT):"
	@echo "Port forwarding stopped."

# Delete the kind cluster
k8s-delete-cluster:
	@echo "---> Deleting kind cluster '$(KIND_NAME)'..."
	@kind delete cluster --name $(KIND_NAME)

# Tail logs for a specific pod in the vexa namespace
# Usage: make k8s-logs pod=admin-api (will match first pod for that service)
k8s-logs:
ifndef pod
	$(error Please specify pod name to tail logs, e.g., make k8s-logs pod=admin-api)
endif
	@echo "---> Tailing logs for first pod matching '$(pod)' in namespace $(K8S_NS)..."
	@KUBECONFIG=$(KUBECONFIG) kubectl logs -n $(K8S_NS) $$(KUBECONFIG=$(KUBECONFIG) kubectl get pods -n $(K8S_NS) -l io.kompose.service=$(pod) -o jsonpath='{.items[0].metadata.name}') -f

# Get shell access to a running pod
# Usage: make k8s-shell pod=admin-api
k8s-shell:
ifndef pod
	$(error Please specify pod name to get shell access, e.g., make k8s-shell pod=admin-api)
endif
	@echo "---> Getting shell for first pod matching '$(pod)' in namespace $(K8S_NS)..."
	@KUBECONFIG=$(KUBECONFIG) kubectl exec -n $(K8S_NS) -it $$(KUBECONFIG=$(KUBECONFIG) kubectl get pods -n $(K8S_NS) -l io.kompose.service=$(pod) -o jsonpath='{.items[0].metadata.name}') -- /bin/sh || KUBECONFIG=$(KUBECONFIG) kubectl exec -n $(K8S_NS) -it $$(KUBECONFIG=$(KUBECONFIG) kubectl get pods -n $(K8S_NS) -l io.kompose.service=$(pod) -o jsonpath='{.items[0].metadata.name}') -- /bin/bash

# Describe a specific pod in the vexa namespace
# Usage: make k8s-describe-pod pod=admin-api
k8s-describe-pod:
ifndef pod
	$(error Please specify pod name to describe, e.g., make k8s-describe-pod pod=admin-api)
endif
	@echo "---> Describing first pod matching '$(pod)' in namespace $(K8S_NS)..."
	@KUBECONFIG=$(KUBECONFIG) kubectl describe pod -n $(K8S_NS) $$(KUBECONFIG=$(KUBECONFIG) kubectl get pods -n $(K8S_NS) -l io.kompose.service=$(pod) -o jsonpath='{.items[0].metadata.name}')
