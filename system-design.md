# Vexa System Design

This document outlines the architecture of the Vexa application based on its Docker Compose configuration and recent code analysis.

## Overview

Vexa is a multi-service application orchestrated using Docker Compose. It primarily provides real-time transcription capabilities, alongside administrative functions and bot management. Key technologies include Python (FastAPI for backend services), Whisper (for transcription via WhisperLive), Redis (for messaging via Streams and Pub/Sub, and temporary storage via Hashes/Sets), PostgreSQL (for persistent storage), and Traefik (as a reverse proxy/load balancer).

## Services

The system is composed of the following services:

### 1. `api-gateway`

*   **Purpose**: Acts as the primary entry point for external API requests. It routes incoming traffic to the appropriate backend services (`bot-manager`, `transcription-collector`, `admin-api`) and forwards necessary authentication headers.
*   **Technology**: FastAPI (Python).
*   **Build**: `services/api-gateway/Dockerfile`
*   **Ports**: Host `8056` -> Container `8000`
*   **Routing Logic**:
    *   Uses a generic `forward_request` helper.
    *   `POST /bots`, `DELETE /bots/...`: Forwards to `bot-manager`.
    *   `PUT /bots/{platform}/{native_meeting_id}/config`: Forwards to `bot-manager`.
    *   `GET /meetings`, `GET /transcripts/...`: Forwards to `transcription-collector`.
    *   `/admin/*` (all methods): Forwards to `admin-api`.
    *   `/usage/quote`: (Future - Will need routing to `admin-api`)
*   **Authentication Handling**:
    *   Expects `X-API-Key` header for non-admin routes.
    *   Forwards `X-API-Key` to `bot-manager` and `transcription-collector`.
    *   Expects `X-Admin-API-Key` header for `/admin/*` routes.
    *   Forwards `X-Admin-API-Key` to `admin-api`.
*   **Dependencies**: `admin-api`, `bot-manager`, `transcription-collector`
*   **Key Config**: Relies on environment variables (`ADMIN_API_URL`, `BOT_MANAGER_URL`, `TRANSCRIPTION_COLLECTOR_URL`) to know the addresses of downstream services.
*   **Network**: `vexa_default`
*   **Other**: Provides OpenAPI (Swagger) documentation for the exposed API endpoints.

### 2. `admin-api`

*   **Purpose**: Provides administrative API endpoints for managing users, API tokens (`X-API-Key`), Plans (including transcription model limits), User Plan assignments, and user referral/UTM data.
*   **Technology**: FastAPI (Python). Organized into routers (`core.py`, `billing.py`) and CRUD modules (`app/crud/`).
*   **Build**: `services/admin-api/Dockerfile`
*   **Ports**: Host `8057` -> Container `8001`
*   **Authentication**:
    *   Requires a static `ADMIN_API_TOKEN` (set via environment variable) sent in the `X-Admin-API-Key` header for most `/admin/*` endpoints (applied globally in `main.py`).
    *   The `/admin/internal/log_referral` endpoint requires standard user authentication (implementation pending).
*   **API Endpoints** (prefixed with `/admin`):
    *   **Users & Tokens:**
        *   `POST /users`: Create a new user.
        *   `GET /users`: List users.
        *   `GET /users/{user_id}`: Get a specific user.
        *   `DELETE /users/{user_id}`: Delete a user.
        *   `POST /users/{user_id}/tokens`: Generate a new API token for a specific user.
        *   `DELETE /tokens/{token_value}`: Delete a token by its value.
    *   **Billing - Plans:**
        *   `POST /plans`: Create a new plan (optionally with model limits).
        *   `GET /plans`: List plans.
        *   `GET /plans/{plan_id}`: Get a specific plan.
        *   `PUT /plans/{plan_id}`: Update a plan.
        *   `DELETE /plans/{plan_id}`: Delete a plan.
    *   **Billing - User Plans:**
        *   `POST /users/{user_id}/plan`: Assign/Update a plan for a user.
        *   `GET /users/{user_id}/plan`: Get the plan assigned to a user.
        *   `PUT /users/{user_id}/plan`: Update a user's plan assignment details.
        *   `DELETE /users/{user_id}/plan`: Remove a plan assignment from a user.
    *   **Billing - Internal:**
        *   `POST /internal/log_referral`: Log UTM/referer data for the authenticated user. (Requires user auth)
        *   *(Future)* `GET /internal/check_limits`: Internal endpoint for `bot-manager` to check usage/concurrency.
    *   **Usage (Future):**
        *   *(Future)* `GET /usage/quote`: User-facing endpoint to query usage.
