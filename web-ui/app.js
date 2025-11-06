// Configuration
let config = {
    apiUrl: localStorage.getItem('apiUrl') || 'http://localhost:8080',
    apiKey: localStorage.getItem('apiKey') || '',
    pageSize: parseInt(localStorage.getItem('pageSize')) || 20,
    theme: localStorage.getItem('theme') || 'light'
};

// State
let state = {
    memories: [],
    stats: null,
    currentPage: 1,
    totalPages: 1,
    currentView: 'memories',
    searchQuery: '',
    filters: {
        project: '',
        tag: '',
        sort: 'recent'
    },
    bulkMode: false,
    selectedMemories: new Set(),
    editingMemory: null
};

// API Helper
async function apiCall(endpoint, options = {}) {
    const url = `${config.apiUrl}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
        ...(config.apiKey && { 'X-API-Key': config.apiKey })
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers: { ...headers, ...options.headers }
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification(error.message, 'error');
        throw error;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeTheme();
    initializeEventListeners();
    loadMemories();
    loadStats();
});

function initializeTheme() {
    document.documentElement.setAttribute('data-theme', config.theme);
    updateThemeButton();
}

function updateThemeButton() {
    const btn = document.getElementById('themeToggle');
    const isDark = config.theme === 'dark';
    const icon = btn.querySelector('.theme-icon');
    icon.textContent = isDark ? '☀' : '🌙';
    btn.querySelector('.label').textContent = isDark ? 'Light Mode' : 'Dark Mode';
}

function initializeEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            switchView(item.dataset.view);
        });
    });

    // Theme toggle
    document.getElementById('themeToggle').addEventListener('click', toggleTheme);

    // Search
    document.getElementById('searchBtn').addEventListener('click', handleSearch);
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Add memory
    document.getElementById('addMemoryBtn').addEventListener('click', () => openMemoryModal());

    // Filters
    document.getElementById('projectFilter').addEventListener('change', handleFilterChange);
    document.getElementById('tagFilter').addEventListener('change', handleFilterChange);
    document.getElementById('sortFilter').addEventListener('change', handleFilterChange);

    // Bulk actions
    document.getElementById('bulkSelectBtn').addEventListener('click', toggleBulkMode);
    document.getElementById('cancelBulkBtn').addEventListener('click', () => toggleBulkMode(false));
    document.getElementById('bulkTagBtn').addEventListener('click', handleBulkTag);
    document.getElementById('bulkDeleteBtn').addEventListener('click', handleBulkDelete);

    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => changePage(-1));
    document.getElementById('nextPage').addEventListener('click', () => changePage(1));

    // Modal
    document.getElementById('saveMemory').addEventListener('click', handleSaveMemory);
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', closeModal);
    });
    document.getElementById('memoryText').addEventListener('input', updatePreview);

    // Settings
    document.getElementById('saveSettings').addEventListener('click', saveSettings);
    document.getElementById('apiUrl').value = config.apiUrl;
    document.getElementById('apiKey').value = config.apiKey;
    document.getElementById('pageSize').value = config.pageSize;
}

// View Management
function switchView(view) {
    state.currentView = view;
    
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === view);
    });

    // Update views
    document.querySelectorAll('.view').forEach(v => {
        v.classList.toggle('active', v.id === `${view}View`);
    });

    // Load data for view
    if (view === 'stats') loadStats();
}

function toggleTheme() {
    config.theme = config.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('theme', config.theme);
    document.documentElement.setAttribute('data-theme', config.theme);
    updateThemeButton();
}

// Memory Management
async function loadMemories() {
    const list = document.getElementById('memoriesList');
    list.innerHTML = '<div class="loading">Loading memories...</div>';

    try {
        const params = new URLSearchParams({
            limit: config.pageSize,
            offset: (state.currentPage - 1) * config.pageSize,
            ...(state.filters.project && { project: state.filters.project }),
            ...(state.filters.tag && { tag: state.filters.tag }),
            ...(state.searchQuery && { q: state.searchQuery })
        });

        const data = state.searchQuery 
            ? await apiCall(`/memory/search?${params}`)
            : await apiCall(`/memory/list?${params}`);

        state.memories = data.results || data.memories || [];
        state.totalPages = Math.ceil((data.total || 0) / config.pageSize);

        renderMemories();
        updatePagination();
        updateFilters();
    } catch (error) {
        list.innerHTML = `<div class="empty-state"><h3>Failed to load memories</h3><p>${error.message}</p></div>`;
    }
}

function renderMemories() {
    const list = document.getElementById('memoriesList');

    if (state.memories.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <h3>No memories found</h3>
                <p>Start by adding your first memory!</p>
            </div>
        `;
        return;
    }

    list.innerHTML = state.memories.map(memory => `
        <div class="memory-card ${state.selectedMemories.has(memory.id) ? 'selected' : ''}" data-id="${memory.id}">
            ${state.bulkMode ? `<input type="checkbox" class="bulk-checkbox" ${state.selectedMemories.has(memory.id) ? 'checked' : ''}>` : ''}
            ${memory.score ? `<span class="memory-score">${(memory.score * 100).toFixed(0)}%</span>` : ''}
            <div class="memory-header">
                <div class="memory-meta">
                    ${memory.project ? `<span class="memory-project">${memory.project}</span>` : ''}
                    <div class="memory-date">${formatDate(memory.created_at)}</div>
                </div>
                <div class="memory-actions">
                    <button class="btn btn-sm btn-secondary" onclick="editMemory('${memory.id}')">Edit</button>
                    <button class="btn btn-sm btn-danger" onclick="deleteMemory('${memory.id}')">Delete</button>
                </div>
            </div>
            <div class="memory-text">${escapeHtml(memory.text)}</div>
            ${memory.tags && memory.tags.length > 0 ? `
                <div class="memory-tags">
                    ${memory.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('');

    // Add bulk checkbox listeners
    if (state.bulkMode) {
        document.querySelectorAll('.bulk-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const id = e.target.closest('.memory-card').dataset.id;
                if (e.target.checked) {
                    state.selectedMemories.add(id);
                } else {
                    state.selectedMemories.delete(id);
                }
                updateBulkActions();
            });
        });
    }
}

