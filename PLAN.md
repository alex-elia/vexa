# Vexa Simplified Implementation Plan: UTM Tracking, Concurrency, Per-Model Usage Limits & Quote

## 1. Objectives

*   Implement basic user attribution tracking via UTM parameters and referers.
*   Enforce limits on the number of concurrent bot sessions per user based on assigned plans.
*   Introduce a simple monthly usage limit (in hours) **per transcription model type** per user, based on assigned plans.
*   Provide an efficient API endpoint for users to query their usage (total duration, potentially filterable by model) within a given period.
*   Establish foundational elements (Plans, per-model limits, usage aggregation) that align closer to potential future billing needs.

## 2. Rationale

*   The original `PLAN.md` detailed a comprehensive billing system, which was initially simplified.
*   This revised plan re-introduces **per-model usage limits** based on user requirements, adding back some complexity but targeting specific control needs.
*   It focuses on controlling resource usage (concurrency, total hours per model) and understanding user acquisition (UTM).
*   It leverages Redis for fast concurrency checks and introduces an aggregation table (`SessionUsageSummary`) for efficient usage calculation per model, per session.

## 3. Core Requirements

*   **Database:**
    *   `Base` defined in `database.py`.
    *   Core models (`User`, `APIToken`, `Meeting`, `Transcription`, `MeetingSession`) in `models.py`.
    *   Billing models (`Plan`, `PlanModelLimit`, `UserPlan`, `ReferralData`) in `billing_models.py`.
    *   **Modify `MeetingSession` table:** Add `model_identifier`, `max_end_time` (Float), `total_segment_duration_seconds` (Numeric), `last_updated` columns. **(Implemented in Phase 1)**
*   **Services:**
    *   `admin-api`:
        *   Endpoint (`/admin/internal/log_referral`) to receive and store UTM/referer data (called by client-side). **(Basic endpoint implemented in Phase 1)**
        *   Admin endpoints to manage `Plan` definitions (including nested `PlanModelLimit`) and `UserPlan` assignments. **(Basic CRUD implemented in Phase 1)**
        *   **NEW (Phase 3):** Internal endpoint (`/internal/check_limits`) queried by `bot-manager`:
            *   Accepts `user_id` and `model_identifier`.
            *   Checks monthly usage for that *specific model* against plan limits (querying `PlanModelLimit` and **`MeetingSession`**/**`Meeting`** tables).
            *   Retrieves the overall concurrency limit from the `Plan`.
            *   Returns usage status and concurrency limit.
        *   **NEW (Phase 3):** User-facing endpoint (`/usage/quote`) to report total usage duration for a given period (querying **`MeetingSession`**/**`Meeting`** tables), potentially allowing filtering by model.
    *   `transcription-collector` **(Phase 3):**
        *   Modify processing of `session_start` events to parse `model_identifier`, store it in `MeetingSession`, and initialize usage aggregate fields.
        *   Modify processing of `transcription` events to look up the `MeetingSession` row via `session_uid` and update its usage aggregate fields (`max_end_time`, increment `total_segment_duration_seconds`, `last_updated`).
    *   `bot-manager` **(Phase 2):**
        *   Pass the requested `model_identifier` when calling **`admin-api`**'s `/internal/check_limits`.
        *   Call **`admin-api`** to check usage (for the specific model) and get concurrency limit before starting a bot.
        *   Use Redis Set (`active_bots:{user_id}`) to track and enforce the retrieved concurrency limit.
        *   Update the Redis Set when bots start and stop.
*   **Client-Side:**
    *   User-facing application needs a script to capture UTM/referer data and send it to the `admin-api` endpoint.

## 4. Prerequisites

*   **Modify `whisperlive`:** The `whisperlive` service **must** be updated to include the `actual_model_identifier` being used for transcription in the **`session_start` event** published to the `transcription_segments` Redis Stream. This identifier is required for per-model usage tracking and limit enforcement. **(Still Pending)**

## 5. Uncertainties & Assumptions (Post-Verification)

