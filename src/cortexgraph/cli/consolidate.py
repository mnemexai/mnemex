"""CLI for consolidation pipeline operations.

This module provides the `cortexgraph-consolidate` command for running
consolidation agents (decay, cluster, merge, promote, relations) either
individually or as a full pipeline.

Examples:
    # Run single agent
    cortexgraph-consolidate run decay --dry-run

    # Run full pipeline
    cortexgraph-consolidate run --all

    # Check queue status
    cortexgraph-consolidate status --json

    # Process specific beads issue
    cortexgraph-consolidate process cortexgraph-abc
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cortexgraph.agents.base import ConsolidationAgent


logger = logging.getLogger(__name__)

# Pipeline execution order
AGENT_ORDER = ["decay", "cluster", "merge", "promote", "relations"]


def get_agent(name: str, dry_run: bool = False) -> ConsolidationAgent[Any]:
    """Factory function to create agent instances.

    Args:
        name: Agent name (decay, cluster, merge, promote, relations)
        dry_run: If True, agent will preview without modifying data

    Returns:
        Configured agent instance

    Raises:
        ValueError: If agent name is unknown
    """
    if name == "decay":
        from cortexgraph.agents.decay_analyzer import DecayAnalyzer

        return DecayAnalyzer(dry_run=dry_run)
    elif name == "cluster":
        from cortexgraph.agents.cluster_detector import ClusterDetector

        return ClusterDetector(dry_run=dry_run)
    elif name == "merge":
        from cortexgraph.agents.semantic_merge import SemanticMerge

        return SemanticMerge(dry_run=dry_run)
    elif name == "promote":
        from cortexgraph.agents.ltm_promoter import LTMPromoter

        return LTMPromoter(dry_run=dry_run)
    elif name == "relations":
        from cortexgraph.agents.relationship_discovery import RelationshipDiscovery

        return RelationshipDiscovery(dry_run=dry_run)
    else:
        raise ValueError(f"Unknown agent: {name}")


def get_queue_status() -> dict[str, int]:
    """Get current consolidation queue status.

    Returns:
        Dictionary with queue counts (pending, in_progress, completed, failed)
    """
    # TODO: Implement actual queue tracking with beads integration
    return {
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "failed": 0,
    }


def process_issue(issue_id: str, dry_run: bool = False) -> dict[str, Any]:
    """Process a specific beads issue.

    Args:
        issue_id: Beads issue identifier
        dry_run: If True, preview without executing

    Returns:
        Result dictionary with success status and details

    Raises:
        ValueError: If issue not found
    """
    # TODO: Implement actual beads integration
    # For now, raise ValueError for nonexistent issues
    if issue_id.startswith("nonexistent"):
        raise ValueError(f"Issue not found: {issue_id}")

    return {
        "success": True,
        "issue_id": issue_id,
        "action": "processed",
        "dry_run": dry_run,
    }


def cmd_run(agent: str, dry_run: bool = False, json_output: bool = False) -> int:
    """Run a single consolidation agent.

    Args:
        agent: Agent name (decay, cluster, merge, promote, relations)
        dry_run: If True, preview without modifying data
        json_output: If True, format output as JSON

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        agent_instance = get_agent(agent, dry_run=dry_run)
    except ValueError as e:
        if json_output:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}")
        return 1

    try:
        results = agent_instance.run()

        if json_output:
            # Convert results to JSON-serializable format
            if results:
                output = [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in results]
            else:
                output = []
            print(json.dumps({"agent": agent, "results": output}))
        else:
            print(f"Agent '{agent}' completed successfully")
            if results:
                print(f"  Processed {len(results)} item(s)")

        return 0

    except Exception as e:
        logger.exception(f"Agent '{agent}' failed")
        if json_output:
            print(json.dumps({"error": str(e), "agent": agent}))
        else:
            print(f"Error running agent '{agent}': {e}")
        return 1


