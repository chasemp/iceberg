// Iceberg SPA - Main Application

// State
let state = {
    index: null,
    selectedDimension: null,
    filters: {
        onlyWithDeps: false,  // Toggle to show only repos with dependencies
        trending: ['weekly', 'monthly'],  // Selected trending timeframes: 'weekly', 'monthly'
        stars: ['0-100', '100-1000', '1000-10000', '10000+'],  // Selected star ranges
        languages: [],  // Selected languages (populated on load with all languages)
        aiTools: []  // Selected AI tools (empty = show all repos including those without AI tools)
    },
    sort: 'stars-desc',
    searchQuery: '',
    rankings: null,
    analysisRepoCount: null  // Set after first render to track repos with analysis data
};

// Initialize app
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await loadData();
    renderStatistics();
    populateLanguageFilter();

    // Initialize dropdown button labels to reflect default selections
    initializeDropdownLabels();

    // Show all repositories by default
    await renderFilteredRepositories();

    // Update dropdown counts with initial filter state
    await updateDropdownCounts();

    // Handle initial URL
    const hash = window.location.hash.slice(1); // Remove #
    if (hash) {
        handleHashChange(hash);
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

    // Sort and search filters
    document.getElementById('sort-select').addEventListener('change', (e) => {
        state.sort = e.target.value;
        // Re-render with new sort
        renderFilteredRepositories();
    });

    document.getElementById('repo-search').addEventListener('input', async (e) => {
        state.searchQuery = e.target.value;
        // Re-render with new search
        await renderFilteredRepositories();
        await updateDropdownCounts();
    });

    document.getElementById('deps-toggle').addEventListener('change', async (e) => {
        state.filters.onlyWithDeps = e.target.checked;
        // Re-render with new filter
        await renderFilteredRepositories();
        await updateDropdownCounts();
    });

    // Multiselect dropdowns
    setupMultiselectDropdowns();

    // Clear and Reset filter buttons
    document.getElementById('clear-filters-btn').addEventListener('click', clearAllFilters);
    document.getElementById('reset-filters-btn').addEventListener('click', resetAllFilters);

    // Modal close
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('repo-modal').addEventListener('click', (e) => {
        if (e.target.id === 'repo-modal') closeModal();
    });
}

// Setup multiselect dropdowns for all filters
function setupMultiselectDropdowns() {
    const trendingDropdown = document.querySelector('[data-testid="trending-dropdown"]');
    const starsDropdown = document.querySelector('[data-testid="stars-dropdown"]');
    const aiToolsDropdown = document.querySelector('[data-testid="ai-tools-dropdown"]');

    if (trendingDropdown) {
        setupDropdown(trendingDropdown, 'trending', updateTrendingFilter);
    }

    if (starsDropdown) {
        setupDropdown(starsDropdown, 'stars', updateStarsFilter);
    }

    if (aiToolsDropdown) {
        setupDropdown(aiToolsDropdown, 'ai-tools', updateAIToolsFilter);
    }

    // Note: language dropdown is set up in populateLanguageFilter() after options are populated

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multiselect-dropdown')) {
            document.querySelectorAll('.multiselect-menu.open').forEach(menu => {
                menu.classList.remove('open');
            });
        }
    });
}

function setupDropdown(dropdownElement, filterType, updateCallback) {
    const button = dropdownElement.querySelector('.multiselect-button');
    const menu = dropdownElement.querySelector('.multiselect-menu');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]');

    // Toggle dropdown
    button.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = menu.classList.contains('open');

        // Close all other dropdowns
        document.querySelectorAll('.multiselect-menu.open').forEach(m => {
            if (m !== menu) m.classList.remove('open');
        });

        // Toggle this dropdown
        if (isOpen) {
            menu.classList.remove('open');
        } else {
            menu.classList.add('open');
        }
    });

    // Handle checkbox changes
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            updateCallback();
            updateDropdownButton(dropdownElement, filterType);
        });
    });

    // Prevent menu from closing when clicking inside
    menu.addEventListener('click', (e) => {
        e.stopPropagation();
    });
}

