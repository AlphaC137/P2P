/**
 * UI fixes for P2P Lending Platform
 */

// Process text nodes for currency formatting
function processTextNodes(node) {
    if (node.nodeType === Node.TEXT_NODE) {
        let content = node.textContent;
        let changed = false;
        
        // Replace R format with proper spacing
        if (content.match(/R\d+(\.\d+)?/)) {
            content = content.replace(/R(\d+(\.\d+)?)/g, "R $1");
            changed = true;
        }
        
        // Replace $ format (if erroneously used)
        if (content.match(/\$\d+(\.\d+)?/)) {
            content = content.replace(/\$(\d+(\.\d+)?)/g, "R $1");
            changed = true;
        }
        
        if (changed) {
            node.textContent = content;
        }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
        // Skip script and style elements
        if (node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
            Array.from(node.childNodes).forEach(processTextNodes);
        }
    }
}

// Initialize all UI fixes when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    fixCurrencyFormat();
});

// Fix currency format inconsistencies
function fixCurrencyFormat() {
    // Target specific elements that commonly have currency values
    const targetSelectors = [
        '.card-header h3', '.card-body h5', '.card-text',
        '.stat-value', '.loan-amount', '.monthly-payment',
        '.price', '.loan-detail'
    ];
    
    // Target specific elements
    targetSelectors.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            processTextNodes(el);
        });
    });
    
    // Process text elements containing currency values
    processElementsWithCurrencyValues();
    
    // Fix formatting in badges with currency
    processBadgesWithCurrency();
}

// Process elements that might contain currency values (text elements)
function processElementsWithCurrencyValues() {
    // Find elements with text-success class that might contain currency
    document.querySelectorAll('.text-success').forEach(el => {
        if (el.textContent.includes('R')) {
            processTextNodes(el);
        }
    });
    
    // Find elements with text-danger class that might contain currency
    document.querySelectorAll('.text-danger').forEach(el => {
        if (el.textContent.includes('R')) {
            processTextNodes(el);
        }
    });
    
    // Find elements with Badge class that might contain currency
    document.querySelectorAll('.badge.bg-success').forEach(el => {
        if (el.textContent.includes('R')) {
            processTextNodes(el);
        }
    });
    
    // Find elements with currency-related words
    const currencyTextElements = Array.from(document.querySelectorAll('*')).filter(el => {
        const text = el.textContent.toLowerCase();
        return (text.includes('balance') || text.includes('amount') || 
                text.includes('payment') || text.includes('loan')) &&
               (text.includes('r') || text.includes('$'));
    });
    
    currencyTextElements.forEach(el => {
        processTextNodes(el);
    });
}

// Process badges that might contain currency values
function processBadgesWithCurrency() {
    document.querySelectorAll('.badge').forEach(badge => {
        const content = badge.textContent;
        if (content.includes('R') && content.match(/R\d+/)) {
            badge.textContent = content.replace(/R(\d+(\.\d+)?)/, "R $1");
        }
    });
}

// Ensure consistent form field padding and appearance
function fixFormFields() {
    const formControls = document.querySelectorAll('.form-control, .form-select');
    formControls.forEach(field => {
        if (!field.classList.contains('is-invalid') && !field.classList.contains('is-valid')) {
            field.style.paddingTop = '0.6rem';
            field.style.paddingBottom = '0.6rem';
        }
    });
}

// Fix any icon alignment issues
function fixIconAlignment() {
    const icons = document.querySelectorAll('.fas, .fab, .far');
    icons.forEach(icon => {
        const parent = icon.parentElement;
        if (parent && parent.style.display !== 'flex') {
            parent.style.display = 'inline-flex';
            parent.style.alignItems = 'center';
        }
    });
}

// Fix any responsive table issues
function fixResponsiveTables() {
    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
        const parent = table.parentElement;
        if (!parent.classList.contains('table-responsive')) {
            // Wrap the table in a responsive container if it isn't already
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            parent.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
}

// Make sure we don't register multiple identical event listeners
if (window.uiFixesInitialized !== true) {
    // Run all fixes when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        // Run all our fixes
        setTimeout(() => {
            fixCurrencyFormat();
            fixFormFields();
            fixIconAlignment();
            fixResponsiveTables();
        }, 100);
    });

    // Fix UI issues after dynamically loaded content
    window.addEventListener('load', function() {
        setTimeout(() => {
            fixCurrencyFormat();
        }, 500);
    });
    
    // Mark as initialized to prevent duplicate handlers
    window.uiFixesInitialized = true;
}
