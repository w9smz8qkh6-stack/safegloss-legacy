/**
 * Client-Side Form Validation
 * Provides real-time validation feedback for forms
 */

(function() {
  'use strict';

  // Bootstrap 5 validation integration
  function setupBootstrapValidation() {
    // Fetch all forms we want to apply custom Bootstrap validation to
    const forms = document.querySelectorAll('.needs-validation');

    Array.from(forms).forEach(form => {
      form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
          event.preventDefault();
          event.stopPropagation();
        }
        form.classList.add('was-validated');
      }, false);
    });
  }

  // Real-time validation on input
  function setupRealtimeValidation() {
    // Text inputs
    document.querySelectorAll('input[required], textarea[required]').forEach(input => {
      input.addEventListener('blur', function() {
        validateField(this);
      });

      input.addEventListener('input', function() {
        if (this.classList.contains('is-invalid')) {
          validateField(this);
        }
      });
    });

    // Select elements
    document.querySelectorAll('select[required]').forEach(select => {
      select.addEventListener('change', function() {
        validateField(this);
      });
    });
  }

  function validateField(field) {
    const isValid = field.checkValidity();

    // Clear previous state
    field.classList.remove('is-valid', 'is-invalid');

    if (field.value.trim() === '' && field.required) {
      field.classList.add('is-invalid');
      showFeedback(field, 'This field is required.', false);
    } else if (!isValid) {
      field.classList.add('is-invalid');
      showFeedback(field, getValidationMessage(field), false);
    } else if (field.value.trim() !== '') {
      field.classList.add('is-valid');
      removeFeedback(field);
    }

    return isValid;
  }

  function getValidationMessage(field) {
    if (field.validity.valueMissing) {
      return 'This field is required.';
    }
    if (field.validity.typeMismatch) {
      if (field.type === 'email') {
        return 'Please enter a valid email address.';
      }
      if (field.type === 'url') {
        return 'Please enter a valid URL.';
      }
      return 'Please enter a valid value.';
    }
    if (field.validity.tooShort) {
      return `Please enter at least ${field.minLength} characters.`;
    }
    if (field.validity.tooLong) {
      return `Please enter no more than ${field.maxLength} characters.`;
    }
    if (field.validity.patternMismatch) {
      return field.title || 'Please match the requested format.';
    }
    if (field.validity.rangeUnderflow) {
      return `Value must be at least ${field.min}.`;
    }
    if (field.validity.rangeOverflow) {
      return `Value must be no more than ${field.max}.`;
    }
    return field.validationMessage;
  }

  function showFeedback(field, message, isValid) {
    let feedback = field.nextElementSibling;

    if (!feedback || (!feedback.classList.contains('invalid-feedback') && !feedback.classList.contains('valid-feedback'))) {
      feedback = document.createElement('div');
      field.parentNode.insertBefore(feedback, field.nextSibling);
    }

    feedback.className = isValid ? 'valid-feedback' : 'invalid-feedback';
    feedback.textContent = message;
    feedback.style.display = 'block';
  }

  function removeFeedback(field) {
    const feedback = field.nextElementSibling;
    if (feedback && (feedback.classList.contains('invalid-feedback') || feedback.classList.contains('valid-feedback'))) {
      feedback.style.display = 'none';
    }
  }

  // Password confirmation validation
  function setupPasswordConfirmation() {
    const password = document.querySelector('input[name="password1"], input[name="password"]');
    const confirm = document.querySelector('input[name="password2"], input[name="password_confirm"]');

    if (password && confirm) {
      confirm.addEventListener('input', function() {
        if (this.value !== password.value) {
          this.setCustomValidity('Passwords do not match.');
          this.classList.add('is-invalid');
          showFeedback(this, 'Passwords do not match.', false);
        } else {
          this.setCustomValidity('');
          this.classList.remove('is-invalid');
          this.classList.add('is-valid');
          removeFeedback(this);
        }
      });
    }
  }

  // Character counter for textareas
  function setupCharacterCounters() {
    document.querySelectorAll('textarea[maxlength]').forEach(textarea => {
      const maxLength = parseInt(textarea.getAttribute('maxlength'));
      const counterId = `counter-${Math.random().toString(36).substr(2, 9)}`;

      const counter = document.createElement('small');
      counter.id = counterId;
      counter.className = 'text-muted d-block text-end';
      counter.textContent = `0 / ${maxLength}`;
      textarea.parentNode.insertBefore(counter, textarea.nextSibling);

      textarea.addEventListener('input', function() {
        const remaining = maxLength - this.value.length;
        counter.textContent = `${this.value.length} / ${maxLength}`;
        counter.classList.toggle('text-danger', remaining < 20);
      });
    });
  }

  // Initialize
  function init() {
    setupBootstrapValidation();
    setupRealtimeValidation();
    setupPasswordConfirmation();
    setupCharacterCounters();
  }

  // Auto-init when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
