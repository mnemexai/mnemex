# Memory MCP Visualization Guide

**Author**: Scot Campbell
**Date**: November 4, 2025
**Tool**: dzivkovi/mcp-memory-visualizer
**Installation Location**: /Users/sc/GitHub/memory-visualizer

## Executive Summary

After comparing two memory visualization tools for Anthropic's memory.json format, I chose **dzivkovi/mcp-memory-visualizer** because it offers three complementary visualization modes:

1. Web-based visualizer (zero installation, 100% private)
2. Python static analysis (statistical + high-res graphs)
3. Python interactive (browser-based with Python processing)

The tool is installed and tested successfully.

## Why This Tool?

### Comparison: mjherich vs dzivkovi

| Feature | mjherich/memory-visualizer | dzivkovi/mcp-memory-visualizer |
|---------|---------------------------|-------------------------------|
| **Installation** | npm + dependencies | None (web) OR pip (Python) |
| **Tech Stack** | React + TypeScript + D3.js + Vite | D3.js (web) + NetworkX/PyVis (Python) |
| **Stars** | 12 | 0 |
| **Maintenance** | Active (13 commits, last Aug 2025) | Recent (4 commits, last Jun 2025) |
| **Modes** | 1 (web app) | 3 (web + 2 Python) |
| **Live Demo** | memviz.herich.tech | dzivkovi.github.io/mcp-memory-visualizer |
| **Features** | Interactive graph, search, filters | Three modes: quick, statistical, deep |
| **Best For** | Interactive exploration | Multiple use cases (exploration, analysis, research) |

### Decision: dzivkovi

**Chosen: dzivkovi/mcp-memory-visualizer**

**Reasons:**
1. **Three modes for different workflows**: Web (quick), Python static (research), Python interactive (deep analysis)
2. **Easier installation**: Web version = zero install, Python version = `pip install -r requirements.txt`
3. **Statistical analysis**: NetworkX provides graph metrics (centrality, clusters, redundancy detection)
4. **Export options**: PNG (static), HTML (interactive), screenshots (web)
5. **Simpler codebase**: Single HTML file (web) + 2 Python scripts vs full React build system

mjherich's tool is more polished (React + TypeScript, better UI), but dzivkovi's three-mode approach better serves different use cases.

## Installation

### Method 1: Web Visualizer (Recommended)

**Zero installation required!**

Visit: https://dzivkovi.github.io/mcp-memory-visualizer/

Features:
- Drag & drop memory.json file
- 100% private (all processing in browser)
- Interactive graph with physics simulation
- Search entities and observations
- Color-coded entity types
- Detail panel with relationships

### Method 2: Python Tools (For Analysis)

Already installed at: `/Users/sc/GitHub/memory-visualizer`

```bash
# If you need to reinstall:
cd ~/GitHub
git clone https://github.com/dzivkovi/mcp-memory-visualizer.git memory-visualizer
cd memory-visualizer
pip install -r requirements.txt
```

Dependencies installed:
- networkx (graph analysis)
- matplotlib (static visualization)
- pyvis (interactive HTML output)

## Usage

### Option 1: Web Visualizer (Quick Exploration)

1. Navigate to: https://dzivkovi.github.io/mcp-memory-visualizer/
2. Locate your memory.json file (see "Finding Your Memory File" below)
3. Drag & drop the file into the browser
4. Explore:
   - Drag nodes to rearrange
   - Zoom with mouse wheel
   - Click nodes to see observations
   - Search for entities
   - View relationships in detail panel

**Best for**: Quick visualization, on-the-fly debugging, sharing with others

### Option 2: Python Static Analysis (Research & Reports)

```bash
cd /Users/sc/GitHub/memory-visualizer

# Run static analysis (generates PNG + terminal output)
python visualize_memory.py

# Output:
# - memory_graph.png (300 DPI high-res graph)
# - Terminal: statistics, centrality, redundancy detection
```

**Provides:**
- Network statistics (nodes, edges, connected components)
- Centrality analysis (most connected entities)
- Redundancy detection (similar entities, sparse nodes)
- High-resolution graph (300 DPI)

**Best for**: Research papers, reports, quantitative analysis, finding optimization opportunities

### Option 3: Python Interactive (Deep Analysis)

```bash
cd /Users/sc/GitHub/memory-visualizer

# Run interactive analysis (generates HTML)
python visualize_memory_interactive.py

# Output:
# - memory_graph_interactive.html (opens in browser)
```

**Provides:**
- Browser-based interactive visualization
- Hover tooltips with full entity details
- Physics-based node positioning
- Zoom, pan, node dragging
- HTML export for sharing

**Best for**: Deep analysis, presentations, sharing with collaborators

## Finding Your Memory File

### Default Location (Problematic)

Anthropic's Memory MCP server stores memory.json by default in:

```
# macOS
~/.cache/npm/_npx/[hash]/node_modules/@modelcontextprotocol/server-memory/dist/memory.json

# Windows
C:\Users\[username]\AppData\Local\npm-cache\_npx\[hash]\node_modules\@modelcontextprotocol\server-memory\dist\memory.json
```

**Warning**: This location is temporary and gets wiped during npm cache clears or package updates!

### Recommended: Configure Persistent Location

