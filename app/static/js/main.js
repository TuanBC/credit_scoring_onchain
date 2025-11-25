/**
 * OnChain Credit Scoring - Main JavaScript
 * Modern UI interactions and form handling
 */

(function() {
  'use strict';

  // ========== Constants ==========
  const ADDRESS_LENGTH = 42;
  const HEX_PATTERN = /^[0-9a-fA-F]+$/;

  // ========== Theme Management ==========
  const ThemeManager = {
    init() {
      const savedTheme = localStorage.getItem('theme') || 'dark';
      this.setTheme(savedTheme);
      this.bindEvents();
    },

    setTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      localStorage.setItem('theme', theme);
    },

    toggle() {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      this.setTheme(newTheme);
    },

    bindEvents() {
      const toggleBtn = document.querySelector('.theme-toggle');
      if (toggleBtn) {
        toggleBtn.addEventListener('click', () => this.toggle());
      }
    }
  };

  // ========== Mobile Navigation ==========
  const MobileNav = {
    init() {
      const toggleBtn = document.querySelector('.mobile-menu-toggle');
      const mobileNav = document.querySelector('.mobile-nav');
      
      if (toggleBtn && mobileNav) {
        toggleBtn.addEventListener('click', () => {
          mobileNav.classList.toggle('active');
          const icon = toggleBtn.querySelector('i');
          icon.classList.toggle('fa-bars');
          icon.classList.toggle('fa-times');
        });
      }
    }
  };

  // ========== Address Validation ==========
  const AddressValidator = {
    normalize(value) {
      value = value.trim();
      
      // Auto-prefix with 0x if missing
      if (!value.startsWith('0x') && value.length > 0) {
        value = '0x' + value;
      }
      
      return value;
    },

    validate(value) {
      const normalized = this.normalize(value);
      const hexPart = normalized.startsWith('0x') ? normalized.slice(2) : normalized;
      
      // Empty check
      if (normalized.length === 0) {
        return { valid: false, normalized, error: null };
      }
      
      // Validate hex characters
      if (hexPart.length > 0 && !HEX_PATTERN.test(hexPart)) {
        return { valid: false, normalized, error: 'Invalid hex characters detected' };
      }
      
      // Check length
      if (normalized.length > ADDRESS_LENGTH) {
        return { valid: false, normalized, error: 'Address is too long' };
      }
      
      if (normalized.length < ADDRESS_LENGTH && normalized.length > 2) {
        return { valid: false, normalized, error: `Address incomplete (${normalized.length}/${ADDRESS_LENGTH} characters)` };
      }
      
      if (normalized.length === ADDRESS_LENGTH) {
        return { valid: true, normalized: normalized.toLowerCase(), error: null };
      }
      
      return { valid: false, normalized, error: null };
    }
  };

  // ========== Form Handler ==========
  const FormHandler = {
    form: null,
    input: null,
    button: null,
    feedback: null,
    isSubmitting: false,  // Flag to prevent double submission

    init() {
      this.form = document.querySelector('.search-form, #scoreForm');
      if (!this.form) return;

      this.input = this.form.querySelector('#wallet_address');
      this.button = this.form.querySelector('.search-button, button[type="submit"]');
      this.feedback = this.form.querySelector('.search-feedback, #searchFeedback');
      this.isSubmitting = false;

      this.bindEvents();
    },

    bindEvents() {
      if (!this.input) return;

      // Real-time validation
      this.input.addEventListener('input', () => this.handleInput());
      this.input.addEventListener('blur', () => this.handleInput());
      
      // Paste handler
      this.input.addEventListener('paste', (e) => {
        setTimeout(() => this.handleInput(), 10);
      });

      // Form submission - use capture phase to ensure we handle it first
      if (this.form) {
        this.form.addEventListener('submit', (e) => this.handleSubmit(e), { capture: true });
      }
    },

    handleInput() {
      const result = AddressValidator.validate(this.input.value);
      this.input.value = result.normalized;
      this.showFeedback(result);
      return result.valid;
    },

    showFeedback(result) {
      if (!this.feedback) return;

      // Clear existing feedback
      const existingAlert = this.feedback.querySelector('.validation-alert');
      if (existingAlert) existingAlert.remove();

      if (result.error) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-error validation-alert';
        alert.innerHTML = `<i class="fas fa-exclamation-circle"></i><span>${result.error}</span>`;
        this.feedback.appendChild(alert);
      } else if (result.valid) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success validation-alert';
        alert.innerHTML = `<i class="fas fa-check-circle"></i><span>Valid Ethereum address</span>`;
        this.feedback.appendChild(alert);
      }
    },

    handleSubmit(e) {
      // Prevent double submission
      if (this.isSubmitting) {
        e.preventDefault();
        e.stopPropagation();
        console.log('Form submission blocked - already submitting');
        return false;
      }

      const result = AddressValidator.validate(this.input.value);

      if (!result.valid) {
        e.preventDefault();
        e.stopPropagation();
        this.showFeedback({
          valid: false,
          normalized: result.normalized,
          error: result.error || 'Please enter a valid 42-character Ethereum address'
        });
        this.input.focus();
        return false;
      }

      // Set normalized value
      this.input.value = result.normalized;

      // Mark as submitting and show loading state
      this.isSubmitting = true;
      this.setLoading(true);
      
      // Allow the form to submit normally (don't prevent default)
      return true;
    },

    setLoading(isLoading) {
      if (!this.button) return;

      if (isLoading) {
        this.button.classList.add('loading');
        this.button.disabled = true;
        this.input.readOnly = true;
      } else {
        this.button.classList.remove('loading');
        this.button.disabled = false;
        this.input.readOnly = false;
        this.isSubmitting = false;
      }
    }
  };

  // ========== Copy to Clipboard ==========
  const CopyHandler = {
    init() {
      document.addEventListener('click', (e) => {
        const copyBtn = e.target.closest('.copy-btn, [data-copy]');
        if (copyBtn) {
          const text = copyBtn.dataset.copy || copyBtn.dataset.address;
          if (text) this.copy(text, copyBtn);
        }
      });
    },

    async copy(text, button) {
      try {
        await navigator.clipboard.writeText(text);
        this.showSuccess(button);
      } catch (err) {
        // Fallback for older browsers
        this.fallbackCopy(text);
        this.showSuccess(button);
      }
    },

    fallbackCopy(text) {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    },

    showSuccess(button) {
      const icon = button.querySelector('i');
      if (icon) {
        const originalClass = icon.className;
        icon.className = 'fas fa-check';
        setTimeout(() => {
          icon.className = originalClass;
        }, 2000);
      }
    }
  };

  // ========== Animations ==========
  const Animations = {
    init() {
      this.animateOnScroll();
      this.animateScoreRing();
    },

    animateOnScroll() {
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            entry.target.classList.add('animate-in');
          }
        });
      }, { threshold: 0.1 });

      document.querySelectorAll('.feature-card, .step-card, .stat-item').forEach(el => {
        observer.observe(el);
      });
    },

    animateScoreRing() {
      const scoreRing = document.querySelector('.score-ring');
      if (!scoreRing) return;

      const score = parseFloat(scoreRing.dataset.score) || 0;
      const progress = (score / 1000) * 100;
      const circle = scoreRing.querySelector('.score-ring-progress');
      
      if (!circle) return;

      const circumference = 2 * Math.PI * 90;
      const offset = circumference - (progress / 100) * circumference;

      circle.style.strokeDasharray = circumference;
      circle.style.strokeDashoffset = circumference;

      // Trigger animation after a short delay
      setTimeout(() => {
        circle.style.transition = 'stroke-dashoffset 1.5s ease-out';
        circle.style.strokeDashoffset = offset;
      }, 100);
    }
  };

  // ========== Smooth Scrolling ==========
  const SmoothScroll = {
    init() {
      document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', (e) => {
          e.preventDefault();
          const target = document.querySelector(anchor.getAttribute('href'));
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
          }
        });
      });
    }
  };

  // ========== Tooltips ==========
  const Tooltips = {
    init() {
      document.querySelectorAll('[title]').forEach(el => {
        el.addEventListener('mouseenter', (e) => this.show(e));
        el.addEventListener('mouseleave', () => this.hide());
      });
    },

    show(e) {
      const text = e.target.getAttribute('title');
      if (!text) return;

      // Store and remove title to prevent default tooltip
      e.target.dataset.tooltip = text;
      e.target.removeAttribute('title');

      const tooltip = document.createElement('div');
      tooltip.className = 'custom-tooltip';
      tooltip.textContent = text;
      tooltip.style.cssText = `
        position: fixed;
        background: var(--color-bg-tertiary);
        color: var(--color-text-primary);
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 13px;
        pointer-events: none;
        z-index: 1000;
        box-shadow: var(--shadow-md);
      `;

      document.body.appendChild(tooltip);

      const rect = e.target.getBoundingClientRect();
      tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
      tooltip.style.top = `${rect.top - tooltip.offsetHeight - 8}px`;
    },

    hide() {
      const tooltip = document.querySelector('.custom-tooltip');
      if (tooltip) {
        tooltip.remove();
      }

      // Restore title attribute
      document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.setAttribute('title', el.dataset.tooltip);
        delete el.dataset.tooltip;
      });
    }
  };

  // ========== Initialize ==========
  let initialized = false;
  
  function init() {
    // Prevent double initialization
    if (initialized) {
      console.log('App already initialized, skipping');
      return;
    }
    
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init, { once: true });
      return;
    }

    initialized = true;
    
    ThemeManager.init();
    MobileNav.init();
    FormHandler.init();
    CopyHandler.init();
    Animations.init();
    SmoothScroll.init();
    
    console.log('🚀 OnChain Credit UI initialized');
  }

  // Start initialization
  init();
})();

