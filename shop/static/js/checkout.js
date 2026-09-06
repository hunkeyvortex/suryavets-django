(() => {
  const form = document.querySelector('[data-checkout-form]');
  if (!form) return;
  const button = form.querySelector('button[type="submit"]');
  const initiallyDisabled = button.disabled;
  form.addEventListener('submit', () => { button.disabled = true; button.textContent = 'Placing order…'; });
  window.addEventListener('pageshow', () => { button.disabled = initiallyDisabled; button.textContent = 'Place order'; });
})();
