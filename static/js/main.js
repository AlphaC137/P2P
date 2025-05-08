/**
 * Main JavaScript file for P2P Lending Platform
 * Created: May 2025
 */

// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Enable all tooltips
    var tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    if (tooltips.length) {
        tooltips.forEach(function(tooltip) {
            new bootstrap.Tooltip(tooltip);
        });
    }

    // Enable all popovers
    var popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
    if (popovers.length) {
        popovers.forEach(function(popover) {
            new bootstrap.Popover(popover);
        });
    }

    // Add animation to elements with fade-in class
    const fadeElems = document.querySelectorAll('.fade-in');
    if (fadeElems.length) {
        fadeElems.forEach(function(elem) {
            elem.style.opacity = '1';
            elem.style.transform = 'translateY(0)';
        });
    }

    // Handle loan filter form
    const loanFilterForm = document.getElementById('loan-filter-form');
    if (loanFilterForm) {
        loanFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            // Build the query string
            const formData = new FormData(loanFilterForm);
            const queryParams = new URLSearchParams(formData).toString();
            // Redirect with filters
            window.location.href = `${window.location.pathname}?${queryParams}`;
        });
    }

    // Interactive loan calculator
    const loanCalculator = document.getElementById('loan-calculator');
    if (loanCalculator) {
        const amountInput = document.getElementById('calc-amount');
        const termInput = document.getElementById('calc-term');
        const interestInput = document.getElementById('calc-interest');
        const monthlyPayment = document.getElementById('calc-monthly-payment');
        const totalInterest = document.getElementById('calc-total-interest');
        const totalPayment = document.getElementById('calc-total-payment');

        // Function to calculate loan payment
        function calculateLoan() {
            const principal = parseFloat(amountInput.value);
            const interestRate = parseFloat(interestInput.value) / 100 / 12;
            const termMonths = parseFloat(termInput.value);

            if (principal > 0 && interestRate > 0 && termMonths > 0) {
                const monthlyAmount = principal * interestRate * Math.pow(1 + interestRate, termMonths) / (Math.pow(1 + interestRate, termMonths) - 1);
                const totalAmount = monthlyAmount * termMonths;
                const interestAmount = totalAmount - principal;

                monthlyPayment.textContent = '$' + monthlyAmount.toFixed(2);
                totalInterest.textContent = '$' + interestAmount.toFixed(2);
                totalPayment.textContent = '$' + totalAmount.toFixed(2);
            }
        }

        // Add event listeners to calculator inputs
        [amountInput, termInput, interestInput].forEach(input => {
            if (input) {
                input.addEventListener('input', calculateLoan);
            }
        });

        // Initial calculation
        calculateLoan();
    }

    // Investment slider for loan detail page
    const investmentSlider = document.getElementById('investment-slider');
    if (investmentSlider) {
        const amountDisplay = document.getElementById('investment-amount-display');
        const amountInput = document.getElementById('investment-amount');
        
        investmentSlider.addEventListener('input', function() {
            const value = this.value;
            amountDisplay.textContent = '$' + parseFloat(value).toFixed(2);
            amountInput.value = value;
        });
    }

    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    if (alerts.length) {
        alerts.forEach(function(alert) {
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    }
});