async function handleSearch() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        state.searchQuery = '';
        loadMemories();
        return;
    }

    state.searchQuery = query;
    state.currentPage = 1;
    loadMemories();
}

function handleFilterChange() {
    state.filters.project = document.getElementById('projectFilter').value;
    state.filters.tag = document.getElementById('tagFilter').value;
    state.filters.sort = document.getElementById('sortFilter').value;
    state.currentPage = 1;
    loadMemories();
}

async function updateFilters() {
    // Extract unique projects and tags
    const projects = new Set();
    const tags = new Set();

    state.memories.forEach(m => {
        if (m.project) projects.add(m.project);
        if (m.tags) m.tags.forEach(t => tags.add(t));
    });

    // Update project filter
    const projectFilter = document.getElementById('projectFilter');
    projectFilter.innerHTML = '<option value="">All Projects</option>' +
        Array.from(projects).sort().map(p => `<option value="${p}">${p}</option>`).join('');

    // Update tag filter
    const tagFilter = document.getElementById('tagFilter');
    tagFilter.innerHTML = '<option value="">All Tags</option>' +
        Array.from(tags).sort().map(t => `<option value="${t}">${t}</option>`).join('');
}

function toggleBulkMode(enable = !state.bulkMode) {
    state.bulkMode = enable;
    state.selectedMemories.clear();
    document.getElementById('bulkActions').classList.toggle('hidden', !enable);
    renderMemories();
    updateBulkActions();
}

function updateBulkActions() {
    document.getElementById('selectedCount').textContent = `${state.selectedMemories.size} selected`;
}

async function handleBulkTag() {
    const tags = prompt('Enter tags to add (comma-separated):');
    if (!tags) return;

    const tagArray = tags.split(',').map(t => t.trim());
    
    for (const id of state.selectedMemories) {
        // This would need backend support for updating tags
        showNotification('Bulk tagging not yet implemented', 'warning');
    }
}

async function handleBulkDelete() {
    if (!confirm(`Delete ${state.selectedMemories.size} memories?`)) return;

    try {
        for (const id of state.selectedMemories) {
            await apiCall(`/memory/${id}`, { method: 'DELETE' });
        }
        showNotification(`Deleted ${state.selectedMemories.size} memories`, 'success');
        toggleBulkMode(false);
        loadMemories();
    } catch (error) {
        // Error already shown by apiCall
    }
}

async function deleteMemory(id) {
    if (!confirm('Delete this memory?')) return;

    try {
        await apiCall(`/memory/${id}`, { method: 'DELETE' });
        showNotification('Memory deleted', 'success');
        loadMemories();
    } catch (error) {
        // Error already shown
    }
}

function editMemory(id) {
    const memory = state.memories.find(m => m.id === id);
    if (!memory) return;

    state.editingMemory = memory;
    document.getElementById('modalTitle').textContent = 'Edit Memory';
    document.getElementById('memoryText').value = memory.text;
    document.getElementById('memoryProject').value = memory.project || '';
    document.getElementById('memoryTags').value = memory.tags ? memory.tags.join(', ') : '';
    document.getElementById('autoTag').checked = false;
    updatePreview();
    openMemoryModal();
}