*   **Database Interaction**: Interacts directly with PostgreSQL (`shared_models`) to manage `User`, `APIToken`, `Plan`, `PlanModelLimit`, `UserPlan`, and `ReferralData` records.
*   **Dependencies**: `postgres` (healthy).
*   **Key Config**: Connects to `postgres`. Uses `.env` file for configuration (including the `ADMIN_API_TOKEN`).
*   **Network**: `vexa_default`
*   **Structure**: Routes organized into `app/api/routes/core.py` and `app/api/routes/billing.py`. CRUD logic in `app/crud/`.

### 3. `bot-manager`

*   **Purpose**: Provides an API to manage the lifecycle of `vexa-bot` instances. Acts as a controller for the bots.
*   **Build**: `services/bot-manager/Dockerfile`
*   **API Endpoints**:
    *   `POST /bots`: Start a bot. **(Will require `model_identifier` in request)**
    *   `DELETE /bots/{platform}/{native_meeting_id}`: Stop a bot.
    *   `PUT /bots/{platform}/{native_meeting_id}/config`: Update `language`/`task` for an active bot.
*   **Authentication**: Authenticates incoming API requests using user tokens sent in the `X-API-Key` header. It verifies the token against the `APIToken` table and retrieves the associated `User` from the `User` table in PostgreSQL (via `auth.py`).
*   **Database Interaction**: Uses PostgreSQL (`shared_models`) to:
    *   Track meeting state (`Meeting` table).
    *   Track bot sessions (`MeetingSession` table).
    *   Prevent duplicate active bot sessions for the same user/platform/native ID.
*   **Limit Checking (Future):**
    *   Will call `admin-api:/admin/internal/check_limits` before starting a bot, passing `user_id` and `model_identifier`.
    *   Will use Redis Set `active_bots:{user_id}` to enforce overall concurrency limit from the API response.
*   **Docker Interaction**: Uses `requests_unixsocket` to communicate with the host's Docker daemon.
*   **Redis Interaction**: Uses Redis (`aioredis` client) for:
    *   **Pub/Sub Commands:** `bot_commands:{connectionId}` channel for `reconfigure`/`leave`.
    *   **Concurrency Tracking (Future):** Manages `active_bots:{user_id}` Set.
*   **Dependencies**: `redis` (started), `postgres` (healthy), Docker daemon access, `admin-api` (for future limit checks).
*   **Key Config**:
    *   Uses `BOT_IMAGE=vexa-bot:latest`.
    *   Connects to `postgres`, `redis`.
    *   Requires Docker daemon access.
    *   Specifies `DOCKER_NETWORK=vexa_vexa_default`.
*   **Network**: `vexa_default`

### 3a. `vexa-bot` (Managed Container Image)

*   **Purpose**: Headless browser automation bot to join meetings, capture audio, and respond to Redis commands.
*   **Technology**: Node.js/TypeScript, Playwright, `redis`.
*   **Execution**: Runs within a container based on `services/vexa-bot/core/Dockerfile`.
*   **Control**: Launched and stopped by `bot-manager`. Receives context via `BOT_CONFIG` environment variable.
*   **Interaction**:
    *   Joins meeting, captures audio.
    *   Establishes WebSocket connection(s) to `WHISPER_LIVE_URL`.
    *   **WebSocket Session Handling:** For *each* WebSocket connection, it:
        *   Generates a **new unique UUID** (`uid`).
        *   Sends this **new UUID** and **(Future) the requested `model_identifier`** in the initial JSON configuration message.
    *   Sends audio chunks via WebSocket.
    *   **Redis Command Subscription:** Subscribes to `bot_commands:{original_connectionId}`.
*   **Network**: Launched onto `vexa_vexa_default`. Needs access to `whisperlive` and `redis`.

### 4. `whisperlive`

*   **Purpose**: Performs real-time audio transcription using the `faster-whisper` backend. Receives audio via WebSocket, publishes transcription segments and session start events to a Redis Stream.
*   **Build**: `services/WhisperLive/Dockerfile.project`
*   **Ports**: Exposes `9090` (service) and `9091` (healthcheck).
*   **Dependencies**: `transcription-collector` (started), `redis`.
*   **Deployment**: 1 replica.
*   **Key Config**:
    *   Receives audio via WebSocket on port 9090.
    *   Accepts initial JSON config message containing `uid`, `token`, meeting details, etc.
    *   **(Future Prerequisite)** Needs modification to include the actual `model_identifier` being used in the `session_start` event payload sent to Redis.
    *   Uses Redis Streams (`REDIS_STREAM_URL`, `REDIS_STREAM_NAME=transcription_segments`) for outputting `session_start` and `transcription` events.
*   **Healthcheck**: `http://localhost:9091/health`
*   **Network**: `vexa_default`, `whispernet`. (Redundancy note remains)
*   **Traefik Integration**: Uses labels for discovery.

### 5. `traefik`

