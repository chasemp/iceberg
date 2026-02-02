// Iceberg SPA - Main Application

// State
let state = {
    index: null,
    selectedDimension: null,
    filters: {
        source: 'all',
        timeframe: 'all',
        language: 'all',
        aiTools: 'all'
    },
    sort: 'stars-desc',
    searchQuery: '',
    rankings: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await loadData();
    renderStatistics();
    renderDimensions();
    populateLanguageFilter();

    // Handle initial URL
    const hash = window.location.hash.slice(1); // Remove #
    if (hash) {
        handleHashChange(hash);
    } else {
        selectDefaultDimension();
    }
});

// Handle hash changes for navigation
window.addEventListener('hashchange', () => {
    const hash = window.location.hash.slice(1);
    if (hash) {
        handleHashChange(hash);
    }
});

function handleHashChange(hash) {
    // Handle tab switching: #rankings or #about
    if (hash === 'rankings' || hash === 'about') {
        switchTab(hash, false); // false = don't update URL
    }
    // Handle dimension selection: #trending-monthly
    else if (hash.startsWith('trending-') || hash.startsWith('search:')) {
        // Make sure discovery tab is active
        switchTab('discovery', false);
        const dimension = state.index?.dimensions?.find(d => d.id === hash);
        if (dimension) {
            selectDimension(dimension, false); // false = don't update URL
        }
    }
    // Handle repo detail: #repo/owner/name
    else if (hash.startsWith('repo/')) {
        const parts = hash.split('/');
        if (parts.length === 3) {
            const [_, owner, name] = parts;
            showRepoDetailFromUrl(owner, name);
        }
    }
}

async function showRepoDetailFromUrl(owner, name) {
    // Create a minimal repo object for showRepoDetail
    const repo = {
        owner,
        name,
        full_name: `${owner}/${name}`,
        url: `https://github.com/${owner}/${name}`
    };
    await showRepoDetail(repo);
}

// Event Listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => switchTab(button.dataset.tab));
    });

    // Filters
    document.getElementById('source-filter').addEventListener('change', (e) => {
        state.filters.source = e.target.value;
        renderDimensions();
    });

    document.getElementById('timeframe-filter').addEventListener('change', (e) => {
        state.filters.timeframe = e.target.value;
        renderDimensions();
    });

    document.getElementById('language-filter').addEventListener('change', (e) => {
        state.filters.language = e.target.value;
        renderDimensions();
    });

    document.getElementById('ai-filter').addEventListener('change', (e) => {
        state.filters.aiTools = e.target.value;
        renderDimensions();
    });

    document.getElementById('sort-select').addEventListener('change', (e) => {
        state.sort = e.target.value;
        // Re-render current dimension with new sort
        if (state.selectedDimension) {
            const dimension = state.index.dimensions.find(d => d.id === state.selectedDimension);
            if (dimension) {
                renderRepositories(dimension);
            }
        }
    });

    document.getElementById('repo-search').addEventListener('input', (e) => {
        state.searchQuery = e.target.value;
        // Re-render current dimension with new search
        if (state.selectedDimension) {
            const dimension = state.index.dimensions.find(d => d.id === state.selectedDimension);
            if (dimension) {
                renderRepositories(dimension);
            }
        }
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('repo-modal').addEventListener('click', (e) => {
        if (e.target.id === 'repo-modal') closeModal();
    });
}

// Statistics Rendering
function renderStatistics() {
    const container = document.getElementById('stats-summary');

    if (!state.index || !state.index.dimensions) {
        container.innerHTML = '';
        return;
    }

    // Calculate aggregate statistics
    const repos = getAllRepos();
    const totalRepos = repos.length;
    const languages = new Set(repos.map(r => r.language).filter(Boolean));
    const avgStars = totalRepos > 0
        ? Math.round(repos.reduce((sum, r) => sum + (r.stars || 0), 0) / totalRepos)
        : 0;

    // Count repos with AI tools
    const reposWithAI = repos.filter(r => r.ai_tools && r.ai_tools.length > 0).length;

    const stats = [
        { value: totalRepos.toLocaleString(), label: 'Repositories' },
        { value: languages.size.toLocaleString(), label: 'Languages' },
        { value: avgStars.toLocaleString(), label: 'Avg Stars' },
        { value: reposWithAI.toLocaleString(), label: 'Using AI Tools' },
    ];

    container.innerHTML = stats.map(stat => `
        <div class="stat-summary-card">
            <span class="stat-summary-value">${stat.value}</span>
            <span class="stat-summary-label">${stat.label}</span>
        </div>
    `).join('');
}

// Data Loading
async function loadData() {
    // Show loading state
    document.getElementById('dimensions-list').innerHTML = `
        <div class="loading-container">
            <div class="spinner"></div>
            <p class="loading-text">Loading discovery data...</p>
        </div>
    `;

    try {
        const response = await fetch('data/index.json');
        if (!response.ok) throw new Error('Failed to load index.json');
        state.index = await response.json();

        // Update last updated timestamp
        if (state.index.generated_at) {
            const date = new Date(state.index.generated_at);
            document.getElementById('last-updated').textContent = date.toLocaleString();
        }

        // Try to load rankings (may not exist yet)
        try {
            const rankingsResponse = await fetch('data/rankings.json');
            if (rankingsResponse.ok) {
                state.rankings = await rankingsResponse.json();
                renderRankings();
            }
        } catch (e) {
            console.log('Rankings not available yet');
        }

    } catch (error) {
        console.error('Error loading data:', error);
        document.getElementById('dimensions-list').innerHTML =
            '<p class="placeholder">Failed to load data. Please try again later.</p>';
    }
}

// Tab Switching
function switchTab(tabName, updateUrl = true) {
    // Update buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.toggle('active', content.id === `${tabName}-tab`);
    });

    // Load rankings if switching to rankings tab
    if (tabName === 'rankings' && !state.rankings) {
        renderRankings();
    }

    // Update URL for shareability (but not for discovery tab, as dimension will handle that)
    if (updateUrl && (tabName === 'rankings' || tabName === 'about')) {
        window.location.hash = tabName;
    }
}