*   **Schema Details:** Resolved.
*   **`MeetingSession.model_identifier` Source:** Requires implementation in `whisperlive`. Status: Implementation Required.
*   **Timestamp Precision/Timezones:** Recommendation: New fields use `DateTime(timezone=True)`. Existing require care. Status: Implemented with `DateTime(timezone=True)`. Requires careful handling in queries.
*   **Client-Side UTM Implementation:** External Dependency.
*   **Usage Granularity Metric:** Using **Sum of `MeetingSession.max_end_time`**. Each `max_end_time` represents the duration of a specific WebSocket connection instance (relative to its own start=0). Summing these across relevant sessions provides total active usage time. `total_segment_duration_seconds` also stored for potential alternative analysis. Status: Design Decision Confirmed (User disregard concern).
*   **Performance:** **Mitigation:** `transcription-collector` will use **Redis Hashes + a Set** for caching aggregates + periodic flush (e.g., every 10s) to avoid excessive DB UPDATEs on `MeetingSession`. This reduces DB write load significantly. Performance of Redis ops, flush task, and `admin-api` queries needs monitoring. **Status: Concern Mitigated - Requires Monitoring.**
*   **Data Consistency:** Usage data in PG DB will lag slightly behind real-time Redis cache (by flush interval). Limit checks use PG DB data. Status: Known Limitation (Acceptable Delay Confirmed).
*   **Scalability/Maintainability:** Architectural Concern (Caching adds complexity).
*   **Edge Cases:** Implementation Design Concern.

---

**Phase 1: Foundations - Database Models & Basic Setup (Implemented)**

1.  **Define/Refine Database Schemas:** **(DONE)**
    *   **`Base` definition moved to `libs/shared-models/shared_models/database.py`**.
    *   **Core Models (`libs/shared-models/shared_models/models.py`):** **(DONE)**
        *   Kept `User`, `APIToken`, `Meeting`, `Transcription`.
        *   Modified `MeetingSession` Table (added `model_identifier`, `max_end_time`, `total_segment_duration_seconds`, `last_updated`).
    *   **Billing Models (`libs/shared-models/shared_models/billing_models.py`) (New File):** **(DONE)**
        *   Created file.
        *   Defined `Plan`, `PlanModelLimit`, `UserPlan`, `ReferralData` models inheriting `Base` from `database.py`.
    *   **Removed `SessionUsageSummary` Table definition.** **(N/A - Was not created)**
2.  **Centralize Redis Key Management (`libs/shared-models/shared_models/redis_keys.py`) (New Task):** **(DONE)**
    *   Created the new file `redis_keys.py`.
    *   Defined constants and helper functions.
3.  **Update `libs/shared-models/shared_models/schemas.py`:** **(DONE)**
    *   Added/updated Pydantic schemas for `Plan`, `PlanModelLimit`, `UserPlan`, `ReferralData`, internal API requests/responses.
    *   Modified `MeetingSessionResponse`, `MeetingCreate`, `WhisperLiveData`.
4.  **Refactor `whisperlive` Redis Usage (Minor Refactor):** **(PENDING - Requires `whisperlive` changes)**
    *   Update `whisper_live/server.py` to use `redis_keys.py`.
5.  **Enhance `admin-api`:** **(DONE - Basic CRUD & Routes)**
    *   Refactored routes into `app/api/routes/core.py` and `app/api/routes/billing.py`.
    *   Created `app/crud/` directory with `crud_plan.py`, `crud_user_plan.py`, `crud_referral.py`, `crud_user.py`, `crud_token.py`.
    *   Implemented basic CRUD functions for Plan, UserPlan, ReferralData, User, Token.
    *   Updated route handlers in `core.py` and `billing.py` to use CRUD functions.
    *   Added `/admin/plans`, `/admin/users/{user_id}/plan` CRUD endpoints.
    *   Added `/admin/internal/log_referral` endpoint (with placeholder user auth).
    *   Added missing `/admin/users/{user_id}` (GET/DELETE) and `/admin/tokens/{token_value}` (DELETE) endpoints.
6.  **Client-Side Implementation (UTM):** **(PENDING - External)**
7.  **Database Migration Configuration:** **(DONE - Implicit via `init_db(drop_tables=True)`)**
    *   Using drop/create strategy for development via `init_db`.
    *   *Note: For production or persistent dev, proper Alembic migration generation required.*

