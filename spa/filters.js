// Pure filtering functions for repository data
// Extracted for testability — no DOM or global state dependencies

function deduplicateRepos(dimensions) {
    const reposMap = new Map();

    dimensions.forEach(dimension => {
        if (dimension.repos && Array.isArray(dimension.repos)) {
            dimension.repos.forEach(repo => {
                const key = `${repo.owner}/${repo.name}`;

                let source = dimension.id;
                if (dimension.type === 'trending') {
                    source = `trending-${dimension.timeframe}`;
                } else if (dimension.type === 'search') {
                    source = 'search';
                } else if (dimension.type === 'github-ranking') {
                    source = `github-ranking-${dimension.category}`;
                } else if (dimension.type === 'tracked') {
                    source = 'tracked';
                }

                if (reposMap.has(key)) {
                    reposMap.get(key).sources.push(source);
                } else {
                    reposMap.set(key, {
                        ...repo,
                        sources: [source]
                    });
                }
            });
        }
    });

    return Array.from(reposMap.values());
}

function filterByTrending(repos, selectedTrending) {
    const trendingSources = selectedTrending.map(t => `trending-${t}`);
    return repos.filter(repo => {
        const hasNonTrendingSource = repo.sources.some(s => !s.startsWith('trending-'));
        if (hasNonTrendingSource) return true;
        if (selectedTrending.length === 0) return false;
        return repo.sources.some(s => trendingSources.includes(s));
    });
}

function filterByStars(repos, selectedRanges) {
    if (selectedRanges.length === 0) return [];
    return repos.filter(repo => {
        const stars = repo.stars || 0;
        return selectedRanges.some(range => {
            if (range === '0-100') return stars >= 0 && stars < 100;
            if (range === '100-1000') return stars >= 100 && stars < 1000;
            if (range === '1000-10000') return stars >= 1000 && stars < 10000;
            if (range === '10000+') return stars >= 10000;
            return false;
        });
    });
}

function filterByLanguage(repos, selectedLanguages) {
    if (selectedLanguages.length === 0) return [];
    return repos.filter(repo =>
        selectedLanguages.includes(repo.language) || !repo.language
    );
}

function filterBySearch(repos, query) {
    if (!query) return repos;
    const lowerQuery = query.toLowerCase();
    return repos.filter(repo =>
        (repo.full_name || '').toLowerCase().includes(lowerQuery) ||
        (repo.description || '').toLowerCase().includes(lowerQuery) ||
        (repo.language || '').toLowerCase().includes(lowerQuery)
    );
}

function filterByAiTools(repos, selectedTools) {
    if (selectedTools.length === 0) return repos;
    if (selectedTools.includes('any')) {
        return repos.filter(repo =>
            repo.ai_tools && repo.ai_tools.length > 0
        );
    }
    return repos.filter(repo =>
        repo.ai_tools && repo.ai_tools.some(tool =>
            selectedTools.includes(tool.toLowerCase())
        )
    );
}

function applyAllFilters(repos, filters) {
    let filtered = repos;
    filtered = filterByTrending(filtered, filters.trending);
    filtered = filterByStars(filtered, filters.stars);
    filtered = filterByLanguage(filtered, filters.languages);
    filtered = filterBySearch(filtered, filters.searchQuery);
    filtered = filterByAiTools(filtered, filters.aiTools);
    return filtered;
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        deduplicateRepos,
        filterByTrending,
        filterByStars,
        filterByLanguage,
        filterBySearch,
        filterByAiTools,
        applyAllFilters
    };
}
