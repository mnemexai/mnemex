// Graph Visualization using Cytoscape.js

const API_BASE = '/api';
let cy;
let allNodes = [];
let allEdges = [];

// Initialize graph when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initGraph();
    setupControls();
});

async function initGraph() {
    const container = document.getElementById('graph-viz');

    // Initialize Cytoscape
    cy = cytoscape({
        container: container,
        style: getStylesheet(),
        layout: { name: 'grid' }, // Initial layout before data load
        wheelSensitivity: 0.2,
    });

    // Event Listeners
    cy.on('tap', 'node', (evt) => {
        const node = evt.target;
        showNodeDetails(node.data());
    });

    cy.on('tap', (evt) => {
        if (evt.target === cy) {
            hideNodeDetails();
        }
    });

    // Fetch and render data
    try {
        const data = await fetchGraphData();
        renderGraph(data);
    } catch (error) {
        console.error('Failed to load graph data:', error);
        container.innerHTML = `<div class="error-state">Failed to load graph data: ${error.message}</div>`;
    }

    // Theme initialization
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateGraphTheme(savedTheme);

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateGraphTheme(newTheme);
        });
    }

    // Zoom Controls
    document.getElementById('zoom-in').addEventListener('click', () => {
        cy.zoom({
            level: cy.zoom() * 1.5,
            renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
        });
    });

    document.getElementById('zoom-out').addEventListener('click', () => {
        cy.zoom({
            level: cy.zoom() * 0.66,
            renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 }
        });
    });

    document.getElementById('zoom-fit').addEventListener('click', () => {
        cy.fit(undefined, 50);
    });
}

async function fetchGraphData(filter = {}) {
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

function renderGraph(data) {
    // Transform data for Cytoscape
    const elements = [
        ...data.nodes.map(n => ({
            group: 'nodes',
            data: { ...n, id: n.id, label: n.label, status: n.status, decay_score: n.decay_score }
        })),
        ...data.edges.map(e => ({
            group: 'edges',
            data: { ...e, id: `${e.source}-${e.target}`, source: e.source, target: e.target, strength: e.strength }
        }))
    ];

    cy.elements().remove();
    cy.add(elements);

    runLayout();
}

function runLayout() {
    const layout = cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 1000,
        refresh: 20,
        fit: true,
        padding: 50,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        nodeOverlap: 10,
        idealEdgeLength: 100,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: 1000,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0
    });

    layout.run();
}

function getStylesheet() {
    // Define colors based on CSS variables (we'll need to read them or hardcode defaults that match)
    // Since Cy styles are JS, we can't directly use var() in all properties easily without a helper,
    // but Cy supports standard CSS color names and hex.
    // For dynamic theming, we'll update the stylesheet when theme changes.

    return [
        {
            selector: 'node',
            style: {
                'label': 'data(label)',
                'width': 40,
                'height': 40,
                'background-color': '#666', // Default, overridden by status
                'color': '#fff',
                'text-valign': 'center',
                'text-halign': 'right',
                'text-margin-x': 10,
                'font-size': '12px',
                'font-family': 'Inter, sans-serif'
            }
        },
        {
            selector: 'node[status = "active"]',
            style: { 'background-color': '#007AFF' } // brand-primary
        },
        {
            selector: 'node[status = "archived"]',
            style: { 'background-color': '#8E8E93' } // text-secondary
        },
        {
            selector: 'node[status = "deleted"]',
            style: { 'background-color': '#FF3B30' } // accent-error
        },
        {
            selector: 'edge',
            style: {
                'width': 3,
                'line-color': '#8E8E93', // text-secondary
                'opacity': 0.8,
                'curve-style': 'bezier'
            }
        },
        {
            selector: ':selected',
            style: {
                'border-width': 2,
                'border-color': '#fff'
            }
        }
    ];
}

function updateGraphTheme(theme) {
    const isDark = theme === 'dark';
    const bgColor = isDark ? '#1c1c1e' : '#ffffff';
    const textColor = isDark ? '#ffffff' : '#000000';
    const edgeColor = isDark ? '#48484a' : '#d1d1d6'; // darker gray in dark mode, lighter in light

    // Update container background
    document.getElementById('graph-viz').style.backgroundColor = bgColor;

    // Update Cy styles
    cy.style()
        .selector('node')
        .style({
            'color': textColor
        })
        .selector('edge')
        .style({
            'line-color': edgeColor
        })
        .update();
}

function showNodeDetails(nodeData) {
    const panel = document.getElementById('node-details');
    panel.innerHTML = `
        <h3>${nodeData.label}</h3>
        <div class="meta">
            <p><strong>ID:</strong> ${nodeData.id}</p>
            <p><strong>Status:</strong> ${nodeData.status}</p>
            <p><strong>Decay Score:</strong> ${nodeData.decay_score ? nodeData.decay_score.toFixed(3) : 'N/A'}</p>
            <p><strong>Tags:</strong> ${nodeData.tags ? nodeData.tags.join(', ') : 'None'}</p>
        </div>
        <div class="actions" style="margin-top: 1rem;">
            <a href="/?memory_id=${nodeData.id}" class="btn-save">View Full Memory</a>
        </div>
    `;
    panel.classList.add('visible');
}

function hideNodeDetails() {
    const panel = document.getElementById('node-details');
    panel.classList.remove('visible');
}

function setupControls() {
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
                renderGraph(data);
            } catch (error) {
                console.error('Failed to filter graph:', error);
                alert('Failed to filter graph: ' + error.message);
            }
        });
    }

    // Force slider - update layout parameters
    const forceSlider = document.getElementById('force-strength');
    if (forceSlider) {
        forceSlider.addEventListener('change', (e) => {
            // Re-run layout with new spacing
            const val = parseInt(e.target.value);
            const layout = cy.layout({
                name: 'cose',
                animate: true,
                componentSpacing: val * 2 + 50,
                nodeRepulsion: val * 10000 + 100000,
                idealEdgeLength: val * 2 + 50
            });
            layout.run();
        });
    }
}
