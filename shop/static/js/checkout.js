(() => {
  const form = document.querySelector('[data-checkout-form]');
  if (!form) return;
  const button = form.querySelector('[data-place-order]');
  const billing = form.querySelector('[data-billing-fields]');
  const sameAddress = form.querySelector('[name="billing_same_as_shipping"]');
  const updateBilling = () => {
    billing.hidden = sameAddress.checked;
    sameAddress.setAttribute('aria-expanded', String(!sameAddress.checked));
  };
  billing.id = 'checkout-billing';
  sameAddress.setAttribute('aria-controls', billing.id);
  sameAddress.addEventListener('change', updateBilling);
  updateBilling();
  const initiallyDisabled = button.disabled;
  form.addEventListener('submit', event => {
    if (event.submitter && event.submitter.value !== 'place_order') return;
    button.disabled = true;
    button.textContent = 'Placing order…';
  });
  window.addEventListener('pageshow', () => { button.disabled = initiallyDisabled; button.textContent = 'Place order'; });
})();