*   **Purpose**: Modern reverse proxy and load balancer. Handles incoming HTTP requests, service discovery (via Docker labels), and routing to backend services, particularly `whisperlive`.
*   **Image**: `traefik:v2.10`
*   **Ports**: Host `9090` -> Container `80` (service traffic), Host `8085` -> Container `8080` (Traefik dashboard)
*   **Dependencies**: None explicit, but relies on other services running and being labeled correctly for discovery.
*   **Key Config**:
    *   Uses Docker provider for service discovery (`--providers.docker=true`).
    *   Requires explicit labels on services to expose them (`--providers.docker.exposedbydefault=false`).
    *   Listens on port `80` internally (`--entrypoints.web.address=:80`).
    *   Configured via `traefik.toml` (mounted volume).
*   **Network**: `vexa_default`, `whispernet`. *(Note: `whispernet` appears redundant)*.

### 6. `transcription-collector`

*   **Purpose**: Consumes events (`session_start`, `transcription`) from the `transcription_segments` Redis Stream. Processes segments, stores them temporarily, persists them, handles sessions, and provides retrieval API.
*   **Technology**: FastAPI (Python).
*   **Build**: `services/transcription-collector/Dockerfile`
*   **Ports**: Host `8123` -> Container `8000`
*   **Dependencies**: `redis` (started), `postgres` (healthy)
*   **Key Config**:
    *   Connects to `postgres`.
    *   Connects to `redis` to consume from stream.
    *   **Stream Processing (Future):**
        *   Processes `session_start` events: Will parse `model_identifier`, create/update `MeetingSession` record in PostgreSQL (including `model_identifier`, `uid`, `start_timestamp`). **Will initialize Redis cache `session_agg:{uid}` for caching usage.**
        *   Processes `transcription` events: Looks up user/meeting, **updates aggregates in Redis Hash `session_agg:{uid}` (`max_end_time`, `total_segment_duration_seconds`), adds `uid` to `dirty_sessions` Redis Set.** Stores immutable segments in `meeting:{id}:segments` Hash (existing logic).
    *   Background task (`process_redis_to_postgres`): **(Future) Will flush aggregate data from `session_agg:{uid}` Hashes to `MeetingSession` table in PostgreSQL based on `dirty_sessions` Set.** Also moves immutable segments (existing logic).
*   **Network**: `vexa_default`

### 7. `redis`

*   **Purpose**: In-memory data store used for:
    *   **Message Brokering (Streams):** `transcription_segments`.
    *   **Message Brokering (Pub/Sub):** `bot_commands:{connectionId}`.
    *   **Temporary Segment Storage:** Redis Hashes (`meeting:{id}:segments`).
    *   **Active Meeting Tracking:** Redis Sets (`active_meetings`).
    *   **(Future)** **Concurrency Tracking:** Redis Sets (`active_bots:{user_id}`).
    *   **(Future)** **Usage Aggregate Caching:** Redis Hashes (`session_agg:{session_uid}`) and Set (`dirty_sessions`).
*   **Image**: `redis:7.0-alpine`
*   **Persistence**: Append-only file.
*   **Network**: `vexa_default`

### 8. `postgres`

*   **Purpose**: Relational database backend used by `admin-api`, `bot-manager`, and `transcription-collector`.
*   **Image**: `postgres:15-alpine`
*   **Schema**: Contains tables `users`, `api_tokens`, `meetings`, `meeting_sessions`, `transcriptions`, **`plans`, `plan_model_limits`, `user_plans`, `referral_data`**.
*   **Key Table Changes:**
    *   `meeting_sessions` now includes `model_identifier`, `max_end_time`, `total_segment_duration_seconds`, `last_updated`.
*   **Ports**: Host `5438` -> Container `5432`
*   **Persistence**: `postgres-data` volume.
*   **Healthcheck**: `pg_isready`.
*   **Network**: `vexa_default`

## Networking

*   **`vexa_default`**: A bridge network providing the primary communication channel for most services.
*   **`vexa_vexa_default`**: A network seemingly created implicitly by Docker Compose, onto which `bot-manager` launches `vexa-bot` containers. Connectivity exists between this network and `vexa_default` allowing bots to reach `whisperlive` and `redis`.
*   **`whispernet`**: A separate bridge network connecting only `whisperlive` and `traefik`. **This network appears redundant** as communication can occur over `vexa_default`. Simplifying by removing it is recommended.

## Volumes

*   **`redis-data`**: Named volume for persisting Redis data.
*   **`postgres-data`**: Named volume for persisting PostgreSQL data.
*   **`/var/run/docker.sock` (Mount)**: Host Docker socket mounted into `bot-manager` to allow Docker operations.
*   **`./hub` (Mount)**: Host directory mounted into `whisperlive` for Hugging Face model cache.
*   **`./services/WhisperLive/models` (Mount)**: Host directory mounted into `whisperlive` for local models.
*   **`./traefik.toml` (Mount)**: Host configuration file mounted into `traefik`.