// Dimension Filtering and Rendering
function getDimensions() {
    if (!state.index || !state.index.dimensions) return [];

    return state.index.dimensions.filter(dimension => {
        // Source filter
        if (state.filters.source !== 'all') {
            if (state.filters.source === 'trending' && !dimension.type === 'trending') return false;
            if (state.filters.source === 'search' && dimension.type !== 'search') return false;
        }

        // Timeframe filter (only for trending)
        if (state.filters.timeframe !== 'all' && dimension.type === 'trending') {
            if (dimension.timeframe !== state.filters.timeframe) return false;
        }

        return true;
    });
}

function getAllRepos() {
    const dimensions = getDimensions();
    const reposMap = new Map();

    dimensions.forEach(dimension => {
        if (dimension.type === 'trending' && dimension.snapshots) {
            // Use most recent snapshot
            const latestSnapshot = dimension.snapshots[dimension.snapshots.length - 1];
            if (latestSnapshot && latestSnapshot.repos) {
                latestSnapshot.repos.forEach(repo => {
                    const key = `${repo.owner}/${repo.name}`;
                    if (!reposMap.has(key)) {
                        reposMap.set(key, repo);
                    }
                });
            }
        } else if (dimension.type === 'search' && dimension.repos) {
            dimension.repos.forEach(repo => {
                const key = `${repo.owner}/${repo.name}`;
                if (!reposMap.has(key)) {
                    reposMap.set(key, repo);
                }
            });
        }
    });

    return Array.from(reposMap.values());
}

function populateLanguageFilter() {
    const repos = getAllRepos();
    const languages = new Set(repos.map(r => r.language).filter(Boolean));

    const select = document.getElementById('language-filter');
    select.innerHTML = '<option value="all">All Languages</option>';

    Array.from(languages).sort().forEach(lang => {
        const option = document.createElement('option');
        option.value = lang;
        option.textContent = lang;
        select.appendChild(option);
    });
}