function updateDropdownButton(dropdownElement, filterType) {
    const button = dropdownElement.querySelector('.multiselect-button');
    const label = button.querySelector('.multiselect-label');
    const menu = dropdownElement.querySelector('.multiselect-menu');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    const count = checkboxes.length;

    if (count === 0) {
        const placeholders = {
            'trending': 'Trending',
            'stars': 'Star ranges',
            'language': 'Languages',
            'ai-tools': 'AI Usage'
        };
        label.textContent = placeholders[filterType] || 'Select options';
    } else {
        const selectedLabels = {
            'trending': `${count} trending selected`,
            'stars': `${count} star range${count !== 1 ? 's' : ''}`,
            'language': `${count} language${count !== 1 ? 's' : ''}`,
            'ai-tools': `${count} AI Usage${count !== 1 ? 's' : ''}`
        };
        label.textContent = selectedLabels[filterType] || `${count} selected`;
    }
}

function initializeDropdownLabels() {
    // Update all dropdown button labels to reflect initial checked state
    const dropdowns = [
        { selector: '[data-testid="trending-dropdown"]', type: 'trending' },
        { selector: '[data-testid="stars-dropdown"]', type: 'stars' },
        { selector: '[data-testid="ai-tools-dropdown"]', type: 'ai-tools' }
    ];

    dropdowns.forEach(({ selector, type }) => {
        const dropdown = document.querySelector(selector);
        if (dropdown) {
            updateDropdownButton(dropdown, type);
        }
    });
}