## Configuration Files

*   **`.env`**: This file is explicitly loaded by the `admin-api` service. It **must contain the `ADMIN_API_TOKEN`** used for authenticating administrative requests. It may also contain other sensitive configurations or override environment variables defined elsewhere (though only `admin-api` is explicitly configured to load it).
*   **`traefik.toml`**: Configuration file for the `traefik` service, mounted read-only. Defines entrypoints, providers, etc.
*   **`filter_config.py`**: Optional Python file confirmed to exist in `services/transcription-collector/`. Used by `filters.py` (via dynamic import) to load custom filtering rules (regex patterns, stopwords, length/word counts, custom functions). If absent, defaults are used.

## Data Schemas (Pydantic)

Defined in `shared_models/schemas.py`:

*   **Core Schemas:** `Platform`, `UserCreate`, `UserResponse`, `TokenResponse`, `MeetingCreate` **(now includes `model_identifier`)**, `MeetingResponse`, `MeetingSessionResponse` **(updated with new fields)**, `TranscriptionSegment`, `WhisperLiveData` **(now includes `model_identifier`)**, `TranscriptionResponse`, `HealthResponse`, `ErrorResponse`, `MeetingListResponse`.
*   **Billing Schemas:** `PlanModelLimitBase`, `PlanModelLimitCreate`, `PlanModelLimitResponse`, `PlanBase`, `PlanCreate`, `PlanUpdate`, `PlanResponse`, `UserPlanBase`, `UserPlanCreate`, `UserPlanUpdate`, `UserPlanResponse`, `ReferralDataBase`, `ReferralDataCreate`, `ReferralDataResponse`.
*   **Internal Schemas:** `InternalReferralLogRequest`, `InternalLimitCheckResponse`, `UsageQuoteResponse`.

## Data Flow (Transcription & Reconfiguration Example)

**Initial Bot Start & Transcription:**

1.  `bot-manager` receives `POST /bots` **(with future `model_identifier`)**, generates `connectionId`, starts `vexa-bot` container, records `MeetingSession` (Session A).
2.  `vexa-bot` starts, connects Redis, subscribes to `bot_commands:conn_A`.
3.  `vexa-bot` joins meeting, establishes WebSocket.
4.  `vexa-bot` generates `uid_1`, sends WebSocket config message with `uid: uid_1`, **(future) `model_identifier`**.
5.  `whisperlive` receives connection, **(future) parses `model_identifier`**, publishes `session_start` event with `uid: uid_1` **and (future) `model_identifier`** to Redis Stream.
6.  `transcription-collector` consumes `session_start` event, **(future) parses `model_identifier`**, creates new `MeetingSession` record (Session B) with `uid: uid_1` and `model_identifier`. **(Future) Initializes Redis cache `session_agg:uid_1`.**
7.  `vexa-bot` sends audio. `whisperlive` transcribes, publishes `transcription` events with `uid: uid_1`.
8.  `transcription-collector` consumes `transcription` events, validates, **(future) updates Redis cache `session_agg:uid_1`**, stores segments in Redis Hash `meeting:{id}:segments`.

**Runtime Reconfiguration:**

*(Flow remains largely the same, but subsequent reconnections will generate new `uid`s and trigger new `session_start` events and `MeetingSession` records/cache entries)*

**Graceful Stop:**

*(Flow remains the same, but `bot-manager` will also remove entry from `active_bots:{user_id}` Redis Set in Phase 2)*

## Conclusion (Updated)

The system now includes foundational database structures (`Plan`, `PlanModelLimit`, `UserPlan`, `ReferralData`, updated `MeetingSession`) and basic administrative API endpoints for managing these. Key next steps involve modifying `whisperlive` to report model usage, implementing usage aggregation in `transcription-collector`, and adding limit enforcement logic to `bot-manager` and `admin-api`.

**Key Issues Identified:**

*   **`bot-manager` Redis Client (Partial)**: Locking/mapping client still inactive.
*   **Unused Config**: `admin-api` Redis config, `transcription-collector` `REDIS_CLEANUP_THRESHOLD`.
*   **Redundant Networking**: `whispernet`.
*   **Outdated Bot Code**: `transcript-adapter.js`.
*   **WhisperLive Replicas**: >1 replica issue remains relevant.
*   **Prerequisite Pending:** `whisperlive` needs modification to report `model_identifier`.
*   **Pending Implementation:** Limit logic (`admin-api`, `bot-manager`), Usage aggregation (`transcription-collector`), User Auth for referral endpoint (`admin-api`).

docker build -t vexa-bot:latest -f services/vexa-bot/core/Dockerfile services/vexa-bot/core