Edit Claude Desktop config to use a persistent location:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": {
        "MEMORY_FILE_PATH": "/Users/sc/Documents/claude-memory/memory.json"
      }
    }
  }
}
```

**Recommended locations (macOS):**
- `~/Documents/claude-memory/memory.json`
- `~/Library/Application Support/claude-memory/memory.json`
- `~/Dropbox/claude-memory/memory.json` (if you want cloud backup)

**Note**: Create the directory first!

```bash
mkdir -p ~/Documents/claude-memory
```

## Memory File Format

Anthropic's memory.json uses JSONL format (one JSON object per line):

```json
{"type":"entity","name":"Python","entityType":"technology","observations":["Used for data analysis","Popular ML language"]}
{"type":"relation","from":"Python","to":"Data Science","relationType":"used_in"}
```

**Entity types**: person, technology, project, event, organization, product, concept, research, feature, etc.

**Relation types**: leads, organizes, collaborates_with, uses, powers, built_on, implements, analyzed_in, supports, etc.

## Demo Data

The repo includes demo data at `/Users/sc/GitHub/memory-visualizer/memory.json`:

- 16 entities across 9 types
- 25 relationships
- Complex connections (AI research, enterprise systems, academic collaboration)
- Varied node sizes (1-10 observations)

Use this to test the tools before using your own data.

## Technical Details

### Web Visualizer
- **D3.js** for force-directed graph layout
- **Client-side processing** (privacy-first)
- **Responsive design** (works on mobile)
- **No backend required**

### Python Static Analysis
- **NetworkX** for graph analysis
- **Matplotlib** for high-res visualization (300 DPI)
- **Metrics**: degree centrality, betweenness, clustering
- **Output**: PNG + terminal statistics

### Python Interactive
- **PyVis** for interactive HTML output
- **NetworkX** for graph processing
- **Physics simulation** for natural layout
- **HTML export** for sharing

## Workflow Examples

### Workflow 1: Quick Check (Web)
1. Open https://dzivkovi.github.io/mcp-memory-visualizer/
2. Drop your memory.json
3. Visually scan for:
   - Disconnected entities (isolated nodes)
   - Overly connected entities (hubs)
   - Clusters (related concepts)

### Workflow 2: Research Analysis (Python Static)
1. `cd /Users/sc/GitHub/memory-visualizer`
2. `python visualize_memory.py > analysis.txt`
3. Review terminal output for:
   - Network statistics
   - Centrality rankings
   - Redundancy candidates
4. Include `memory_graph.png` in your paper/report

### Workflow 3: Deep Dive (Python Interactive)
1. `cd /Users/sc/GitHub/memory-visualizer`
2. `python visualize_memory_interactive.py`
3. Open generated HTML in browser
4. Explore with hover tooltips
5. Share HTML file with collaborators

### Workflow 4: Memory Cleanup
1. Run static analysis: `python visualize_memory.py`
2. Identify:
   - **Sparse nodes**: Entities with <2 observations (candidates for deletion)
   - **Redundant entities**: Similar names (e.g., "AI Project" vs "AI_Project")
   - **Disconnected nodes**: Entities with no relations (orphans)
3. Manually edit memory.json or use Claude Desktop to refine memories

## Comparison to mjherich's Tool

If you want to try the React-based alternative:

```bash
cd ~/GitHub
git clone https://github.com/mjherich/memory-visualizer.git mjherich-visualizer
cd mjherich-visualizer
npm install
npm run dev
```

**Live demo**: https://memviz.herich.tech

**Pros:**
- More polished UI (React + TypeScript + TailwindCSS)
- Better keyboard shortcuts (documented in CLAUDE.md)
- Theme system (light/dark modes)
- More active maintenance (12 stars, recent commits)

**Cons:**
- Requires Node.js build setup (more complex)
- Only one mode (interactive web)
- No statistical analysis features
- No export to PNG/HTML

**When to use mjherich instead:**
- You prefer modern React UI
- You want theme support
- You don't need statistical analysis
- You're already familiar with npm/Vite workflows

## Troubleshooting

### Issue: "File not found" when running Python scripts

**Solution**: Ensure you're in the correct directory:

```bash
cd /Users/sc/GitHub/memory-visualizer
ls  # Should show: visualize_memory.py, memory.json, etc.
```

### Issue: Matplotlib "building font cache"

**Solution**: This is normal on first run. Wait 30-60 seconds. Subsequent runs will be faster.

### Issue: "ModuleNotFoundError"

**Solution**: Reinstall dependencies:

```bash
cd /Users/sc/GitHub/memory-visualizer
pip install -r requirements.txt
```

### Issue: Web visualizer not loading memory.json

**Solution**: Check file format. Must be JSONL (one JSON object per line), not pretty-printed JSON array.

**Wrong:**
```json
[
  {"type": "entity", ...},
  {"type": "relation", ...}
]
```

**Correct:**
```json
{"type":"entity",...}
{"type":"relation",...}
```

### Issue: Memory file in temporary npm cache location

**Solution**: Configure persistent location (see "Finding Your Memory File" section above).

## Future Enhancements

Potential extensions (mentioned in repo):
- Export formats (GraphML, GEXF, JSON)
- Filtering options (entity types, date ranges)
- Advanced metrics (betweenness centrality, clustering coefficients)
- Memory editing capabilities (add/remove entities, relations)

## Related Tools

- **Anthropic Memory MCP Server**: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- **mjherich's visualizer**: https://github.com/mjherich/memory-visualizer
- **cortexgraph** (your temporal memory system): https://github.com/cortexgraphai/cortexgraph

## Credits

**Tool**: dzivkovi/mcp-memory-visualizer
**GitHub**: https://github.com/dzivkovi/mcp-memory-visualizer
**Live Demo**: https://dzivkovi.github.io/mcp-memory-visualizer/
**Philosophy**: "Perfection is achieved, not when there is nothing more to add, but when there is nothing left to take away." - Antoine de Saint-Exupéry

---

**Installation verified**: November 4, 2025
**Tool version**: Latest commit 7a0bb1e (Jun 20, 2025)
**Python dependencies**: networkx, matplotlib, pyvis (installed)
**Status**: Ready to use
