# Vexa System Design (Based on docker-compose.yml)

*This document outlines the architecture of the Vexa system as defined by the `docker-compose.yml` configuration. It will be updated as further components are explored.*

## Overview

The Vexa system is a multi-container application orchestrated using Docker Compose. It comprises several microservices handling tasks such as API gateway routing, administration, bot management, real-time audio transcription, data collection, and persistence. The system utilizes PostgreSQL for relational data, Redis for caching/messaging, and Nginx for load balancing the transcription service.

## Services

### 1. `api-gateway`
*   **Build:** `services/api-gateway/Dockerfile`
*   **Purpose:** Acts as the primary entry point for external requests, routing traffic to backend services.
*   **Ports:** `8056` (host) -> `8000` (container)
*   **Environment:**
    *   `ADMIN_API_URL=http://admin-api:8001`
    *   `BOT_MANAGER_URL=http://bot-manager:8080`
    *   `TRANSCRIPTION_COLLECTOR_URL=http://transcription-collector:8000`
    *   `LOG_LEVEL=DEBUG`
*   **Dependencies:** `admin-api`, `bot-manager`, `transcription-collector` (waits for service start)
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`

### 2. `admin-api`
*   **Build:** `services/admin-api/Dockerfile`
*   **Purpose:** Provides an API for administrative functions.
*   **Ports:** `8057` (host) -> `8001` (container)
*   **Environment:**
    *   Loads variables from `.env` file.
    *   `REDIS_URL=redis://redis:6379/0`
    *   `DB_HOST=postgres`, `DB_PORT=5432`, `DB_NAME=vexa`, `DB_USER=postgres`, `DB_PASSWORD=postgres`
    *   `LOG_LEVEL=DEBUG`
*   **Dependencies:** `redis` (service started), `postgres` (service healthy)
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`

### 3. `bot-manager`
*   **Build:** `services/bot-manager/Dockerfile`
*   **Purpose:** Manages bot instances, likely interacting with the Docker daemon to start/stop other containers.
*   **Environment:**
    *   `REDIS_URL=redis://redis:6379/0`
    *   `BOT_IMAGE=vexa-bot:latest` (Image for the bots it manages)
    *   `DOCKER_NETWORK=vexa_vexa_default` (Network for managed bots)
    *   `LOG_LEVEL=DEBUG`
    *   `DB_HOST=postgres`, `DB_PORT=5432`, `DB_NAME=vexa`, `DB_USER=postgres`, `DB_PASSWORD=postgres`
    *   `DOCKER_HOST=unix://var/run/docker.sock`
*   **Volumes:** `/var/run/docker.sock:/var/run/docker.sock` (Allows interaction with host Docker daemon)
*   **Dependencies:** `redis` (service started), `postgres` (service healthy)
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`

### 4. `whisperlive`
*   **Build:** `services/WhisperLive/Dockerfile.project`
*   **Purpose:** Real-time transcription service using the Whisper model, scaled to multiple replicas and utilizing GPU resources.
*   **Volumes:**
    *   `./hub:/root/.cache/huggingface/hub` (Hugging Face cache)
    *   `./services/WhisperLive/models:/app/models` (Local models)
*   **Environment:** `TRANSCRIPTION_COLLECTOR_URL=ws://transcription-collector:8000/collector`
*   **Command:** `["--port", "9090", "--backend", "faster_whisper", "-fw", "/root/.cache/huggingface/hub/models--Systran--faster-whisper-medium/snapshots/08e178d48790749d25932bbc082711ddcfdfbc4f"]`
*   **Deployment:**
    *   `replicas: 3`
    *   GPU reservation: `device_ids: ['3']`, `driver: nvidia`
*   **Dependencies:** `transcription-collector` (service started)
*   **Networks:** `vexa_default`, `whispernet`
*   **Restart:** `unless-stopped`
*   **Logging:** JSON driver, max size 10m, 3 files.

### 5. `load-balancer`
*   **Image:** `nginx:latest`
*   **Purpose:** Reverse proxy and load balancer for the `whisperlive` replicas.
*   **Ports:** `9090` (host) -> `80` (container)
*   **Volumes:** `./nginx.conf:/etc/nginx/nginx.conf:ro` (Custom Nginx config)
*   **Dependencies:** `whisperlive`
*   **Network:** `whispernet`

### 6. `load-tester`
*   **Build:** `load-tester/Dockerfile`
*   **Purpose:** Container environment for running load tests against the transcription service.
*   **Volumes:**
    *   `./load_test_client.py:/app/load_test_client.py`
    *   `./test_audio:/app/test_audio`
*   **Working Dir:** `/app`
*   **Command:** `sleep infinity` (Allows manual execution of tests)
*   **Dependencies:** `load-balancer`
*   **Network:** `whispernet`

### 7. `transcription-collector`
*   **Build:** `services/transcription-collector/Dockerfile`
*   **Purpose:** Collects transcription results (likely via WebSocket from `whisperlive`) and interacts with storage.
*   **Ports:** `8123` (host) -> `8000` (container)
*   **Environment:**
    *   `DB_HOST=postgres`, `DB_PORT=5432`, `DB_NAME=vexa`, `DB_USER=postgres`, `DB_PASSWORD=postgres`
    *   `REDIS_HOST=redis`, `REDIS_PORT=6379`
    *   `LOG_LEVEL=DEBUG`
*   **Dependencies:** `redis` (service started), `postgres` (service healthy)
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`

### 8. `redis`
*   **Image:** `redis:7.0-alpine`
*   **Purpose:** In-memory data store (cache, message queue).
*   **Volumes:** `redis-data:/data` (Persistence)
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`

### 9. `postgres`
*   **Image:** `postgres:15-alpine`
*   **Purpose:** Relational database.
*   **Environment:** `POSTGRES_DB=vexa`, `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`
*   **Volumes:** `postgres-data:/var/lib/postgresql/data` (Persistence)
*   **Healthcheck:** `pg_isready -U postgres -d vexa`
*   **Network:** `vexa_default`
*   **Restart:** `unless-stopped`
*   **Ports:** `5438` (host) -> `5432` (container) (For external access/debugging)

## Volumes

*   **`redis-data`:** Persists Redis data.
*   **`postgres-data`:** Persists PostgreSQL data.

## Networks

*   **`vexa_default`:** (Bridge) Default network for most inter-service communication.
*   **`whispernet`:** (Bridge) Dedicated network for transcription services (`whisperlive`, `load-balancer`, `load-tester`), isolating high-volume traffic.

## Inferred Flow

1.  **External Interaction:** `api-gateway` (port `8056`) receives external requests.
2.  **Routing:** `api-gateway` routes to `admin-api`, `bot-manager`, or `transcription-collector`.
3.  **Bot Management:** `bot-manager` uses the Docker socket to manage separate `vexa-bot` containers.
4.  **Data Storage:** Services use `postgres` for structured data and `redis` for caching/messaging.
5.  **Transcription Pipeline:**
    *   Audio likely sent to `load-balancer` (port `9090`).
    *   `load-balancer` distributes requests to `whisperlive` replicas (`whispernet`).
    *   `whisperlive` performs transcription using GPU resources.
    *   Results sent via WebSocket to `transcription-collector`.
    *   `transcription-collector` processes/stores results.
6.  **Testing:** `load-tester` can initiate tests against the `load-balancer`.

---
*Further Exploration Needed: Dockerfiles, `nginx.conf`, `.env` details, Source Code structure (`services/` subdirectories), `load_test_client.py`.* 