### Validation Tests (End of Phase 1)

*   **Database Migration:** Schema created successfully via `init_db(drop_tables=True)` during container startup. Verified manually via API tests.
*   **Unit Tests (`admin-api`):** *(PENDING - No unit tests written yet)*
*   **Integration Tests (`admin-api`):** **(DONE - Basic Manual via `curl`)**
    *   Verified `/admin/plans` (GET) returns `[]`.
    *   Verified `/admin/users` (GET) works.
    *   Verified `/admin/users/{user_id}/tokens` (POST) works.
    *   *(Further `curl` tests for POST/PUT/DELETE on plans/userplans recommended).*
*   **Manual Check:** *(PENDING - Requires more API calls)* Create a plan, assign it to a user.

**Phase 2: Enforcement in `bot-manager` (Usage & Concurrency) (PENDING)**

1.  **Modify `bot-manager` (`POST /bots`):**
    *   Request body includes `model_identifier`.
    *   **Refactor Redis Usage:** Update code to use helper functions/constants from `shared_models.redis_keys` for generating `bot_commands:{connectionId}` channel names and the planned `active_bots:{user_id}` key.
    *   Call `admin-api` -> `GET /internal/check_limits` (to check usage against the specific model limit). *(Requires Phase 3)*
    *   Process response, handle usage failure (`usage_ok: false`).
    *   **Perform Overall Concurrency Check:** Use Redis Set (`active_bots:{user_id}`) to track total active bots for the user. Compare count against `concurrency_limit` received from `check_limits`.
    *   If checks pass, start bot & add bot identifier (e.g., `meeting.id` or `container_id`) to Redis Set `active_bots:{user_id}`.
2.  **Modify `bot-manager` (`DELETE /bots`, Background Task):**
    *   **Refactor Redis Usage:** Update Redis key generation using `shared_models.redis_keys`.
    *   Ensure the bot identifier is removed from the Redis Set `active_bots:{user_id}` upon successful termination.

### Validation Tests (End of Phase 2)

*   **Mocked Integration Test (`bot-manager`):**
    *   Mock the HTTP response from `admin-api`'s `/internal/check_limits` endpoint.
    *   Test `POST /bots`.
*   **Integration Test (`bot-manager`):**
    *   Requires `/internal/check_limits` in `admin-api` (from Phase 3) to be functional.
    *   Test concurrency limit enforcement via Redis Set.

**Phase 3: Limit Checking & Quote API in `admin-api` (PENDING)**

1.  **Modify `transcription-collector` (Usage Aggregation):**
    *   Inject SQLAlchemy session and `aioredis.Redis` client.
    *   **Refactor Redis Usage:** Use `shared_models.redis_keys`.
    *   **Modify `process_session_start_event`:** Parse `model_identifier`, create/update `MeetingSession`, initialize Redis Hash `session_agg:{session_uid}`. *(Requires Prerequisite)*
    *   **Modify `transcription` event processing:** Update Redis Hash (`max_end_time`, `total_duration`), add to `dirty_sessions` Set.
    *   **Implement Background Flush Task:** Periodically update `MeetingSession` in DB from Redis cache (`dirty_sessions`).
2.  **Implement Endpoints in `admin-api`:**
    *   **Internal Limit Check (`GET /internal/check_limits`):** Implement logic using `UserPlan`, `PlanModelLimit`, and **summing `MeetingSession.max_end_time`** within billing period.
    *   **User-Facing Quote API (`GET /usage/quote`):** Implement logic using `MeetingSession` filters and **summing `MeetingSession.max_end_time`**.

### Validation Tests (End of Phase 3)

*   Unit/Integration Tests (`transcription-collector`): Verify Redis updates and DB flush.
*   Unit/Integration Tests (`admin-api`): Verify limit/quote endpoint logic.
*   End-to-End Test: Verify limit enforcement and quote API results.

**Phase 4: Analytics & Logging (PENDING)**

*   Update logging in `admin-api`, `transcription-collector`.
*   Dashboards remain similar.

**Phase 5: Testing & Deployment (PENDING)**

*   Update tests for `admin-api` Phase 3 endpoints.
*   Update integration/E2E tests.
*   Deployment updates.