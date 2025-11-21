// Graph Visualization using D3.js v7

const API_BASE = '/api';
let simulation;
let svg;
let width;
let height;
let g; // Group for zoom
let nodes = [];
let links = [];

// Initialize graph when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initGraph();
    setupControls();
});

async function initGraph() {
    const container = document.getElementById('graph-viz');
    width = container.clientWidth;
    height = container.clientHeight;

    // Setup SVG
    svg = d3.select('#graph-viz')
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height])
        .style('max-width', '100%')
        .style('height', 'auto');

    // Add zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
            g.attr('transform', event.transform);
        });

    svg.call(zoom);

    // Group for all graph elements (to support zoom)
    g = svg.append('g');

    // Fetch data
    try {
        const data = await fetchGraphData();
        nodes = data.nodes;
        links = data.edges.map(d => ({ ...d })); // Copy to avoid mutation issues if re-fetching

        renderGraph();
    } catch (error) {
        console.error('Failed to load graph data:', error);
        container.innerHTML = `<div class="error-state">Failed to load graph data: ${error.message}</div>`;
    }
}

async function fetchGraphData(filter = {}) {
    // If filter is empty, use GET /api/graph
    // If filter has properties, use POST /api/graph/filtered

    let url = `${API_BASE}/graph`;
    let options = {};

    if (Object.keys(filter).length > 0) {
        url = `${API_BASE}/graph/filtered`;
        options = {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filter)
        };
    }

    const response = await fetch(url, options);
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    return await response.json();
}

function renderGraph() {
    // Clear existing
    g.selectAll('*').remove();

    // Simulation setup
    simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collide', d3.forceCollide().radius(30));

    // Draw links
    const link = g.append('g')
        .attr('stroke', '#999')
        .attr('stroke-opacity', 0.6)
        .selectAll('line')
        .data(links)
        .join('line')
        .attr('stroke-width', d => Math.sqrt(d.strength * 5)); // Strength determines thickness

    // Draw nodes
    const node = g.append('g')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1.5)
        .selectAll('circle')
        .data(nodes)
        .join('circle')
        .attr('r', 10) // Fixed radius for now, could use use_count
        .attr('fill', d => getNodeColor(d.status))
        .attr('opacity', d => d.decay_score || 1)
        .call(drag(simulation));

    // Add labels (optional, maybe on hover or zoom level)
    const label = g.append('g')
        .attr('class', 'labels')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .attr('dx', 12)
        .attr('dy', '.35em')
        .text(d => d.label)
        .style('font-size', '10px')
        .style('pointer-events', 'none')
        .style('fill', 'var(--text-secondary)');

    // Tooltip/Interaction
    node.on('click', (event, d) => {
        showNodeDetails(d);
        event.stopPropagation(); // Prevent background click
    });

    svg.on('click', () => {
        hideNodeDetails();
    });

    // Simulation tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        label
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });
}

function getNodeColor(status) {
    switch (status) {
        case 'active': return 'var(--brand-primary)';
        case 'archived': return 'var(--text-secondary)';
        case 'deleted': return 'var(--accent-error)';
        default: return '#ccc';
    }
}

function drag(simulation) {
    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }

    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }

    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }

    return d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended);
}

function showNodeDetails(node) {
    const panel = document.getElementById('node-details');
    panel.innerHTML = `
        <h3>${node.label}</h3>
        <div class="meta">
            <p><strong>ID:</strong> ${node.id}</p>
            <p><strong>Status:</strong> ${node.status}</p>
            <p><strong>Tags:</strong> ${node.tags.join(', ') || 'None'}</p>
        </div>
        <div class="actions" style="margin-top: 1rem;">
            <a href="/?memory_id=${node.id}" class="btn-save">View Full Memory</a>
        </div>
    `;
    panel.classList.add('visible');
}

function hideNodeDetails() {
    const panel = document.getElementById('node-details');
    panel.classList.remove('visible');
}

function setupControls() {
    const forceSlider = document.getElementById('force-strength');
    if (forceSlider) {
        forceSlider.addEventListener('input', (e) => {
            if (simulation) {
                simulation.force('charge').strength(-e.target.value * 10);
                simulation.alpha(1).restart();
            }
        });
    }

    const applyBtn = document.getElementById('apply-filters');
    if (applyBtn) {
        applyBtn.addEventListener('click', async () => {
            const searchInput = document.getElementById('search-input');
            const statusCheckboxes = document.querySelectorAll('.status-filter:checked');

            const filter = {};

            if (searchInput && searchInput.value.trim()) {
                filter.search_query = searchInput.value.trim();
            }

            if (statusCheckboxes.length > 0) {
                filter.statuses = Array.from(statusCheckboxes).map(cb => cb.value);
            }

            try {
                const data = await fetchGraphData(filter);
                nodes = data.nodes;
                links = data.edges.map(d => ({ ...d }));
                renderGraph();
            } catch (error) {
                console.error('Failed to filter graph:', error);
                alert('Failed to filter graph: ' + error.message);
            }
        });
    }
}
