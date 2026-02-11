const {
    deduplicateRepos,
    filterByTrending,
    filterByStars,
    filterByLanguage,
    filterBySearch,
    filterByAiTools,
    applyAllFilters
} = require('../../spa/filters.js');

function makeRepo(overrides) {
    return {
        owner: 'test',
        name: 'repo',
        stars: 5000,
        language: 'Python',
        sources: ['search'],
        ...overrides
    };
}

describe('deduplicateRepos', () => {
    test('assigns source based on dimension type', () => {
        const dimensions = [
            { type: 'trending', timeframe: 'monthly', repos: [{ owner: 'a', name: 'b', stars: 100 }] },
            { type: 'search', id: 'search-1', repos: [{ owner: 'c', name: 'd', stars: 200 }] },
            { type: 'github-ranking', category: 'python', id: 'rank-py', repos: [{ owner: 'e', name: 'f', stars: 300 }] },
        ];

        const repos = deduplicateRepos(dimensions);

        expect(repos).toHaveLength(3);
        expect(repos.find(r => r.owner === 'a').sources).toEqual(['trending-monthly']);
        expect(repos.find(r => r.owner === 'c').sources).toEqual(['search']);
        expect(repos.find(r => r.owner === 'e').sources).toEqual(['github-ranking-python']);
    });

    test('accumulates multiple sources for the same repo', () => {
        const dimensions = [
            { type: 'github-ranking', category: 'python', id: 'rank-py', repos: [{ owner: 'a', name: 'b', stars: 100 }] },
            { type: 'trending', timeframe: 'monthly', repos: [{ owner: 'a', name: 'b', stars: 100 }] },
            { type: 'search', id: 'search-1', repos: [{ owner: 'a', name: 'b', stars: 100 }] },
        ];

        const repos = deduplicateRepos(dimensions);

        expect(repos).toHaveLength(1);
        expect(repos[0].sources).toEqual(['github-ranking-python', 'trending-monthly', 'search']);
    });

    test('deduplicates by owner/name key', () => {
        const dimensions = [
            { type: 'github-ranking', category: 'top-100-stars', id: 'top-stars', repos: [
                { owner: 'a', name: 'b', stars: 100 },
                { owner: 'c', name: 'd', stars: 200 },
            ]},
            { type: 'github-ranking', category: 'python', id: 'rank-py', repos: [
                { owner: 'a', name: 'b', stars: 100 },
            ]},
        ];

        const repos = deduplicateRepos(dimensions);

        expect(repos).toHaveLength(2);
        expect(repos.find(r => r.owner === 'a').sources).toEqual([
            'github-ranking-top-100-stars',
            'github-ranking-python'
        ]);
    });

    test('skips dimensions without repos array', () => {
        const dimensions = [
            { type: 'trending', timeframe: 'monthly' },
            { type: 'search', id: 's', repos: [{ owner: 'a', name: 'b', stars: 1 }] },
        ];

        expect(deduplicateRepos(dimensions)).toHaveLength(1);
    });
});

describe('filterByTrending', () => {
    test('repos with non-trending sources always pass through', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['github-ranking-python'] }),
            makeRepo({ owner: 'b', sources: ['search'] }),
            makeRepo({ owner: 'c', sources: ['github-ranking-top-100-stars', 'search'] }),
        ];

        const result = filterByTrending(repos, ['monthly']);
        expect(result).toHaveLength(3);
    });

    test('repos with non-trending sources pass through even when no trending selected', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['github-ranking-python'] }),
            makeRepo({ owner: 'b', sources: ['search'] }),
        ];

        const result = filterByTrending(repos, []);
        expect(result).toHaveLength(2);
    });

    test('trending-only repos are gated by selected timeframes', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['trending-monthly'] }),
            makeRepo({ owner: 'b', sources: ['search'] }),
        ];

        const result = filterByTrending(repos, ['monthly']);
        expect(result).toHaveLength(2);
        expect(result[0].owner).toBe('a');
    });

    test('trending-only repos are excluded when no trending selected', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['trending-monthly'] }),
            makeRepo({ owner: 'b', sources: ['trending-monthly'] }),
        ];

        const result = filterByTrending(repos, []);
        expect(result).toHaveLength(0);
    });

    test('multi-source repos with trending + ranking pass through regardless of trending selection', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['trending-monthly', 'github-ranking-python'] }),
        ];

        const result = filterByTrending(repos, ['monthly']);
        expect(result).toHaveLength(1);
    });

    test('monthly trending repos pass with monthly selected', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['trending-monthly'] }),
            makeRepo({ owner: 'b', sources: ['trending-monthly'] }),
        ];

        const result = filterByTrending(repos, ['monthly']);
        expect(result).toHaveLength(2);
    });
});