// Modal Management
function openMemoryModal() {
    document.getElementById('memoryModal').classList.add('active');
}

function closeModal() {
    document.getElementById('memoryModal').classList.remove('active');
    document.getElementById('memoryText').value = '';
    document.getElementById('memoryProject').value = '';
    document.getElementById('memoryTags').value = '';
    document.getElementById('autoTag').checked = true;
    document.getElementById('modalTitle').textContent = 'Add Memory';
    state.editingMemory = null;
}

function updatePreview() {
    const text = document.getElementById('memoryText').value;
    document.getElementById('memoryPreview').textContent = text || 'Preview will appear here...';
}

async function handleSaveMemory() {
    const text = document.getElementById('memoryText').value.trim();
    if (!text) {
        showNotification('Please enter memory text', 'error');
        return;
    }

    const project = document.getElementById('memoryProject').value.trim();
    const tagsInput = document.getElementById('memoryTags').value.trim();
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()) : [];
    const autoTag = document.getElementById('autoTag').checked && !tagsInput;

    const payload = {
        text,
        ...(project && { project }),
        ...(!autoTag && tags.length > 0 && { tags })
    };

    try {
        if (state.editingMemory) {
            // Update would need PATCH endpoint - not implemented yet
            showNotification('Edit not yet implemented', 'warning');
        } else {
            await apiCall('/memory/save', {
                method: 'POST',
                body: JSON.stringify(payload)
            });
            showNotification('Memory saved!', 'success');
            closeModal();
            loadMemories();
        }
    } catch (error) {
        // Error already shown
    }
}

// Statistics
async function loadStats() {
    try {
        const data = await apiCall('/memory/stats');
        state.stats = data;
        renderStats();
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

function renderStats() {
    if (!state.stats) return;

    document.getElementById('totalMemories').textContent = state.stats.total_memories || 0;
    document.getElementById('totalProjects').textContent = state.stats.total_projects || 0;
    document.getElementById('totalTags').textContent = state.stats.total_tags || 0;
    document.getElementById('avgSize').textContent = state.stats.avg_text_length 
        ? `${state.stats.avg_text_length.toFixed(0)} chars` 
        : '-';

    renderProjectChart();
    renderTagCloud();
}

function renderProjectChart() {
    if (!state.stats.memories_by_project) return;

    const chart = document.getElementById('projectChart');
    const projects = Object.entries(state.stats.memories_by_project)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    const maxCount = Math.max(...projects.map(([_, count]) => count));

    chart.innerHTML = projects.map(([project, count]) => {
        const width = (count / maxCount) * 100;
        return `
            <div class="chart-bar">
                <span class="chart-label">${project}</span>
                <div class="chart-bar-fill" style="width: ${width}%">
                    <span class="chart-value">${count}</span>
                </div>
            </div>
        `;
    }).join('');
}

function renderTagCloud() {
    if (!state.stats.tags_distribution) return;

    const cloud = document.getElementById('tagCloud');
    const tags = Object.entries(state.stats.tags_distribution)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30);

    const maxCount = Math.max(...tags.map(([_, count]) => count));

    cloud.innerHTML = tags.map(([tag, count]) => {
        let sizeClass = '';
        const ratio = count / maxCount;
        if (ratio > 0.7) sizeClass = 'large';
        else if (ratio > 0.4) sizeClass = 'medium';

        return `<span class="tag-cloud-item ${sizeClass}" title="${count} memories">${tag}</span>`;
    }).join('');
}

// Settings
function saveSettings() {
    config.apiUrl = document.getElementById('apiUrl').value.trim();
    config.apiKey = document.getElementById('apiKey').value.trim();
    config.pageSize = parseInt(document.getElementById('pageSize').value);

    localStorage.setItem('apiUrl', config.apiUrl);
    localStorage.setItem('apiKey', config.apiKey);
    localStorage.setItem('pageSize', config.pageSize);

    showNotification('Settings saved!', 'success');
    loadMemories();
}

// Pagination
function changePage(delta) {
    const newPage = state.currentPage + delta;
    if (newPage < 1 || newPage > state.totalPages) return;
    
    state.currentPage = newPage;
    loadMemories();
}

function updatePagination() {
    document.getElementById('pageInfo').textContent = `Page ${state.currentPage} of ${state.totalPages}`;
    document.getElementById('prevPage').disabled = state.currentPage === 1;
    document.getElementById('nextPage').disabled = state.currentPage === state.totalPages;
}

// Utilities
function formatDate(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    
    return date.toLocaleDateString();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showNotification(message, type = 'info') {
    // Simple alert for now - could be replaced with toast notifications
    const prefix = type === 'error' ? 'Error: ' : type === 'success' ? 'Success: ' : 'Info: ';
    alert(prefix + message);
}