function renderDimensions() {
    const dimensions = getDimensions();
    const container = document.getElementById('dimensions-list');

    if (dimensions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔍</div>
                <h3 class="empty-state-title">No dimensions found</h3>
                <p class="empty-state-message">
                    Try adjusting your filters or run the data collection workflow to discover repositories.
                </p>
            </div>
        `;
        return;
    }

    container.innerHTML = '';

    dimensions.forEach(dimension => {
        const card = createDimensionCard(dimension);
        container.appendChild(card);
    });
}

function createDimensionCard(dimension) {
    const card = document.createElement('div');
    card.className = 'dimension-card';
    if (state.selectedDimension === dimension.id) {
        card.classList.add('selected');
    }

    const title = document.createElement('div');
    title.className = 'dimension-title';
    title.textContent = formatDimensionTitle(dimension);

    const meta = document.createElement('div');
    meta.className = 'dimension-meta';

    const typeBadge = document.createElement('span');
    typeBadge.className = 'dimension-badge';
    typeBadge.textContent = dimension.type;

    meta.appendChild(typeBadge);

    if (dimension.type === 'trending' && dimension.snapshots) {
        const snapshotCount = document.createElement('span');
        snapshotCount.textContent = `${dimension.snapshots.length} snapshot${dimension.snapshots.length !== 1 ? 's' : ''}`;
        meta.appendChild(snapshotCount);
    } else if (dimension.type === 'search') {
        const repoCount = document.createElement('span');
        repoCount.textContent = `${dimension.count} repos`;
        meta.appendChild(repoCount);
    }

    card.appendChild(title);
    card.appendChild(meta);

    card.addEventListener('click', () => selectDimension(dimension));

    return card;
}

function formatDimensionTitle(dimension) {
    if (dimension.type === 'trending') {
        return `Trending ${dimension.timeframe.charAt(0).toUpperCase() + dimension.timeframe.slice(1)}`;
    } else if (dimension.type === 'search') {
        // Simplify search query display
        let query = dimension.query;
        // Remove "stars:" prefix and format nicely
        query = query.replace(/stars:/gi, 'Stars ');
        query = query.replace(/language:/gi, '');
        // Clean up extra spaces
        query = query.replace(/\s+/g, ' ').trim();
        return query;
    }
    return dimension.id;
}

function selectDimension(dimension, updateUrl = true) {
    state.selectedDimension = dimension.id;
    renderDimensions();
    renderRepositories(dimension);

    // Update URL for shareability
    if (updateUrl) {
        window.location.hash = dimension.id;
    }
}

function selectDefaultDimension() {
    // Auto-select latest monthly trending to show something on load
    if (!state.index || !state.index.dimensions) return;

    // Find trending-monthly dimension
    const monthly = state.index.dimensions.find(d => d.id === 'trending-monthly');
    if (monthly && monthly.snapshots && monthly.snapshots.length > 0) {
        // Select the latest snapshot
        selectDimension(monthly);
        return;
    }

    // Fallback to trending-weekly
    const weekly = state.index.dimensions.find(d => d.id === 'trending-weekly');
    if (weekly && weekly.snapshots && weekly.snapshots.length > 0) {
        selectDimension(weekly);
        return;
    }

    // Fallback to trending-daily
    const daily = state.index.dimensions.find(d => d.id === 'trending-daily');
    if (daily && daily.snapshots && daily.snapshots.length > 0) {
        selectDimension(daily);
        return;
    }

    // Fallback to first available dimension
    if (state.index.dimensions.length > 0) {
        selectDimension(state.index.dimensions[0]);
    }
}

// Repository Rendering
async function renderRepositories(dimension) {
    const container = document.getElementById('repositories-list');
    const title = document.getElementById('repos-title');

    title.textContent = `Repositories - ${formatDimensionTitle(dimension)}`;

    let repos = [];

    if (dimension.type === 'trending' && dimension.snapshots) {
        // Use most recent snapshot
        const latestSnapshot = dimension.snapshots[dimension.snapshots.length - 1];
        repos = latestSnapshot ? latestSnapshot.repos : [];
    } else if (dimension.type === 'search') {
        repos = dimension.repos || [];
    }

    // Apply language filter
    if (state.filters.language !== 'all') {
        repos = repos.filter(r => r.language === state.filters.language);
    }

    // Apply AI tools filter
    if (state.filters.aiTools !== 'all') {
        repos = repos.filter(r => {
            if (!r.ai_tools || r.ai_tools.length === 0) {
                return false;
            }
            if (state.filters.aiTools === 'any') {
                return true;
            }
            // Check if the specific tool is in the list (case-insensitive)
            const toolName = state.filters.aiTools.toLowerCase();
            return r.ai_tools.some(tool => tool.toLowerCase().includes(toolName));
        });
    }

    // Apply search filter
    if (state.searchQuery && state.searchQuery.trim() !== '') {
        const query = state.searchQuery.toLowerCase().trim();
        repos = repos.filter(r => {
            const name = (r.name || '').toLowerCase();
            const owner = (r.owner || '').toLowerCase();
            const fullName = (r.full_name || `${owner}/${name}`).toLowerCase();
            const description = (r.description || '').toLowerCase();

            return fullName.includes(query) ||
                   name.includes(query) ||
                   owner.includes(query) ||
                   description.includes(query);
        });
    }

    // Apply sorting
    repos = sortRepositories(repos, state.sort);

    if (repos.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📂</div>
                <h3 class="empty-state-title">No repositories match</h3>
                <p class="empty-state-message">
                    Try adjusting the language filter or select a different dimension.
                </p>
            </div>
        `;
        return;
    }

    container.innerHTML = '<div class="loading-container"><div class="spinner"></div></div>';

    // Create bars asynchronously (need to fetch analysis data)
    const bars = await Promise.all(repos.map(repo => createRepoBar(repo)));

    // Filter out null bars (repos without LoC data)
    const validBars = bars.filter(bar => bar !== null);

    if (validBars.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📊</div>
                <h3 class="empty-state-title">No analyzed repositories</h3>
                <p class="empty-state-message">
                    None of these repositories have been analyzed yet. Run analysis to see their code breakdown.
                </p>
            </div>
        `;
        return;
    }

    container.innerHTML = '';
    validBars.forEach(bar => container.appendChild(bar));
}

function sortRepositories(repos, sortBy) {
    const sorted = [...repos]; // Create a copy to avoid mutation

    switch (sortBy) {
        case 'stars-desc':
            sorted.sort((a, b) => (b.stars || 0) - (a.stars || 0));
            break;
        case 'stars-asc':
            sorted.sort((a, b) => (a.stars || 0) - (b.stars || 0));
            break;
        case 'name-asc':
            sorted.sort((a, b) => {
                const nameA = (a.full_name || `${a.owner}/${a.name}`).toLowerCase();
                const nameB = (b.full_name || `${b.owner}/${b.name}`).toLowerCase();
                return nameA.localeCompare(nameB);
            });
            break;
        case 'name-desc':
            sorted.sort((a, b) => {
                const nameA = (a.full_name || `${a.owner}/${a.name}`).toLowerCase();
                const nameB = (b.full_name || `${b.owner}/${b.name}`).toLowerCase();
                return nameB.localeCompare(nameA);
            });
            break;
        default:
            // Default to stars descending
            sorted.sort((a, b) => (b.stars || 0) - (a.stars || 0));
    }

    return sorted;
}

async function createRepoBar(repo) {
    // Fetch analysis data for this repo
    const fileName = `${repo.owner}-${repo.name}.json`;
    let analysis = null;

    try {
        const response = await fetch(`data/repos/${fileName}`);
        if (response.ok) {
            const data = await response.json();
            analysis = data.analysis;
        }
    } catch (e) {
        // No analysis data available
    }

    // Skip repos without LoC data
    if (!analysis || !analysis.loc) {
        return null;
    }

    const bar = document.createElement('div');
    bar.className = 'repo-bar-item';

    // Calculate percentages
    const projectLoc = analysis.loc;
    const depLoc = analysis.total_loc ? (analysis.total_loc - projectLoc) : 0;
    const totalLoc = projectLoc + depLoc;
    const projectPercent = (projectLoc / totalLoc) * 100;
    const depPercent = (depLoc / totalLoc) * 100;

    bar.innerHTML = `
        <div class="repo-bar-label">
            <span class="repo-bar-name">${repo.full_name || `${repo.owner}/${repo.name}`}</span>
            <span class="repo-bar-meta">
                ${repo.language ? `<span class="lang-badge">${repo.language}</span>` : ''}
                <span class="loc-badge">${totalLoc.toLocaleString()} LoC</span>
            </span>
        </div>
        <div class="repo-bar-chart">
            <div class="repo-bar-segment repo-bar-local"
                 style="width: ${projectPercent}%"
                 title="Local: ${projectLoc.toLocaleString()} LoC (${projectPercent.toFixed(1)}%)">
            </div>
            <div class="repo-bar-segment repo-bar-deps"
                 style="width: ${depPercent}%"
                 title="Dependencies: ${depLoc.toLocaleString()} LoC (${depPercent.toFixed(1)}%)">
            </div>
        </div>
        <div class="repo-bar-legend">
            <span class="legend-local">${projectPercent.toFixed(0)}% local</span>
            ${depPercent > 0 ? `<span class="legend-deps">${depPercent.toFixed(0)}% deps</span>` : ''}
        </div>
    `;

    bar.addEventListener('click', async () => {
        await showRepoDetail(repo);
    });

    return bar;
}

// Repository Detail Modal
async function showRepoDetail(repo) {
    const modal = document.getElementById('repo-modal');
    const detailContainer = document.getElementById('repo-detail');

    modal.classList.add('active');
    detailContainer.innerHTML = `
        <div class="loading-container">
            <div class="spinner"></div>
            <p class="loading-text">Loading repository details...</p>
        </div>
    `;

    // Update URL for shareability
    window.location.hash = `repo/${repo.owner}/${repo.name}`;

    try {
        // Try to load analysis data
        const fileName = `${repo.owner}-${repo.name}.json`;
        const response = await fetch(`data/repos/${fileName}`);

        if (!response.ok) {
            throw new Error('Analysis not available');
        }

        const data = await response.json();

        // Try to load graph data
        let graphData = null;
        try {
            const graphResponse = await fetch(`data/graphs/${fileName}`);
            if (graphResponse.ok) {
                graphData = await graphResponse.json();
            }
        } catch (e) {
            // Graph data not available, continue without it
        }

        renderRepoDetail(data, graphData);

    } catch (error) {
        console.error('Error loading repo detail:', error);
        detailContainer.innerHTML = `
            <div class="repo-detail-header">
                <h2 class="repo-detail-title">${repo.full_name || `${repo.owner}/${repo.name}`}</h2>
                <a href="${repo.url}" target="_blank" class="repo-detail-url">View on GitHub →</a>
            </div>
            <p>Analysis data not available for this repository yet.</p>
        `;
    }
}

function renderRepoDetail(data, graphData = null) {
    const detailContainer = document.getElementById('repo-detail');
    const analysis = data.analysis;

    const header = `
        <div class="repo-detail-header">
            <h2 class="repo-detail-title">${data.full_name}</h2>
            <a href="${data.url}" target="_blank" class="repo-detail-url">View on GitHub →</a>
        </div>
    `;

    let content = '';

    if (analysis && analysis.loc !== undefined) {
        // Project has been analyzed
        const projectLoc = analysis.loc;
        const hasFullAnalysis = analysis.total_loc !== undefined && analysis.ratio !== undefined;

        if (hasFullAnalysis) {
            // Full analysis with dependencies
            const totalLoc = analysis.total_loc;
            const ratio = analysis.ratio;

            content += `
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-value">${projectLoc.toLocaleString()}</span>
                        <span class="stat-label">Project LoC</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${totalLoc.toLocaleString()}</span>
                        <span class="stat-label">Dependencies LoC</span>
                    </div>
                    <div class="stat-card">
                        <span class="stat-value">${(ratio * 100).toFixed(1)}%</span>
                        <span class="stat-label">Iceberg Ratio</span>
                    </div>
                </div>
            `;

            // Add pie chart
            content += `
                <div class="iceberg-chart">
                    <h3>Code Distribution</h3>
                    <div class="chart-container">
                        <canvas id="pie-chart" width="300" height="300"></canvas>
                    </div>
                </div>
            `;
        } else {
            // Partial analysis - project LoC only
            content += `
                <div class="stats-grid">
                    <div class="stat-card">
                        <span class="stat-value">${projectLoc.toLocaleString()}</span>
                        <span class="stat-label">Project LoC</span>
                    </div>
                </div>
                <p style="margin-top: 1rem; color: var(--text-muted);">
                    <strong>Note:</strong> Package not detected or dependencies not analyzed.
                    Only project size is available.
                </p>
            `;
        }

        // Add metadata
        if (analysis.package) {
            const pkg = analysis.package;
            content += `<p><strong>Package:</strong> ${pkg.system}:${pkg.name}@${pkg.version}</p>`;
        }
        if (analysis.version) {
            content += `<p><strong>Version:</strong> ${analysis.version}</p>`;
        }
        if (analysis.source) {
            content += `<p><strong>Source:</strong> ${analysis.source}</p>`;
        }
        if (analysis.cached_at) {
            const date = new Date(analysis.cached_at);
            content += `<p><strong>Analyzed:</strong> ${date.toLocaleString()}</p>`;
        }

        // Add AI tools detection
        if (analysis.ai_tools && analysis.ai_tools.length > 0) {
            content += `
                <div style="margin-top: 1.5rem; padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius); border-left: 4px solid var(--primary);">
                    <p style="margin: 0; font-weight: 600; color: var(--primary);">
                        🤖 AI-Assisted Development Detected
                    </p>
                    <p style="margin: 0.5rem 0 0 0; color: var(--text-muted);">
                        Tools: ${analysis.ai_tools.join(', ')}
                    </p>
                </div>
            `;
        }

        // Add dependency graph info if available
        if (graphData && graphData.nodes && graphData.edges) {
            content += `
                <div style="margin-top: 1.5rem; padding: 1rem; background: var(--bg-secondary); border-radius: var(--radius); border-left: 4px solid var(--success);">
                    <p style="margin: 0; font-weight: 600; color: var(--success);">
                        🕸️ Dependency Graph Available
                    </p>
                    <p style="margin: 0.5rem 0 0 0; color: var(--text-muted);">
                        ${graphData.nodes.length} packages, ${graphData.edges.length} dependencies
                    </p>
                </div>
            `;
        }

    } else {
        content += '<p>Analysis in progress or not yet started.</p>';
    }

    detailContainer.innerHTML = header + content;

    // Draw pie chart only if we have full analysis
    if (analysis && analysis.loc !== undefined && analysis.total_loc !== undefined) {
        drawPieChart(analysis.loc, analysis.total_loc);
    }
}

function drawPieChart(projectLoc, depLoc) {
    const canvas = document.getElementById('pie-chart');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 120;

    const total = projectLoc + depLoc;
    const projectAngle = (projectLoc / total) * 2 * Math.PI;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw project slice (blue)
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + projectAngle);
    ctx.closePath();
    ctx.fillStyle = '#2563eb';
    ctx.fill();

    // Draw dependencies slice (orange)
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.arc(centerX, centerY, radius, -Math.PI / 2 + projectAngle, -Math.PI / 2 + 2 * Math.PI);
    ctx.closePath();
    ctx.fillStyle = '#f59e0b';
    ctx.fill();

    // Draw legend
    ctx.font = '14px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    // Project label
    ctx.fillStyle = '#2563eb';
    ctx.fillRect(centerX - 80, centerY + radius + 20, 15, 15);
    ctx.fillStyle = '#1e293b';
    ctx.fillText(`Project: ${projectLoc.toLocaleString()} LoC`, centerX - 60, centerY + radius + 32);

    // Dependencies label
    ctx.fillStyle = '#f59e0b';
    ctx.fillRect(centerX - 80, centerY + radius + 45, 15, 15);
    ctx.fillStyle = '#1e293b';
    ctx.fillText(`Dependencies: ${depLoc.toLocaleString()} LoC`, centerX - 60, centerY + radius + 57);
}

function closeModal() {
    document.getElementById('repo-modal').classList.remove('active');

    // Restore dimension URL when closing modal
    if (state.selectedDimension) {
        window.location.hash = state.selectedDimension;
    } else {
        window.location.hash = '';
    }
}

// Rankings
function renderRankings() {
    const container = document.getElementById('rankings-list');

    if (!state.rankings || !state.rankings.packages) {
        container.innerHTML = '<p class="placeholder">Rankings data not available yet</p>';
        return;
    }

    container.innerHTML = '';

    state.rankings.packages.forEach((pkg, index) => {
        const item = createRankingItem(pkg, index + 1);
        container.appendChild(item);
    });
}

function createRankingItem(pkg, position) {
    const item = document.createElement('div');
    item.className = 'ranking-item';

    const posDiv = document.createElement('div');
    posDiv.className = 'ranking-position';
    if (position <= 3) posDiv.classList.add('top-3');
    posDiv.textContent = position;

    const info = document.createElement('div');
    info.className = 'ranking-info';

    const name = document.createElement('div');
    name.className = 'ranking-name';
    name.textContent = pkg.name;

    const system = document.createElement('div');
    system.className = 'ranking-system';
    system.textContent = pkg.system;

    info.appendChild(name);
    info.appendChild(system);

    const count = document.createElement('div');
    count.className = 'ranking-count';
    count.textContent = `${pkg.count} project${pkg.count !== 1 ? 's' : ''}`;

    item.appendChild(posDiv);
    item.appendChild(info);
    item.appendChild(count);

    return item;
}