describe('filterByStars', () => {
    test('filters repos into correct star ranges', () => {
        const repos = [
            makeRepo({ owner: 'a', stars: 50 }),
            makeRepo({ owner: 'b', stars: 500 }),
            makeRepo({ owner: 'c', stars: 5000 }),
            makeRepo({ owner: 'd', stars: 50000 }),
        ];

        expect(filterByStars(repos, ['0-100'])).toHaveLength(1);
        expect(filterByStars(repos, ['0-100'])[0].owner).toBe('a');

        expect(filterByStars(repos, ['100-1000'])).toHaveLength(1);
        expect(filterByStars(repos, ['100-1000'])[0].owner).toBe('b');

        expect(filterByStars(repos, ['1000-10000'])).toHaveLength(1);
        expect(filterByStars(repos, ['1000-10000'])[0].owner).toBe('c');

        expect(filterByStars(repos, ['10000+'])).toHaveLength(1);
        expect(filterByStars(repos, ['10000+'])[0].owner).toBe('d');
    });

    test('multiple ranges combine with OR logic', () => {
        const repos = [
            makeRepo({ owner: 'a', stars: 50 }),
            makeRepo({ owner: 'b', stars: 500 }),
            makeRepo({ owner: 'c', stars: 5000 }),
        ];

        const result = filterByStars(repos, ['0-100', '1000-10000']);
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'c']);
    });

    test('returns empty array when no ranges selected', () => {
        const repos = [makeRepo({ stars: 5000 })];
        expect(filterByStars(repos, [])).toEqual([]);
    });

    test('all ranges selected returns all repos', () => {
        const repos = [
            makeRepo({ owner: 'a', stars: 50 }),
            makeRepo({ owner: 'b', stars: 500 }),
            makeRepo({ owner: 'c', stars: 5000 }),
            makeRepo({ owner: 'd', stars: 50000 }),
        ];

        const result = filterByStars(repos, ['0-100', '100-1000', '1000-10000', '10000+']);
        expect(result).toHaveLength(4);
    });

    test('repos without stars default to 0', () => {
        const repos = [makeRepo({ stars: undefined })];
        expect(filterByStars(repos, ['0-100'])).toHaveLength(1);
        expect(filterByStars(repos, ['100-1000'])).toHaveLength(0);
    });

    test('star range boundaries are exclusive on the upper end', () => {
        const repos = [
            makeRepo({ owner: 'a', stars: 100 }),
            makeRepo({ owner: 'b', stars: 1000 }),
            makeRepo({ owner: 'c', stars: 10000 }),
        ];

        expect(filterByStars(repos, ['0-100'])).toHaveLength(0);
        expect(filterByStars(repos, ['100-1000'])).toHaveLength(1);
        expect(filterByStars(repos, ['100-1000'])[0].owner).toBe('a');

        expect(filterByStars(repos, ['1000-10000'])).toHaveLength(1);
        expect(filterByStars(repos, ['1000-10000'])[0].owner).toBe('b');

        expect(filterByStars(repos, ['10000+'])).toHaveLength(1);
        expect(filterByStars(repos, ['10000+'])[0].owner).toBe('c');
    });
});

describe('filterByLanguage', () => {
    test('keeps repos matching selected languages', () => {
        const repos = [
            makeRepo({ owner: 'a', language: 'Python' }),
            makeRepo({ owner: 'b', language: 'Rust' }),
            makeRepo({ owner: 'c', language: 'Go' }),
        ];

        const result = filterByLanguage(repos, ['Python', 'Rust']);
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'b']);
    });

    test('repos without a language pass through when any language is selected', () => {
        const repos = [
            makeRepo({ owner: 'a', language: 'Python' }),
            makeRepo({ owner: 'b', language: null }),
            makeRepo({ owner: 'c', language: undefined }),
        ];

        const result = filterByLanguage(repos, ['Python']);
        expect(result).toHaveLength(3);
    });

    test('returns empty when no languages selected', () => {
        const repos = [makeRepo({ language: 'Python' })];
        expect(filterByLanguage(repos, [])).toEqual([]);
    });
});

describe('filterBySearch', () => {
    test('matches against full_name', () => {
        const repos = [
            makeRepo({ full_name: 'facebook/react', description: 'UI library' }),
            makeRepo({ full_name: 'vuejs/vue', description: 'Progressive framework' }),
        ];

        const result = filterBySearch(repos, 'react');
        expect(result).toHaveLength(1);
        expect(result[0].full_name).toBe('facebook/react');
    });

    test('matches against description', () => {
        const repos = [
            makeRepo({ full_name: 'a/b', description: 'A blazing fast bundler' }),
            makeRepo({ full_name: 'c/d', description: 'A test framework' }),
        ];

        const result = filterBySearch(repos, 'bundler');
        expect(result).toHaveLength(1);
    });

    test('matches against language', () => {
        const repos = [
            makeRepo({ full_name: 'a/b', language: 'TypeScript' }),
            makeRepo({ full_name: 'c/d', language: 'Python' }),
        ];

        const result = filterBySearch(repos, 'typescript');
        expect(result).toHaveLength(1);
    });

    test('is case-insensitive', () => {
        const repos = [makeRepo({ full_name: 'Facebook/React' })];
        expect(filterBySearch(repos, 'REACT')).toHaveLength(1);
        expect(filterBySearch(repos, 'react')).toHaveLength(1);
    });

    test('returns all repos when query is empty', () => {
        const repos = [makeRepo(), makeRepo({ owner: 'b' })];
        expect(filterBySearch(repos, '')).toHaveLength(2);
        expect(filterBySearch(repos, null)).toHaveLength(2);
        expect(filterBySearch(repos, undefined)).toHaveLength(2);
    });
});

