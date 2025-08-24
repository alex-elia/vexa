"""Nomad orchestrator implementation (Option A ― Pluggable Launcher).

This module provides minimal stubs that allow the bot-manager to run with
ORCHESTRATOR=nomad.  Only start_bot_container is implemented; the other
functions currently raise NotImplementedError and can be completed later.
"""
from __future__ import annotations

import os
import uuid
import logging
import json
from typing import Optional, Tuple, Dict, Any, List

import httpx

logger = logging.getLogger("bot_manager.nomad_utils")

# Nomad connection parameters - MODIFIED to use injected Nomad agent IP and fail if not present
NOMAD_AGENT_IP = os.getenv("NOMAD_IP_http")
if not NOMAD_AGENT_IP:
    raise RuntimeError(
        "NOMAD_IP_http environment variable not set. "
        "This is required for the bot-manager to connect to the Nomad API."
    )
NOMAD_ADDR = os.getenv("NOMAD_ADDR", f"http://{NOMAD_AGENT_IP}:4646").rstrip("/")

# Name of the *parameterised* job that represents a vexa-bot instance
BOT_JOB_NAME = os.getenv("VEXA_BOT_JOB_NAME", "vexa-bot")

# ---------------------------------------------------------------------------
# Helper / compatibility no-ops ------------------------------------------------

def get_socket_session(*_args, **_kwargs):  # type: ignore
    """Return None – kept for API compatibility (Docker-specific concept)."""
    return None

def close_client():  # type: ignore
    """No persistent Nomad client yet – nothing to close."""
    return None

close_docker_client = close_client  # compatibility alias

# ---------------------------------------------------------------------------
# Core public API -------------------------------------------------------------

async def start_bot_container(
    user_id: int,
    meeting_id: int,
    meeting_url: Optional[str],
    platform: str,
    bot_name: Optional[str],
    user_token: str,
    native_meeting_id: str,
    language: Optional[str],
    task: Optional[str]
) -> Optional[Tuple[str, str]]:
    """Dispatch a parameterised *vexa-bot* Nomad job.

    Returns (dispatched_job_id, connection_id) on success.
    """
    connection_id = str(uuid.uuid4())

    meta: Dict[str, str] = {
        "user_id": str(user_id),
        "meeting_id": str(meeting_id),
        "meeting_url": meeting_url or "",
        "platform": platform,
        "bot_name": bot_name or "",
        "user_token": user_token or "",
        "native_meeting_id": native_meeting_id,
        "connection_id": connection_id,
        "language": language or "",
        "task": task or "",
    }

    # Nomad job dispatch endpoint
    url = f"{NOMAD_ADDR}/v1/job/{BOT_JOB_NAME}/dispatch"

    # According to Nomad docs, metadata can be supplied in JSON body.
    payload = {
        "Meta": meta
    }

    logger.info(
        f"Dispatching Nomad job '{BOT_JOB_NAME}' for meeting {meeting_id} with meta {meta} -> {url}"
    )

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            dispatched_id = data.get("DispatchedJobID") or data.get("EvaluationID")
            if not dispatched_id:
                logger.warning(
                    "Nomad dispatch response missing DispatchedJobID; full response: %s", data
                )
                dispatched_id = f"unknown-{uuid.uuid4()}"
            logger.info(
                "Successfully dispatched Nomad job. Dispatch ID=%s, connection_id=%s",
                dispatched_id,
                connection_id,
            )
            return dispatched_id, connection_id
    except httpx.HTTPStatusError as e:
        error_details = "Unknown error"
        try:
            error_body = e.response.text
            if error_body:
                error_details = error_body
        except Exception:
            pass
        logger.error(
            "HTTP %s error dispatching Nomad job to %s: %s. Response body: %s",
            e.response.status_code, NOMAD_ADDR, e, error_details
        )
    except httpx.HTTPError as e:
        logger.error("HTTP error talking to Nomad at %s: %s", NOMAD_ADDR, e)
    except Exception as e:  # noqa: BLE001
        logger.exception("Unexpected error dispatching Nomad job: %s", e)

    return None, None