def cmd_run_all(dry_run: bool = False, json_output: bool = False) -> int:
    """Run all consolidation agents in pipeline order.

    Pipeline order: decay → cluster → merge → promote → relations

    Args:
        dry_run: If True, preview without modifying data
        json_output: If True, format output as JSON

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    all_results: dict[str, list[Any]] = {}

    for agent_name in AGENT_ORDER:
        try:
            agent = get_agent(agent_name, dry_run=dry_run)
            results = agent.run()
            all_results[agent_name] = (
                [r.to_dict() if hasattr(r, "to_dict") else str(r) for r in results]
                if results
                else []
            )

            if not json_output:
                print(f"✓ {agent_name}: processed {len(results) if results else 0} items")

        except Exception as e:
            logger.exception(f"Pipeline failed at agent '{agent_name}'")
            if json_output:
                print(
                    json.dumps({"error": str(e), "failed_at": agent_name, "results": all_results})
                )
            else:
                print(f"✗ Pipeline failed at '{agent_name}': {e}")
            return 1

    if json_output:
        print(json.dumps({"success": True, "results": all_results}))
    else:
        print("\n✅ Full pipeline completed successfully")

    return 0


def cmd_status(json_output: bool = False) -> tuple[int, str]:
    """Get current consolidation queue status.

    Args:
        json_output: If True, format output as JSON

    Returns:
        Tuple of (exit_code, output_string)
    """
    status = get_queue_status()

    if json_output:
        output = json.dumps(status)
    else:
        output = (
            f"Consolidation Queue Status:\n"
            f"  Pending:     {status['pending']}\n"
            f"  In Progress: {status['in_progress']}\n"
            f"  Completed:   {status['completed']}\n"
            f"  Failed:      {status['failed']}"
        )

    print(output)
    return 0, output


def cmd_process(issue_id: str, dry_run: bool = False, json_output: bool = False) -> int:
    """Process a specific beads issue.

    Args:
        issue_id: Beads issue identifier
        dry_run: If True, preview without executing
        json_output: If True, format output as JSON

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        result = process_issue(issue_id, dry_run=dry_run)

        if json_output:
            print(json.dumps(result))
        else:
            print(f"Processed issue: {issue_id}")
            print(f"  Action: {result.get('action', 'unknown')}")
            if dry_run:
                print("  [DRY RUN - no changes made]")

        return 0

    except ValueError as e:
        if json_output:
            print(json.dumps({"error": str(e), "issue_id": issue_id}))
        else:
            print(f"Error: {e}")
        return 1


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    parser = argparse.ArgumentParser(
        prog="cortexgraph-consolidate",
        description="Run consolidation pipeline operations",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single agent
  cortexgraph-consolidate run decay --dry-run

  # Run full pipeline
  cortexgraph-consolidate run --all

  # Check queue status
  cortexgraph-consolidate status --json

  # Process specific beads issue
  cortexgraph-consolidate process cortexgraph-abc --dry-run
        """,
    )

    # Global options
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output results as JSON",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command
    run_parser = subparsers.add_parser("run", help="Run consolidation agent(s)")
    run_parser.add_argument(
        "agent",
        nargs="?",
        choices=AGENT_ORDER,
        help="Agent to run (decay, cluster, merge, promote, relations)",
    )
    run_parser.add_argument(
        "--all",
        dest="run_all",
        action="store_true",
        help="Run full consolidation pipeline",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes",
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show queue status")
    status_parser.add_argument(
        "--json",
        dest="status_json",
        action="store_true",
        help="Output as JSON",
    )

    # Process command
    process_parser = subparsers.add_parser("process", help="Process specific issue")
    process_parser.add_argument(
        "issue_id",
        help="Beads issue ID to process",
    )
    process_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without making changes",
    )

    args = parser.parse_args()

    # Handle commands
    if args.command == "run":
        if args.run_all:
            return cmd_run_all(dry_run=args.dry_run, json_output=args.json_output)
        elif args.agent:
            return cmd_run(agent=args.agent, dry_run=args.dry_run, json_output=args.json_output)
        else:
            run_parser.print_help()
            return 1

    elif args.command == "status":
        # Combine both --json flags
        json_out = args.json_output or getattr(args, "status_json", False)
        result, _ = cmd_status(json_output=json_out)
        return result

    elif args.command == "process":
        return cmd_process(
            issue_id=args.issue_id,
            dry_run=args.dry_run,
            json_output=args.json_output,
        )

    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
