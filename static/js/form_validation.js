/**
 * Form validation improvements for P2P Lending Platform
 */

document.addEventListener('DOMContentLoaded', function() {
    // Apply to all forms
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        // Add proper validation styles when submitting
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Find all invalid fields and add error message
                const invalidFields = form.querySelectorAll(':invalid');
                invalidFields.forEach(field => {
                    field.classList.add('is-invalid');
                    
                    // Create or update feedback message
                    let feedback = field.nextElementSibling;
                    if (!feedback || !feedback.classList.contains('invalid-feedback')) {
                        feedback = document.createElement('div');
                        feedback.classList.add('invalid-feedback');
                        field.parentNode.insertBefore(feedback, field.nextSibling);
                    }
                    
                    feedback.textContent = field.validationMessage || 'This field is invalid';
                });
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation as user types
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            input.addEventListener('input', function() {
                if (input.checkValidity()) {
                    input.classList.remove('is-invalid');
                    input.classList.add('is-valid');
                } else {
                    input.classList.remove('is-valid');
                    input.classList.add('is-invalid');
                }
            });
        });
    });

    // Fix numeric input fields for currency
    const numberInputs = document.querySelectorAll('input[type="number"]');
    numberInputs.forEach(input => {
        // Ensure proper step value for currency fields
        if (input.id.includes('amount') || 
            input.name.includes('amount') || 
            input.id.includes('payment') || 
            input.name.includes('payment')) {
            
            if (!input.hasAttribute('step')) {
                input.setAttribute('step', '0.01');
            }
            
            // Add minimum value if not set
            if (!input.hasAttribute('min')) {
                input.setAttribute('min', '0');
            }
        }
    });
});
