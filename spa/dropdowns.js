// Multiselect Dropdown Module
// This module provides the logic for custom multiselect dropdown components

/**
 * Initialize a multiselect dropdown
 * @param {HTMLElement} dropdownElement - The dropdown container element
 * @param {string} filterType - Type of filter ('trending' or 'stars')
 * @param {Function} updateCallback - Callback function when selection changes
 */
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

/**
 * Update the dropdown button text based on selection count
 * @param {HTMLElement} dropdownElement - The dropdown container element
 * @param {string} filterType - Type of filter ('trending' or 'stars')
 */
function updateDropdownButton(dropdownElement, filterType) {
    const button = dropdownElement.querySelector('.multiselect-button');
    const label = button.querySelector('.multiselect-label');
    const menu = dropdownElement.querySelector('.multiselect-menu');
    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    const count = checkboxes.length;

    if (count === 0) {
        const placeholderText = filterType === 'trending'
            ? 'Select trending timeframes'
            : 'Select star ranges';
        label.textContent = placeholderText;
    } else {
        label.textContent = `${count} selected`;
    }
}

/**
 * Get selected values from a dropdown
 * @param {string} testId - The data-testid of the dropdown
 * @returns {string[]} Array of selected values
 */
function getSelectedValues(testId) {
    const menu = document.querySelector(`[data-testid="${testId}-menu"]`);
    if (!menu) return [];

    const checkboxes = menu.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

/**
 * Setup click-outside-to-close behavior for all dropdowns
 */
function setupClickOutsideHandler() {
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.multiselect-dropdown')) {
            document.querySelectorAll('.multiselect-menu.open').forEach(menu => {
                menu.classList.remove('open');
            });
        }
    });
}

// Export for use in tests (CommonJS for Jest)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        setupDropdown,
        updateDropdownButton,
        getSelectedValues,
        setupClickOutsideHandler
    };
}
