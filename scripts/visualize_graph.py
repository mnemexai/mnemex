#!/usr/bin/env python3
"""
Visualize cortexgraph memory graph using PyVis.

This script reads memories and relations from JSONL files and creates
an interactive HTML visualization using PyVis and NetworkX.

Usage:
    visualize_graph.py [--memories PATH] [--relations PATH] [--output PATH]
    visualize_graph.py --help

Examples:
    # Use default paths
    visualize_graph.py

    # Custom paths
    visualize_graph.py --memories ~/data/memories.jsonl --output graph.html

    # Specify only output location
    visualize_graph.py --output ~/Desktop/cortexgraph_graph.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    import networkx as nx
    from pyvis.network import Network
except ImportError as e:
    print(f"Error: Missing required dependency: {e}", file=sys.stderr)
    print("\nPlease install required packages:", file=sys.stderr)
    print("  pip install pyvis networkx", file=sys.stderr)
    print("  or", file=sys.stderr)
    print("  uv pip install pyvis networkx", file=sys.stderr)
    sys.exit(1)


def load_jsonl(filepath: Path) -> list[dict[str, Any]]:
    """
    Load JSONL file and return list of parsed JSON objects.

    Args:
        filepath: Path to JSONL file

    Returns:
        List of dictionaries, one per line

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    records = []
    with open(filepath, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON at line {line_num}: {e}", file=sys.stderr)
                continue

    return records


def truncate_text(text: str, max_length: int = 50) -> str:
    """
    Truncate text to max_length, adding ellipsis if needed.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def create_graph(memories: list[dict[str, Any]], relations: list[dict[str, Any]]) -> nx.DiGraph:
    """
    Create NetworkX directed graph from memories and relations.

    Args:
        memories: List of memory dictionaries
        relations: List of relation dictionaries

    Returns:
        NetworkX DiGraph with memories as nodes and relations as edges
    """
    G = nx.DiGraph()

    # Add memory nodes
    for memory in memories:
        memory_id = memory.get("id")
        if not memory_id:
            continue

        content = memory.get("content", "")
        label = truncate_text(content, 50)

        # Extract metadata
        meta = memory.get("meta", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except json.JSONDecodeError:
                meta = {}

        tags = meta.get("tags", [])
        entities = memory.get("entities", [])

        # Add node with attributes
        G.add_node(
            memory_id,
            label=label,
            title=f"{content}\n\nTags: {', '.join(tags)}\nEntities: {', '.join(entities)}",
            content=content,
            tags=tags,
            entities=entities,
            created_at=memory.get("created_at"),
            use_count=memory.get("use_count", 0),
            strength=memory.get("strength", 1.0),
            status=memory.get("status", "active"),
        )

    # Add relation edges
    for relation in relations:
        from_id = relation.get("from_memory_id")
        to_id = relation.get("to_memory_id")

        if not from_id or not to_id:
            continue

        # Skip if nodes don't exist
        if from_id not in G or to_id not in G:
            continue

        relation_type = relation.get("relation_type", "related")
        strength = relation.get("strength", 1.0)
        metadata = relation.get("metadata", {})

        # Create edge label
        edge_label = relation_type
        if metadata and "description" in metadata:
            edge_label = f"{relation_type}\n{metadata['description']}"

        G.add_edge(
            from_id,
            to_id,
            label=edge_label,
            type=relation_type,
            strength=strength,
            title=f"Type: {relation_type}\nStrength: {strength}",
        )

    return G


def visualize_graph(G: nx.DiGraph, output_path: Path) -> None:
    """
    Create interactive PyVis visualization from NetworkX graph.

    Args:
        G: NetworkX directed graph
        output_path: Path to save HTML file
    """
    # Create PyVis network
    net = Network(
        height="900px", width="100%", bgcolor="#222222", font_color="white", directed=True
    )

    # Configure physics for better layout
    net.barnes_hut(
        gravity=-5000,
        central_gravity=0.3,
        spring_length=250,
        spring_strength=0.001,
        damping=0.09,
        overlap=0,
    )

    # Add nodes with custom styling
    for node, attrs in G.nodes(data=True):
        # Color based on status
        status = attrs.get("status", "active")
        color_map = {
            "active": "#4287f5",  # Blue
            "promoted": "#42f554",  # Green
            "archived": "#888888",  # Gray
        }
        color = color_map.get(status, "#4287f5")

        # Size based on use count (logarithmic scale)
        use_count = attrs.get("use_count", 0)
        size = 10 + (use_count**0.5) * 5  # Square root for better visual scaling

        net.add_node(
            node,
            label=attrs.get("label", node),
            title=attrs.get("title", ""),
            color=color,
            size=size,
        )

    # Add edges with custom styling
    for source, target, attrs in G.edges(data=True):
        relation_type = attrs.get("type", "related")
        strength = attrs.get("strength", 1.0)

        # Color based on relation type
        edge_color_map = {
            "related": "#888888",
            "causes": "#ff6b6b",
            "supports": "#51cf66",
            "contradicts": "#ff8c42",
            "has_decision": "#ffd93d",
            "consolidated_from": "#a78bfa",
        }
        edge_color = edge_color_map.get(relation_type, "#888888")

        # Width based on strength
        width = strength * 2

        net.add_edge(
            source, target, title=attrs.get("title", ""), color=edge_color, width=width, arrows="to"
        )

    # Generate HTML
    net.show_buttons(filter_=["physics"])
    net.write_html(str(output_path))
    print(f"✓ Visualization saved to: {output_path}")


def get_default_paths() -> tuple[Path, Path]:
    """
    Get default paths for memories and relations files.

    Returns:
        Tuple of (memories_path, relations_path)
    """
    # Try ~/.config/cortexgraph/jsonl/ first (new default)
    config_dir = Path.home() / ".config" / "cortexgraph" / "jsonl"
    if config_dir.exists():
        return (config_dir / "memories.jsonl", config_dir / "relations.jsonl")

    # Fallback to ~/.local/share/cortexgraph/
    share_dir = Path.home() / ".local" / "share" / "cortexgraph"
    return (share_dir / "memories.jsonl", share_dir / "relations.jsonl")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    memories_default, relations_default = get_default_paths()

    parser = argparse.ArgumentParser(
        description="Visualize cortexgraph memory graph using PyVis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s
  %(prog)s --output ~/Desktop/graph.html
  %(prog)s --memories ~/data/memories.jsonl --relations ~/data/relations.jsonl
        """,
    )

    parser.add_argument(
        "--memories",
        type=Path,
        default=memories_default,
        help=f"Path to memories.jsonl (default: {memories_default})",
    )

    parser.add_argument(
        "--relations",
        type=Path,
        default=relations_default,
        help=f"Path to relations.jsonl (default: {relations_default})",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("cortexgraph_graph.html"),
        help="Path to output HTML file (default: cortexgraph_graph.html)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    try:
        # Load data
        print(f"Loading memories from: {args.memories}")
        memories = load_jsonl(args.memories)
        print(f"✓ Loaded {len(memories)} memories")

        print(f"Loading relations from: {args.relations}")
        relations = load_jsonl(args.relations)
        print(f"✓ Loaded {len(relations)} relations")

        # Create graph
        print("Creating graph...")
        G = create_graph(memories, relations)
        print(f"✓ Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")

        # Visualize
        print("Generating visualization...")
        visualize_graph(G, args.output)

        return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