async function updateTrendingFilter() {
    const menu = document.querySelector('[data-testid="trending-dropdown-menu"]');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    state.filters.trending = Array.from(checkboxes).map(cb => cb.value);
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function updateStarsFilter() {
    const menu = document.querySelector('[data-testid="stars-dropdown-menu"]');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    state.filters.stars = Array.from(checkboxes).map(cb => cb.value);
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function updateLanguageFilter() {
    const menu = document.querySelector('[data-testid="language-dropdown-menu"]');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    state.filters.languages = Array.from(checkboxes).map(cb => cb.value);
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function updateAIToolsFilter() {
    const menu = document.querySelector('[data-testid="ai-tools-dropdown-menu"]');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    state.filters.aiTools = Array.from(checkboxes).map(cb => cb.value);
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function clearAllFilters() {
    // Uncheck all checkboxes in all filter dropdowns
    document.querySelectorAll('.multiselect-menu input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    // Clear state
    state.filters.trending = [];
    state.filters.stars = [];
    state.filters.languages = [];
    state.filters.aiTools = [];

    // Update all dropdown button labels
    updateDropdownButton(document.querySelector('[data-testid="trending-dropdown"]'), 'trending');
    updateDropdownButton(document.querySelector('[data-testid="stars-dropdown"]'), 'stars');
    updateDropdownButton(document.querySelector('[data-testid="language-dropdown"]'), 'language');
    updateDropdownButton(document.querySelector('[data-testid="ai-tools-dropdown"]'), 'ai-tools');

    // Re-render with cleared filters (should show no results)
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function resetAllFilters() {
    // Reset trending filter (weekly, monthly)
    state.filters.trending = ['weekly', 'monthly'];
    document.querySelectorAll('[data-testid="trending-dropdown-menu"] input[type="checkbox"]').forEach(cb => {
        cb.checked = state.filters.trending.includes(cb.value);
    });
    updateDropdownButton(document.querySelector('[data-testid="trending-dropdown"]'), 'trending');

    // Reset stars filter (all ranges)
    state.filters.stars = ['0-100', '100-1000', '1000-10000', '10000+'];
    document.querySelectorAll('[data-testid="stars-dropdown-menu"] input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    updateDropdownButton(document.querySelector('[data-testid="stars-dropdown"]'), 'stars');

    // Reset languages filter (all languages)
    const repos = getAllRepos();
    const languages = Array.from(new Set(repos.map(r => r.language).filter(Boolean))).sort();
    state.filters.languages = languages;
    document.querySelectorAll('[data-testid="language-dropdown-menu"] input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    updateDropdownButton(document.querySelector('[data-testid="language-dropdown"]'), 'language');

    // Reset AI tools filter (none selected = show all)
    state.filters.aiTools = [];
    document.querySelectorAll('[data-testid="ai-tools-dropdown-menu"] input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    updateDropdownButton(document.querySelector('[data-testid="ai-tools-dropdown"]'), 'ai-tools');

    // Re-render with reset filters
    await renderFilteredRepositories();
    await updateDropdownCounts();
}

async function renderFilteredRepositories() {
    // Get all repos from all dimensions
    const allRepos = getAllRepos();

    // If required filters are empty, show no results (user clicked "clear")
    // Note: AI tools is optional, so not included in this check
    const requiredFiltersEmpty = state.filters.trending.length === 0 &&
                                 state.filters.stars.length === 0 &&
                                 state.filters.languages.length === 0;

    if (requiredFiltersEmpty) {
        await renderRepositoryList([]);
        return;
    }

    let filteredRepos = applyAllFilters(allRepos, {
        trending: state.filters.trending,
        stars: state.filters.stars,
        languages: state.filters.languages,
        searchQuery: state.searchQuery,
        aiTools: state.filters.aiTools
    });

    // Apply "Only with dependencies" filter (requires async)
    if (state.filters.onlyWithDeps) {
        const reposWithDeps = [];
        for (const repo of filteredRepos) {
            const hasDeps = await hasActualDependencies(repo);
            if (hasDeps) {
                reposWithDeps.push(repo);
            }
        }
        filteredRepos = reposWithDeps;
    }

    // Sort repos
    const sortedRepos = sortRepositories(filteredRepos, state.sort);

    // Render the repositories
    await renderRepositoryList(sortedRepos);
}


async function renderRepositoryList(repos) {
    const container = document.getElementById('repositories-list');
    const countElement = document.getElementById('results-count-number');

    if (repos.length === 0) {
        container.innerHTML = '<p class="placeholder">No repositories match the selected filters</p>';
        countElement.textContent = '0';
        return;
    }

    container.innerHTML = '';
    let renderedCount = 0;
    for (const repo of repos) {
        const repoBar = await createRepoBar(repo);
        if (repoBar) {  // Only append if not null (repos with analysis data)
            container.appendChild(repoBar);
            renderedCount++;
        }
    }

    // Update results count
    countElement.textContent = renderedCount.toLocaleString();

    if (state.analysisRepoCount === null) {
        state.analysisRepoCount = renderedCount;
        renderStatistics();
    }

    // If no repos were rendered, show a message
    if (renderedCount === 0) {
        container.innerHTML = '<p class="placeholder">No repositories with analysis data match the selected filters</p>';
    }
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
    const totalRepos = state.analysisRepoCount !== null ? state.analysisRepoCount : repos.length;
    const languages = new Set(repos.map(r => r.language).filter(Boolean));

    // Count repos with AI tools
    const reposWithAI = repos.filter(r => r.ai_tools && r.ai_tools.length > 0).length;

    const stats = [
        { value: totalRepos.toLocaleString(), label: 'Repositories' },
        { value: languages.size.toLocaleString(), label: 'Languages' },
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
        alert('Failed to load data. Please make sure the server is running and data files exist.');
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
    // Return all dimensions - filtering is now done in renderFilteredRepositories
    return state.index.dimensions;
}

function getAllRepos() {
    return deduplicateRepos(getDimensions());
}

function populateLanguageFilter() {
    const repos = getAllRepos();
    const languages = new Set(repos.map(r => r.language).filter(Boolean));

    const menu = document.getElementById('language-menu');
    if (!menu) return;

    menu.innerHTML = '';

    const sortedLanguages = Array.from(languages).sort();

    sortedLanguages.forEach(lang => {
        const label = document.createElement('label');
        label.className = 'multiselect-option';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = lang;
        checkbox.checked = true;  // Check all by default

        const span = document.createElement('span');
        span.textContent = lang;
        span.dataset.originalLabel = lang;  // Store original label for count updates

        label.appendChild(checkbox);
        label.appendChild(span);
        menu.appendChild(label);
    });

    // Initialize state with all languages selected
    state.filters.languages = sortedLanguages;

    // Re-setup the language dropdown after populating
    const languageDropdown = document.querySelector('[data-testid="language-dropdown"]');
    if (languageDropdown) {
        setupDropdown(languageDropdown, 'language', updateLanguageFilter);
        // Update the button to show selection count
        updateDropdownButton(languageDropdown, 'language');
    }
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

    // Show repo count for all dimension types
    if (dimension.count) {
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
    // renderDimensions() - not used anymore, we show all repos directly
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
    if (monthly && monthly.repos && monthly.repos.length > 0) {
        selectDimension(monthly);
        return;
    }

    // Fallback to trending-weekly
    const weekly = state.index.dimensions.find(d => d.id === 'trending-weekly');
    if (weekly && weekly.repos && weekly.repos.length > 0) {
        selectDimension(weekly);
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

    // All dimension types now have repos directly
    repos = dimension.repos || [];

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

    // Apply dependencies filter
    if (state.filters.onlyWithDeps) {
        // Filter to only show repos that have dependencies (total_loc > 0)
        const reposWithDeps = [];
        for (const repo of repos) {
            const hasDeps = await hasActualDependencies(repo);
            if (hasDeps) {
                reposWithDeps.push(repo);
            }
        }
        repos = reposWithDeps;
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
        case 'ratio-desc':
            sorted.sort((a, b) => (b.ratio || 0) - (a.ratio || 0));
            break;
        case 'project-loc-desc':
            sorted.sort((a, b) => (b.project_loc || 0) - (a.project_loc || 0));
            break;
        case 'dep-loc-desc':
            sorted.sort((a, b) => (b.dep_loc || 0) - (a.dep_loc || 0));
            break;
        case 'dep-count-desc':
            sorted.sort((a, b) => (b.dep_count || 0) - (a.dep_count || 0));
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

async function hasDepAnalysis(repo) {
    // Quick check if repo has dependency analysis data
    const fileName = `${repo.owner}-${repo.name}.json`;
    try {
        const response = await fetch(`data/repos/${fileName}`);
        if (!response.ok) return false;
        const data = await response.json();
        return data.analysis && data.analysis.total_loc !== null && data.analysis.total_loc !== undefined;
    } catch (error) {
        return false;
    }
}

async function hasActualDependencies(repo) {
    // Check if repo has actual dependencies (total_loc > 0)
    // Cache the result on the repo object to avoid repeated fetches
    if (repo._hasDepsCache !== undefined) {
        return repo._hasDepsCache;
    }

    const fileName = `${repo.owner}-${repo.name}.json`;
    try {
        const response = await fetch(`data/repos/${fileName}`);
        if (!response.ok) {
            repo._hasDepsCache = false;
            return false;
        }
        const data = await response.json();
        const totalLoc = data.analysis?.total_loc;
        const hasDeps = totalLoc !== null && totalLoc !== undefined && totalLoc > 0;
        repo._hasDepsCache = hasDeps;
        return hasDeps;
    } catch (error) {
        repo._hasDepsCache = false;
        return false;
    }
}

async function getFilteredReposExcluding(excludeFilterType) {
    const allRepos = getAllRepos();
    let filtered = allRepos;

    if (excludeFilterType !== 'trending') {
        filtered = filterByTrending(filtered, state.filters.trending);
    }
    if (excludeFilterType !== 'stars') {
        filtered = filterByStars(filtered, state.filters.stars);
    }
    if (excludeFilterType !== 'languages') {
        filtered = filterByLanguage(filtered, state.filters.languages);
    }
    if (excludeFilterType !== 'search') {
        filtered = filterBySearch(filtered, state.searchQuery);
    }
    if (excludeFilterType !== 'aiTools') {
        filtered = filterByAiTools(filtered, state.filters.aiTools);
    }

    if (excludeFilterType !== 'onlyWithDeps' && state.filters.onlyWithDeps) {
        const reposWithDeps = [];
        for (const repo of filtered) {
            const hasDeps = await hasActualDependencies(repo);
            if (hasDeps) {
                reposWithDeps.push(repo);
            }
        }
        filtered = reposWithDeps;
    }

    return filtered;
}

async function updateDropdownCounts() {
    // Update counts in all dropdown options based on current filter state

    // Update Language dropdown counts
    const languageMenu = document.querySelector('[data-testid="language-dropdown-menu"]');
    if (languageMenu) {
        const languageOptions = languageMenu.querySelectorAll('.multiselect-option');
        const baseRepos = await getFilteredReposExcluding('languages');

        for (const option of languageOptions) {
            const checkbox = option.querySelector('input[type="checkbox"]');
            const span = option.querySelector('span');
            const lang = checkbox.value;

            // Count repos that match this language
            const count = baseRepos.filter(repo => repo.language === lang).length;

            // Update label with count using original label
            const originalLabel = span.dataset.originalLabel || lang;
            span.textContent = `${originalLabel} (${count})`;
        }
    }

    // Update Trending dropdown counts
    const trendingMenu = document.querySelector('[data-testid="trending-dropdown-menu"]');
    if (trendingMenu) {
        const trendingOptions = trendingMenu.querySelectorAll('.multiselect-option');
        const baseRepos = await getFilteredReposExcluding('trending');

        for (const option of trendingOptions) {
            const checkbox = option.querySelector('input[type="checkbox"]');
            const span = option.querySelector('span');
            const timeframe = checkbox.value;

            // Count repos from this trending timeframe
            const count = baseRepos.filter(repo => repo.sources.includes(`trending-${timeframe}`)).length;

            // Update label with count using original label
            const originalLabel = span.dataset.originalLabel || timeframe;
            span.textContent = `${originalLabel} (${count})`;
        }
    }

    // Update Stars dropdown counts
    const starsMenu = document.querySelector('[data-testid="stars-dropdown-menu"]');
    if (starsMenu) {
        const starsOptions = starsMenu.querySelectorAll('.multiselect-option');
        const baseRepos = await getFilteredReposExcluding('stars');

        for (const option of starsOptions) {
            const checkbox = option.querySelector('input[type="checkbox"]');
            const span = option.querySelector('span');
            const range = checkbox.value;

            // Count repos in this star range
            const count = baseRepos.filter(repo => {
                const stars = repo.stars || 0;
                if (range === '0-100') return stars >= 0 && stars < 100;
                if (range === '100-1000') return stars >= 100 && stars < 1000;
                if (range === '1000-10000') return stars >= 1000 && stars < 10000;
                if (range === '10000+') return stars >= 10000;
                return false;
            }).length;

            // Update label with count using original label
            const originalLabel = span.dataset.originalLabel || range;
            span.textContent = `${originalLabel} (${count})`;
        }
    }

    // Update AI Tools dropdown counts
    const aiToolsMenu = document.querySelector('[data-testid="ai-tools-dropdown-menu"]');
    if (aiToolsMenu) {
        const aiToolsOptions = aiToolsMenu.querySelectorAll('.multiselect-option');
        const baseRepos = await getFilteredReposExcluding('aiTools');

        for (const option of aiToolsOptions) {
            const checkbox = option.querySelector('input[type="checkbox"]');
            const span = option.querySelector('span');
            const tool = checkbox.value;

            // Count repos with this AI tool
            let count;
            if (tool === 'any') {
                count = baseRepos.filter(repo => repo.ai_tools && repo.ai_tools.length > 0).length;
            } else {
                count = baseRepos.filter(repo =>
                    repo.ai_tools && repo.ai_tools.some(t => t.toLowerCase() === tool)
                ).length;
            }

            // Update label with count using original label
            const originalLabel = span.dataset.originalLabel || tool;
            span.textContent = `${originalLabel} (${count})`;
        }
    }
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
    const hasFullAnalysis = analysis.total_loc !== null && analysis.total_loc !== undefined;
    const depLoc = hasFullAnalysis ? analysis.total_loc : 0;
    const totalLoc = projectLoc + depLoc;
    const projectPercent = (projectLoc / totalLoc) * 100;
    const depPercent = (depLoc / totalLoc) * 100;

    // Build the bar chart
    let barContent = '';
    let legendContent = '';

    if (hasFullAnalysis) {
        // Full analysis with deps
        barContent = `
            <div class="repo-bar-segment repo-bar-local"
                 style="width: ${projectPercent}%"
                 title="Local: ${projectLoc.toLocaleString()} LoC (${projectPercent.toFixed(1)}%)">
            </div>
            ${depPercent > 0 ? `
            <div class="repo-bar-segment repo-bar-deps"
                 style="width: ${depPercent}%"
                 title="Dependencies: ${depLoc.toLocaleString()} LoC (${depPercent.toFixed(1)}%)">
            </div>` : ''}
        `;
        legendContent = `
            <span class="legend-local">${projectPercent.toFixed(0)}% local</span>
            ${depPercent > 0 ? `<span class="legend-deps">${depPercent.toFixed(0)}% deps</span>` : '<span class="legend-no-deps">No dependencies</span>'}
        `;
    } else {
        // Only project LoC (deps not analyzed)
        barContent = `
            <div class="repo-bar-segment repo-bar-local"
                 style="width: 100%"
                 title="Local: ${projectLoc.toLocaleString()} LoC">
            </div>
        `;
        legendContent = `<span class="legend-local">${projectLoc.toLocaleString()} LoC</span><span class="legend-not-analyzed">Dependencies not analyzed</span>`;
    }

    bar.innerHTML = `
        <div class="repo-bar-label">
            <span class="repo-bar-name">${repo.full_name || `${repo.owner}/${repo.name}`}</span>
            <span class="repo-bar-meta">
                ${repo.language ? `<span class="lang-badge">${repo.language}</span>` : ''}
                <span class="loc-badge">${projectLoc.toLocaleString()} LoC</span>
            </span>
        </div>
        <div class="repo-bar-chart">
            ${barContent}
        </div>
        <div class="repo-bar-legend">
            ${legendContent}
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