describe('filterByAiTools', () => {
    test('returns all repos when no tools selected (optional filter)', () => {
        const repos = [
            makeRepo({ ai_tools: ['copilot'] }),
            makeRepo({ ai_tools: [] }),
            makeRepo({ ai_tools: null }),
        ];

        expect(filterByAiTools(repos, [])).toHaveLength(3);
    });

    test('"any" selects all repos with at least one AI tool', () => {
        const repos = [
            makeRepo({ owner: 'a', ai_tools: ['copilot'] }),
            makeRepo({ owner: 'b', ai_tools: [] }),
            makeRepo({ owner: 'c', ai_tools: null }),
            makeRepo({ owner: 'd', ai_tools: ['cursor', 'copilot'] }),
        ];

        const result = filterByAiTools(repos, ['any']);
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'd']);
    });

    test('filters by specific tool name (case-insensitive)', () => {
        const repos = [
            makeRepo({ owner: 'a', ai_tools: ['Copilot'] }),
            makeRepo({ owner: 'b', ai_tools: ['Cursor'] }),
            makeRepo({ owner: 'c', ai_tools: ['Copilot', 'Cursor'] }),
        ];

        const result = filterByAiTools(repos, ['copilot']);
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'c']);
    });

    test('multiple tool selections combine with OR logic', () => {
        const repos = [
            makeRepo({ owner: 'a', ai_tools: ['Copilot'] }),
            makeRepo({ owner: 'b', ai_tools: ['Cursor'] }),
            makeRepo({ owner: 'c', ai_tools: ['Claude'] }),
        ];

        const result = filterByAiTools(repos, ['copilot', 'cursor']);
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'b']);
    });
});

describe('applyAllFilters', () => {
    test('applies all filters with AND logic', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['trending-monthly'], stars: 5000, language: 'Python' }),
            makeRepo({ owner: 'b', sources: ['trending-monthly'], stars: 500, language: 'Python' }),
            makeRepo({ owner: 'c', sources: ['github-ranking-python'], stars: 5000, language: 'Rust' }),
            makeRepo({ owner: 'd', sources: ['github-ranking-rust'], stars: 50000, language: 'Rust' }),
        ];

        const result = applyAllFilters(repos, {
            trending: ['monthly'],
            stars: ['1000-10000'],
            languages: ['Python', 'Rust'],
            searchQuery: '',
            aiTools: []
        });

        // a: trending-monthly (only trending, passes monthly) + 5000 stars (passes 1K-10K) + Python (passes) = YES
        // b: trending-monthly (only trending, passes monthly) + 500 stars (fails 1K-10K) = NO
        // c: ranking (non-trending, passes) + 5000 (passes 1K-10K) + Rust (passes) = YES
        // d: ranking (non-trending, passes) + 50000 (fails 1K-10K) = NO
        expect(result).toHaveLength(2);
        expect(result.map(r => r.owner)).toEqual(['a', 'c']);
    });

    test('default filter state passes through all repos with matching languages', () => {
        const repos = [
            makeRepo({ owner: 'a', sources: ['github-ranking-python'], stars: 50000, language: 'Python' }),
            makeRepo({ owner: 'b', sources: ['search'], stars: 500, language: 'Rust' }),
            makeRepo({ owner: 'c', sources: ['trending-monthly'], stars: 5000, language: 'Go' }),
        ];

        const result = applyAllFilters(repos, {
            trending: ['monthly'],
            stars: ['0-100', '100-1000', '1000-10000', '10000+'],
            languages: ['Python', 'Rust', 'Go'],
            searchQuery: '',
            aiTools: []
        });

        expect(result).toHaveLength(3);
    });

    test('search narrows results across all other filters', () => {
        const repos = [
            makeRepo({ owner: 'a', full_name: 'a/react', sources: ['search'], language: 'JavaScript' }),
            makeRepo({ owner: 'b', full_name: 'b/vue', sources: ['search'], language: 'JavaScript' }),
        ];

        const result = applyAllFilters(repos, {
            trending: ['monthly'],
            stars: ['0-100', '100-1000', '1000-10000', '10000+'],
            languages: ['JavaScript'],
            searchQuery: 'react',
            aiTools: []
        });

        expect(result).toHaveLength(1);
        expect(result[0].owner).toBe('a');
    });
});