def stop_bot_container(container_id: str) -> bool:  # type: ignore
    """Stop (force-fail) a dispatched Nomad job by ID.

    For now this is a stub that logs the request and returns False to indicate
    the operation is not implemented.
    """
    logger.warning(
        "stop_bot_container called for %s but Nomad stop not yet implemented.",
        container_id,
    )
    return False


async def get_running_bots_status(user_id: int) -> List[Dict[str, Any]]:
    """Return a list of running bots for the given user by querying Nomad API.
    
    Queries Nomad for running jobs with the user_id label and returns
    formatted bot status information.
    """
    logger.info(f"Getting running bot status for user {user_id} from Nomad")
    
    try:
        # Query Nomad for running jobs with user_id label
        url = f"{NOMAD_ADDR}/v1/jobs"
        params = {
            "prefix": BOT_JOB_NAME,
            "filter": f"Meta.user_id == \"{user_id}\""
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            jobs_data = response.json()
            
        running_bots = []
        
        for job in jobs_data:
            job_id = job.get("ID", "")
            job_status = job.get("Status", "")
            
            # Only include running jobs
            if job_status != "running":
                continue
                
            # Get detailed job info including allocations
            job_detail_url = f"{NOMAD_ADDR}/v1/job/{job_id}"
            async with httpx.AsyncClient() as client:
                job_response = await client.get(job_detail_url, timeout=10)
                if job_response.status_code == 200:
                    job_detail = job_response.json()
                    
                    # Get running allocations
                    allocations = job_detail.get("Allocations", [])
                    running_allocations = [
                        alloc for alloc in allocations 
                        if alloc.get("ClientStatus") == "running"
                    ]
                    
                    if running_allocations:
                        # Get metadata from job
                        meta = job_detail.get("Meta", {})
                        
                        bot_info = {
                            "container_id": job_id,  # Use job ID as container ID
                            "connection_id": meta.get("connection_id", ""),
                            "meeting_id": meta.get("meeting_id", ""),
                            "platform": meta.get("platform", ""),
                            "native_meeting_id": meta.get("native_meeting_id", ""),
                            "bot_name": meta.get("bot_name", ""),
                            "status": "running",
                            "start_time": job_detail.get("SubmitTime", ""),
                            "user_id": user_id
                        }
                        running_bots.append(bot_info)
                        
                        logger.info(f"Found running bot: {bot_info}")
        
        logger.info(f"Found {len(running_bots)} running bots for user {user_id}")
        return running_bots
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error querying Nomad for user {user_id}: {e}")
        return []
    except httpx.HTTPError as e:
        logger.error(f"HTTP error talking to Nomad for user {user_id}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error getting bot status for user {user_id}: {e}", exc_info=True)
        return []


async def verify_container_running(container_id: str) -> bool:
    """Return True if the dispatched Nomad job is still running.
    
    Queries Nomad API to check if the job exists and has running allocations.
    """
    logger.debug(f"Verifying if Nomad job {container_id} is running")
    
    try:
        # Query Nomad for job details
        url = f"{NOMAD_ADDR}/v1/job/{container_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            if response.status_code != 200:
                logger.debug(f"Job {container_id} not found in Nomad (status: {response.status_code})")
                return False
                
            job_detail = response.json()
            job_status = job_detail.get("Status", "")
            
            if job_status != "running":
                logger.debug(f"Job {container_id} status is '{job_status}', not running")
                return False
            
            # Check if there are running allocations
            allocations = job_detail.get("Allocations", [])
            running_allocations = [
                alloc for alloc in allocations 
                if alloc.get("ClientStatus") == "running"
            ]
            
            is_running = len(running_allocations) > 0
            logger.debug(f"Job {container_id} has {len(running_allocations)} running allocations: {is_running}")
            
            return is_running
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error verifying job {container_id}: {e}")
        return False
    except httpx.HTTPError as e:
        logger.error(f"HTTP error talking to Nomad for job {container_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error verifying job {container_id}: {e}", exc_info=True)
        return False

# Alias for shared function – import lazily to avoid circulars
from app.docker_utils import _record_session_start  # noqa: E402 