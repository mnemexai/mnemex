"""Beads integration for consolidation agent coordination.

This module provides helper functions for creating and querying beads issues
used to coordinate consolidation agents. Uses subprocess calls to the `bd` CLI
with `--json` flag for structured output.

Design Decision (from research.md):
    Beads is designed as a CLI tool, not a Python library. Subprocess approach
    avoids importing beads internals and is consistent with how other tools
    (git, gh) are integrated.
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

# Label conventions for consolidation issues
AGENT_LABELS = {
    "decay": "consolidation:decay",
    "cluster": "consolidation:cluster",
    "merge": "consolidation:merge",
    "promote": "consolidation:promote",
    "relations": "consolidation:relations",
}

URGENCY_LABELS = {
    "high": "urgency:high",
    "medium": "urgency:medium",
    "low": "urgency:low",
}

# Priority mapping (beads uses 1-3, 1 = highest)
URGENCY_PRIORITY = {
    "high": 1,
    "medium": 2,
    "low": 3,
}


class BeadsError(Exception):
    """Raised when beads CLI command fails."""

    pass


def _run_bd_command(args: list[str], check: bool = True) -> dict[str, Any] | list[Any]:
    """Run a beads CLI command and return parsed JSON output.

    Args:
        args: Command arguments (without 'bd' prefix)
        check: If True, raise BeadsError on non-zero exit

    Returns:
        Parsed JSON output from beads

    Raises:
        BeadsError: If command fails and check=True
    """
    cmd = ["bd", *args, "--json"]
    logger.debug(f"Running beads command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,  # Handle errors ourselves
        )

        if result.returncode != 0 and check:
            error_msg = result.stderr.strip() or result.stdout.strip()
            raise BeadsError(f"Beads command failed: {error_msg}")

        if not result.stdout.strip():
            return {}

        parsed: dict[str, Any] | list[Any] = json.loads(result.stdout)
        return parsed

    except json.JSONDecodeError as e:
        raise BeadsError(f"Failed to parse beads output: {e}") from e
    except FileNotFoundError as e:
        raise BeadsError("beads CLI (bd) not found. Is it installed?") from e


def create_consolidation_issue(
    agent: str,
    memory_ids: list[str],
    action: str,
    urgency: str = "medium",
    extra_data: dict[str, Any] | None = None,
) -> str:
    """Create a beads issue for consolidation work.

    Args:
        agent: Agent type (decay/cluster/merge/promote/relations)
        memory_ids: Memory UUIDs involved
        action: Recommended action
        urgency: high/medium/low
        extra_data: Additional JSON data for notes

    Returns:
        Beads issue ID

    Contract:
        - MUST set title as human-readable description
        - MUST set notes as JSON with memory_ids and agent
        - MUST add labels: consolidation:{agent}, urgency:{urgency}
        - MUST NOT create duplicate issues for same memory_ids

    Raises:
        BeadsError: If issue creation fails
        ValueError: If agent or urgency is invalid
    """
    if agent not in AGENT_LABELS:
        raise ValueError(f"Invalid agent: {agent}. Must be one of {list(AGENT_LABELS.keys())}")

    if urgency not in URGENCY_LABELS:
        raise ValueError(
            f"Invalid urgency: {urgency}. Must be one of {list(URGENCY_LABELS.keys())}"
        )

    # Check for existing issue with same memory_ids to prevent duplicates
    existing = query_consolidation_issues(agent=agent, status="open")
    for issue in existing:
        notes = issue.get("notes", {})
        if isinstance(notes, str):
            try:
                notes = json.loads(notes)
            except json.JSONDecodeError:
                notes = {}
        existing_ids = set(notes.get("memory_ids", []))
        if existing_ids == set(memory_ids):
            logger.info(f"Issue already exists for memory_ids: {issue['id']}")
            return str(issue["id"])

    # Build human-readable title
    if len(memory_ids) == 1:
        title = f"{agent.title()}: Memory {memory_ids[0][:8]} - {action}"
    else:
        title = f"{agent.title()}: {len(memory_ids)} memories - {action}"

    # Build notes JSON
    notes_data: dict[str, Any] = {
        "memory_ids": memory_ids,
        "agent": agent,
        "action": action,
    }
    if extra_data:
        notes_data.update(extra_data)

    # Build labels
    labels = [AGENT_LABELS[agent], URGENCY_LABELS[urgency]]

    # Create issue via bd CLI
    args = [
        "create",
        title,
        "--type",
        "task",
        "--priority",
        str(URGENCY_PRIORITY[urgency]),
        "--notes",
        json.dumps(notes_data),
        "--labels",
        ",".join(labels),
    ]

    result = _run_bd_command(args)

    if isinstance(result, dict) and "id" in result:
        issue_id = str(result["id"])
        logger.info(f"Created consolidation issue: {issue_id}")
        return issue_id

    raise BeadsError(f"Unexpected response from beads: {result}")


def query_consolidation_issues(
    agent: str | None = None,
    status: str = "open",
    urgency: str | None = None,
) -> list[dict[str, Any]]:
    """Query beads issues for consolidation work.

    Args:
        agent: Filter by agent type (None = all consolidation issues)
        status: Filter by status (open/in_progress/blocked/closed)
        urgency: Filter by urgency (None = all)

    Returns:
        List of issue dicts with id, title, notes, labels, status

    Contract:
        - MUST return empty list if no matches (not error)
        - MUST parse notes JSON for structured data
        - MUST respect all filters (AND logic)
    """
    args = ["list", "--status", status]

    # Build label filter
    labels = []
    if agent:
        if agent not in AGENT_LABELS:
            raise ValueError(f"Invalid agent: {agent}")
        labels.append(AGENT_LABELS[agent])
    if urgency:
        if urgency not in URGENCY_LABELS:
            raise ValueError(f"Invalid urgency: {urgency}")
        labels.append(URGENCY_LABELS[urgency])

    if labels:
        args.extend(["--labels", ",".join(labels)])

    result = _run_bd_command(args, check=False)

    # Handle empty or error results
    if not result:
        return []

    # Result might be a list or dict with "result" key
    issues: list[Any]
    if isinstance(result, list):
        issues = result
    elif isinstance(result, dict):
        inner = result.get("result", result.get("issues", []))
        if isinstance(inner, list):
            issues = inner
        elif "id" in result:
            issues = [result]
        else:
            issues = []
    else:
        return []

    # Parse notes JSON for each issue
    for issue in issues:
        notes = issue.get("notes", "")
        if isinstance(notes, str) and notes:
            try:
                issue["notes"] = json.loads(notes)
            except json.JSONDecodeError:
                issue["notes"] = {"raw": notes}

    # Filter for consolidation issues if no agent specified
    if not agent:
        consolidation_labels = set(AGENT_LABELS.values())
        issues = [
            i for i in issues if any(label in consolidation_labels for label in i.get("labels", []))
        ]

    return issues


def claim_issue(issue_id: str) -> bool:
    """Claim an issue for processing.

    Args:
        issue_id: Beads issue ID

    Returns:
        True if successfully claimed, False if already claimed

    Contract:
        - MUST set status to in_progress
        - MUST fail gracefully if already in_progress
        - MUST NOT claim blocked issues
    """
    # First check current status
    try:
        result = _run_bd_command(["show", issue_id])
        if isinstance(result, dict):
            current_status = result.get("status", "")
            if current_status == "in_progress":
                logger.info(f"Issue {issue_id} already in_progress")
                return False
            if current_status == "blocked":
                logger.warning(f"Cannot claim blocked issue {issue_id}")
                return False
    except BeadsError:
        logger.warning(f"Could not check status for {issue_id}")

    # Update to in_progress
    try:
        _run_bd_command(["update", issue_id, "--status", "in_progress"])
        logger.info(f"Claimed issue: {issue_id}")
        return True
    except BeadsError as e:
        logger.error(f"Failed to claim issue {issue_id}: {e}")
        return False


def close_issue(issue_id: str, reason: str) -> None:
    """Close an issue after processing.

    Args:
        issue_id: Beads issue ID
        reason: Completion reason for audit trail

    Contract:
        - MUST set status to closed
        - MUST add reason to close message
    """
    try:
        _run_bd_command(["close", issue_id, "--reason", reason])
        logger.info(f"Closed issue {issue_id}: {reason}")
    except BeadsError as e:
        logger.error(f"Failed to close issue {issue_id}: {e}")
        raise


def block_issue(issue_id: str, error: str) -> None:
    """Block an issue due to error.

    Args:
        issue_id: Beads issue ID
        error: Error message for debugging

    Contract:
        - MUST set status to blocked
        - MUST add error to issue notes
    """
    try:
        _run_bd_command(["update", issue_id, "--status", "blocked", "--notes", error])
        logger.info(f"Blocked issue {issue_id}: {error}")
    except BeadsError as e:
        logger.error(f"Failed to block issue {issue_id}: {e}")
        raise
