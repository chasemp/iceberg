/**
 * Jest setup file for frontend tests
 * Configures jsdom environment and testing utilities
 */

require('@testing-library/jest-dom');

// Mock fetch for tests
global.fetch = jest.fn();

// Reset mocks after each test
afterEach(() => {
  jest.clearAllMocks();
});
