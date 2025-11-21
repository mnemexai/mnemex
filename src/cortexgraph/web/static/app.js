const API_BASE = '/api';

// DOM Elements
let memoriesContainer;
let searchInput;
let toast;
let toastMessage;
let themeToggle;
let limitSelects;
let prevBtns;
let nextBtns;
let viewGridBtns;
let viewListBtns;
let modal;
let modalBody;
let closeModalBtn;

// State
let memories = [];
let isLoading = false;
let searchDebounce;
let currentPage = 1;
let itemsPerPage = 50;
let currentSearch = '';
let currentView = localStorage.getItem('viewMode') || 'grid';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM Elements
    memoriesContainer = document.getElementById('memories-container');
    searchInput = document.getElementById('search-input');
    toast = document.getElementById('toast');
    toastMessage = document.getElementById('toast-message');
    themeToggle = document.getElementById('theme-toggle');

    // Select all instances of controls
    limitSelects = document.querySelectorAll('.limit-select');
    prevBtns = document.querySelectorAll('.prev-btn');
    nextBtns = document.querySelectorAll('.next-btn');
    viewGridBtns = document.querySelectorAll('.view-grid-btn');
    viewListBtns = document.querySelectorAll('.view-list-btn');

    modal = document.getElementById('memory-modal');
    modalBody = document.getElementById('modal-body');
    closeModalBtn = document.querySelector('.btn-close');

    // Theme initialization
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);

    // Initialize View Mode
    updateViewMode(currentView);

    // Event Listeners
    themeToggle.addEventListener('click', toggleTheme);

    limitSelects.forEach(select => {
        select.addEventListener('change', (e) => {
            itemsPerPage = parseInt(e.target.value);
            // Sync other selects
            limitSelects.forEach(s => s.value = itemsPerPage);
            currentPage = 1;
            fetchMemories();
        });
    });

    prevBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                fetchMemories();
            }
        });
    });

    nextBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage++;
            fetchMemories();
        });
    });

    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(() => {
            currentSearch = e.target.value;
            currentPage = 1;
            fetchMemories();
        }, 300);
    });

    viewGridBtns.forEach(btn => {
        btn.addEventListener('click', () => updateViewMode('grid'));
    });

    viewListBtns.forEach(btn => {
        btn.addEventListener('click', () => updateViewMode('list'));
    });

    closeModalBtn.addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !modal.classList.contains('hidden')) {
            closeModal();
        }
    });

    // Check for deep link
    const urlParams = new URLSearchParams(window.location.search);
    const memoryId = urlParams.get('memory_id');
    if (memoryId) {
        // Remove param from URL without refresh
        window.history.replaceState({}, document.title, window.location.pathname);
        // Open memory details
        openMemory(memoryId);
    }

    // Initial fetch
    fetchMemories();
});

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

async function fetchMemories() {
    isLoading = true;
    renderLoading();

    try {
        const offset = (currentPage - 1) * itemsPerPage;
        const params = new URLSearchParams({
            limit: itemsPerPage,
            offset: offset
        });
        if (currentSearch) params.append('search', currentSearch);

        const response = await fetch(`${API_BASE}/memories?${params}`);
        if (!response.ok) throw new Error('Failed to fetch memories');

        const data = await response.json();
        memories = data.items;
        const total = data.total;

        renderMemories();
        updatePaginationControls(total);
    } catch (error) {
        console.error('Error:', error);
        showToast('Failed to load memories', 'error');
        memoriesContainer.innerHTML = `<div class="loading-state" style="color: var(--accent-error)">Error loading memories. Please try again.</div>`;
    } finally {
        isLoading = false;
    }
}

function updatePaginationControls(total) {
    const totalPages = Math.ceil(total / itemsPerPage);

    // Update all pagination navs
    const navs = document.querySelectorAll('.pagination-nav');

    navs.forEach(nav => {
        nav.innerHTML = '';

        // Previous Button
        const prevBtn = document.createElement('button');
        prevBtn.innerText = 'Previous';
        prevBtn.className = 'prev-btn'; // Add class for consistency
        prevBtn.disabled = currentPage === 1;
        prevBtn.onclick = () => {
            if (currentPage > 1) {
                currentPage--;
                fetchMemories();
            }
        };
        nav.appendChild(prevBtn);

        // First Page
        if (totalPages > 0) {
            addPageButton(nav, 1);
        }

        // Calculate window
        let startPage = Math.max(2, currentPage - 2);
        let endPage = Math.min(totalPages - 1, currentPage + 2);

        // Adjust window if close to edges
        if (currentPage <= 3) {
            endPage = Math.min(totalPages - 1, 5);
        }
        if (currentPage >= totalPages - 2) {
            startPage = Math.max(2, totalPages - 4);
        }

        // Ellipsis before window
        if (startPage > 2) {
            const span = document.createElement('span');
            span.innerText = '...';
            span.className = 'pagination-ellipsis';
            nav.appendChild(span);
        }

        // Window pages
        for (let i = startPage; i <= endPage; i++) {
            addPageButton(nav, i);
        }

        // Ellipsis after window
        if (endPage < totalPages - 1) {
            const span = document.createElement('span');
            span.innerText = '...';
            span.className = 'pagination-ellipsis';
            nav.appendChild(span);
        }

        // Last Page
        if (totalPages > 1) {
            addPageButton(nav, totalPages);
        }

        // Next Button
        const nextBtn = document.createElement('button');
        nextBtn.innerText = 'Next';
        nextBtn.className = 'next-btn'; // Add class for consistency
        nextBtn.disabled = currentPage === totalPages || totalPages === 0;
        nextBtn.onclick = () => {
            if (currentPage < totalPages) {
                currentPage++;
                fetchMemories();
            }
        };
        nav.appendChild(nextBtn);
    });
}

