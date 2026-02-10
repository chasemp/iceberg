/**
 * Tests for multiselect dropdown components
 *
 * These tests verify the behavior of the trending and stars multiselect dropdowns
 * that replace the dimension tile cards.
 */

const { screen, fireEvent } = require('@testing-library/dom');
require('@testing-library/jest-dom');
const {
  setupDropdown,
  updateDropdownButton,
  getSelectedValues,
  setupClickOutsideHandler
} = require('../../spa/dropdowns.js');

describe('Multiselect Dropdowns', () => {
  let container;

  beforeEach(() => {
    // Create a clean DOM for each test
    container = document.createElement('div');
    container.innerHTML = `
      <div id="discovery-tab">
        <div id="dimensions-filters" class="multiselect-filters">
          <!-- Trending multiselect dropdown -->
          <div class="multiselect-dropdown" data-testid="trending-dropdown">
            <button class="multiselect-button" data-testid="trending-dropdown-button">
              <span class="multiselect-label">Select trending timeframes</span>
              <span class="multiselect-arrow">▼</span>
            </button>
            <div class="multiselect-menu" data-testid="trending-dropdown-menu">
              <label class="multiselect-option">
                <input type="checkbox" value="daily" />
                <span>Daily</span>
              </label>
              <label class="multiselect-option">
                <input type="checkbox" value="weekly" />
                <span>Weekly</span>
              </label>
              <label class="multiselect-option">
                <input type="checkbox" value="monthly" />
                <span>Monthly</span>
              </label>
            </div>
          </div>

          <!-- Stars multiselect dropdown -->
          <div class="multiselect-dropdown" data-testid="stars-dropdown">
            <button class="multiselect-button" data-testid="stars-dropdown-button">
              <span class="multiselect-label">Select star ranges</span>
              <span class="multiselect-arrow">▼</span>
            </button>
            <div class="multiselect-menu" data-testid="stars-dropdown-menu">
              <label class="multiselect-option">
                <input type="checkbox" value="0-100" />
                <span>0-100 stars</span>
              </label>
              <label class="multiselect-option">
                <input type="checkbox" value="100-1000" />
                <span>100-1K stars</span>
              </label>
              <label class="multiselect-option">
                <input type="checkbox" value="1000-10000" />
                <span>1K-10K stars</span>
              </label>
              <label class="multiselect-option">
                <input type="checkbox" value="10000+" />
                <span>10K+ stars</span>
              </label>
            </div>
          </div>
        </div>
        <div id="repositories-list" data-testid="repositories-list"></div>
      </div>
    `;
    document.body.appendChild(container);

    // Initialize dropdowns with mock callbacks
    const mockCallback = jest.fn();
    const trendingDropdown = container.querySelector('[data-testid="trending-dropdown"]');
    const starsDropdown = container.querySelector('[data-testid="stars-dropdown"]');

    if (trendingDropdown) {
      setupDropdown(trendingDropdown, 'trending', mockCallback);
    }

    if (starsDropdown) {
      setupDropdown(starsDropdown, 'stars', mockCallback);
    }

    setupClickOutsideHandler();
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  describe('Trending Dropdown', () => {
    test('renders trending dropdown with daily, weekly, and monthly options', () => {
      // This test will fail until we implement the dropdown
      const dropdown = screen.queryByTestId('trending-dropdown');
      expect(dropdown).toBeInTheDocument();

      // Verify all three trending options are present
      expect(screen.queryByText('Daily')).toBeInTheDocument();
      expect(screen.queryByText('Weekly')).toBeInTheDocument();
      expect(screen.queryByText('Monthly')).toBeInTheDocument();
    });

    test('allows multiple trending timeframes to be selected', () => {
      const dropdownButton = screen.getByTestId('trending-dropdown-button');

      // Open dropdown
      fireEvent.click(dropdownButton);

      // Select daily and weekly
      const dailyCheckbox = screen.getByLabelText('Daily');
      const weeklyCheckbox = screen.getByLabelText('Weekly');

      fireEvent.click(dailyCheckbox);
      fireEvent.click(weeklyCheckbox);

      // Both should be checked
      expect(dailyCheckbox).toBeChecked();
      expect(weeklyCheckbox).toBeChecked();
    });

    test('displays selected count in dropdown button', () => {
      const dropdownButton = screen.getByTestId('trending-dropdown-button');

      // Initially shows placeholder text
      expect(dropdownButton).toHaveTextContent('Select trending timeframes');

      // After selecting one option
      fireEvent.click(dropdownButton);

      const dailyCheckbox = screen.getByLabelText('Daily');
      fireEvent.click(dailyCheckbox);

      // Should show count
      expect(dropdownButton).toHaveTextContent('1 selected');

      // After selecting two options
      const weeklyCheckbox = screen.getByLabelText('Weekly');
      fireEvent.click(weeklyCheckbox);

      expect(dropdownButton).toHaveTextContent('2 selected');
    });

    test('closes dropdown when clicking outside', () => {
      const dropdownButton = screen.getByTestId('trending-dropdown-button');
      const dropdownMenu = screen.getByTestId('trending-dropdown-menu');

      // Open dropdown
      fireEvent.click(dropdownButton);
      expect(dropdownMenu).toHaveClass('open');

      // Click outside
      fireEvent.click(document.body);
      expect(dropdownMenu).not.toHaveClass('open');
    });
  });

  describe('Stars Dropdown', () => {
    test('renders stars dropdown with star range options', () => {
      const dropdown = screen.queryByTestId('stars-dropdown');
      expect(dropdown).toBeInTheDocument();

      // Verify star range options are present
      expect(screen.queryByText('0-100 stars')).toBeInTheDocument();
      expect(screen.queryByText('100-1K stars')).toBeInTheDocument();
      expect(screen.queryByText('1K-10K stars')).toBeInTheDocument();
      expect(screen.queryByText('10K+ stars')).toBeInTheDocument();
    });

    test('allows multiple star ranges to be selected', () => {
      const dropdown = screen.getByTestId('stars-dropdown');

      // Open dropdown
      fireEvent.click(dropdown);

      // Select two ranges
      const range1 = screen.getByLabelText('100-1K stars');
      const range2 = screen.getByLabelText('1K-10K stars');

      fireEvent.click(range1);
      fireEvent.click(range2);

      // Both should be checked
      expect(range1).toBeChecked();
      expect(range2).toBeChecked();
    });

    test('displays selected count in dropdown button', () => {
      const dropdownButton = screen.getByTestId('stars-dropdown-button');

      // Initially shows placeholder text
      expect(dropdownButton).toHaveTextContent('Select star ranges');

      // After selecting one option
      fireEvent.click(dropdownButton);

      const range = screen.getByLabelText('1K-10K stars');
      fireEvent.click(range);

      // Should show count
      expect(dropdownButton).toHaveTextContent('1 selected');
    });
  });

});