function addPageButton(container, page) {
    const btn = document.createElement('button');
    btn.innerText = page;
    if (page === currentPage) {
        btn.classList.add('active');
        btn.disabled = true;
    }
    btn.onclick = () => {
        currentPage = page;
        fetchMemories();
    };
    container.appendChild(btn);
}

function renderLoading() {
    memoriesContainer.innerHTML = '<div class="loading-state">Loading memories...</div>';
}

function updateViewMode(mode) {
    currentView = mode;
    localStorage.setItem('viewMode', mode);

    // Update all buttons
    if (mode === 'grid') {
        viewGridBtns.forEach(btn => btn.classList.add('active'));
        viewListBtns.forEach(btn => btn.classList.remove('active'));
        memoriesContainer.classList.remove('list-view');
    } else {
        viewListBtns.forEach(btn => btn.classList.add('active'));
        viewGridBtns.forEach(btn => btn.classList.remove('active'));
        memoriesContainer.classList.add('list-view');
    }

    // Re-render to apply structure changes if needed (or just CSS handles it)
    // For list view, we might want different content structure, so re-rendering is safer
    renderMemories();
}

async function openModal(memory) {
    const created = new Date(memory.created_at * 1000).toLocaleString();
    const lastUsed = new Date(memory.last_used * 1000).toLocaleString();
    const tagsHtml = memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('');

    // Format entities
    const entitiesHtml = (memory.entities && memory.entities.length > 0)
        ? memory.entities.map(e => `<span class="entity-tag">${e}</span>`).join('')
        : '<span class="text-muted">None</span>';

    // Format promotion info
    let promotionHtml = '';
    if (memory.status === 'promoted') {
        const promotedAt = memory.promoted_at ? new Date(memory.promoted_at * 1000).toLocaleString() : 'Unknown';
        promotionHtml = `
            <div class="meta-group promotion-info">
                <h4>Promotion Details</h4>
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="label">Promoted At:</span>
                        <span class="value">${promotedAt}</span>
                    </div>
                    <div class="meta-item full-width">
                        <span class="label">Vault Path:</span>
                        <span class="value code-font">${memory.promoted_to || 'Unknown'}</span>
                    </div>
                </div>
            </div>
        `;
    }

    // Initial render with loading state for relationships
    modalBody.innerHTML = `
        <div class="memory-card full-detail">
            <div class="memory-header">
                <div class="memory-meta">
                    <span class="memory-id">#${memory.id.substring(0, 8)}</span>
                    <span class="memory-date">${created}</span>
                </div>
                <div class="memory-status status-${memory.status}">${memory.status}</div>
            </div>

            <div class="memory-content">${marked.parse(memory.content)}</div>

            <div class="metadata-section">
                <div class="meta-grid">
                    <div class="meta-item">
                        <span class="label">Decay Score:</span>
                        <span class="value">${memory.strength ? memory.strength.toFixed(3) : 'N/A'}</span>
                    </div>
                    <div class="meta-item">
                        <span class="label">Use Count:</span>
                        <span class="value">${memory.use_count}</span>
                    </div>
                    <div class="meta-item">
                        <span class="label">Last Used:</span>
                        <span class="value">${lastUsed}</span>
                    </div>
                    <div class="meta-item">
                        <span class="label">Source:</span>
                        <span class="value">${memory.source || '<span class="text-muted">Not set</span>'}</span>
                    </div>
                </div>

                <div class="meta-group">
                    <span class="label">Entities:</span>
                    <div class="entities-list">${entitiesHtml}</div>
                </div>

                ${memory.context ? `
                <div class="meta-group">
                    <span class="label">Context:</span>
                    <div class="context-text">${memory.context}</div>
                </div>` : ''}

                ${promotionHtml}
            </div>

            <div class="memory-relationships-section">
                <h3>Relationships</h3>
                <div id="relationships-container" class="relationships-container">
                    <div class="loading-state small">Loading relationships...</div>
                </div>
            </div>

            <div class="memory-footer">
                <div class="memory-tags">${tagsHtml}</div>
                <div class="memory-actions">
                    <button onclick="saveToVault('${memory.id}', this)" class="btn-secondary">
                        Save to Vault
                    </button>
                </div>
            </div>
        </div>
    `;

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling

    // Fetch and render relationships
    try {
        const response = await fetch(`${API_BASE}/memories/${memory.id}/relationships`);
        if (!response.ok) throw new Error('Failed to fetch relationships');

        const data = await response.json();
        const relationships = data.relationships;
        const container = document.getElementById('relationships-container');

        if (relationships.length === 0) {
            container.innerHTML = '<div class="empty-state small">No relationships found.</div>';
            return;
        }

        container.innerHTML = relationships.map(rel => `
            <div class="relationship-item">
                <span class="relation-type">${rel.relation_type}</span>
                <span class="relation-target clickable" onclick="openMemory('${rel.target_memory_id}')" title="View Memory">
                    #${rel.target_memory_id.substring(0, 8)}
                </span>
                <span class="relation-strength" style="opacity: ${rel.strength}">
                    ${Math.round(rel.strength * 100)}%
                </span>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading relationships:', error);
        const container = document.getElementById('relationships-container');
        if (container) {
            container.innerHTML = '<div class="error-state small">Failed to load relationships.</div>';
        }
    }
}

// Global function for relationship navigation
window.openMemory = async function (id) {
    try {
        // Optional: Show loading indicator in the modal before content replacement
        const modalBody = document.getElementById('modal-body');
        if (modalBody) {
            modalBody.style.opacity = '0.5';
        }

        const response = await fetch(`${API_BASE}/memories/${id}`);
        if (!response.ok) throw new Error('Failed to fetch memory details');

        const memory = await response.json();

        if (modalBody) {
            modalBody.style.opacity = '1';
        }

        openModal(memory);

    } catch (error) {
        console.error('Error opening memory:', error);
        showToast('Failed to load memory details', 'error');
        const modalBody = document.getElementById('modal-body');
        if (modalBody) {
            modalBody.style.opacity = '1';
        }
    }
};

function closeModal() {
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}

function renderMemories() {
    memoriesContainer.innerHTML = '';

    if (memories.length === 0) {
        memoriesContainer.innerHTML = '<div class="empty-state">No memories found matching your criteria.</div>';
        return;
    }

    memories.forEach(memory => {
        const card = document.createElement('div');
        card.className = 'memory-card';

        // Add click event for list view expansion
        card.onclick = (e) => {
            // Don't trigger if clicking a button
            if (e.target.tagName === 'BUTTON') return;

            if (currentView === 'list') {
                openModal(memory);
            }
        };

        const date = new Date(memory.created_at * 1000).toLocaleString();
        const tagsHtml = memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('');

        // For list view, we render a simplified version
        // We strip HTML tags to ensure text-overflow: ellipsis works correctly
        let contentHtml = marked.parse(memory.content);
        if (currentView === 'list') {
            // Create a temporary element to strip HTML
            const temp = document.createElement('div');
            temp.innerHTML = contentHtml;
            contentHtml = temp.textContent || temp.innerText || '';
        }

        card.innerHTML = `
            <div class="memory-header">
                <div class="memory-meta">
                    <span class="memory-id">#${memory.id.substring(0, 8)}</span>
                    <span class="memory-date">${date}</span>
                </div>
                <div class="memory-status status-${memory.status}">${memory.status}</div>
            </div>
            <div class="memory-content">${contentHtml}</div>
            <div class="memory-footer">
                <div class="memory-tags">${tagsHtml}</div>
                <div class="memory-actions">
                    <button onclick="saveToVault('${memory.id}', this)" class="btn-secondary">
                        Save to Vault
                    </button>
                </div>
            </div>
        `;

        memoriesContainer.appendChild(card);
    });
}

// Make function available globally for onclick
window.saveToVault = async function (id, btn) {
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = 'Saving...';

    try {
        const response = await fetch(`${API_BASE}/memories/${id}/save-to-vault`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            let errorMessage = 'Failed to save';
            try {
                const error = await response.json();
                errorMessage = error.detail || errorMessage;
            } catch (e) {
                // Fallback to status text if JSON parsing fails
                errorMessage = `Error ${response.status}: ${response.statusText}`;
            }
            throw new Error(errorMessage);
        }

        await response.json();
        showToast('Memory saved to vault');
        btn.innerText = 'Saved';
        setTimeout(() => {
            btn.disabled = false;
            btn.innerText = originalText;
        }, 2000);

    } catch (error) {
        console.error('Error:', error);
        showToast(error.message, 'error');
        btn.innerText = 'Error';
        setTimeout(() => {
            btn.disabled = false;
            btn.innerText = originalText;
        }, 2000);
    }
};

function showToast(message, type = 'success') {
    toastMessage.innerText = message;
    toast.className = `toast ${type}`;

    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}
