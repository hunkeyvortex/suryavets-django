/* Isolated card controls. Prices are precomputed by Django; cart POSTs remain authoritative. */
(() => {
  document.querySelectorAll('[data-product-card]').forEach(card => {
    const form = card.querySelector('[data-card-form]');
    const quantity = form.querySelector('[name="quantity"]');
    const add = form.querySelector('[data-card-add]');
    const down = form.querySelector('[data-card-step="-1"]');
    const up = form.querySelector('[data-card-step="1"]');
    let available = !add.disabled;
    const updateQuantity = () => {
      const maximum = Number(quantity.max) || 10000;
      quantity.value = Math.max(1, Math.min(maximum, parseInt(quantity.value, 10) || 1));
      down.disabled = !available || Number(quantity.value) <= 1;
      up.disabled = !available || Number(quantity.value) >= maximum;
      quantity.disabled = !available;
      add.disabled = !available;
      add.textContent = available ? 'Add to Cart' : 'Out of stock';
    };
    const select = input => {
      if (!input) return;
      const data = input.dataset;
      available = data.stock === '1';
      card.querySelector('[data-card-price]').textContent = data.price;
      const regular = card.querySelector('[data-card-regular]');
      regular.textContent = data.regular;
      regular.hidden = data.sale !== '1';
      const saving = card.querySelector('[data-card-saving]');
      saving.textContent = data.saving;
      saving.hidden = data.sale !== '1';
      const badge = card.querySelector('[data-card-badge]');
      badge.textContent = data.badge;
      badge.hidden = data.sale !== '1';
      card.querySelector('[data-card-stock]').textContent = available ? 'In stock' : 'Out of stock';
      card.querySelector('[data-card-selected]').textContent = `${data.name} selected`;
      card.querySelector('[data-card-from]')?.setAttribute('hidden', '');
      quantity.max = data.max;
      const image = card.querySelector('[data-card-image]');
      image.hidden = !data.image;
      if (data.image) { image.src = data.image; image.alt = data.alt; }
      else { image.removeAttribute('src'); image.alt = ''; }
      card.querySelector('[data-card-photo-missing]').hidden = Boolean(data.image);
      const more = input.closest('details');
      if (more) more.open = true;
      updateQuantity();
    };
    form.addEventListener('change', event => {
      if (event.target.matches('[name="variant_id"]')) select(event.target);
      if (event.target === quantity) updateQuantity();
    });
    form.addEventListener('click', event => {
      const button = event.target.closest('[data-card-step]');
      if (!button) return;
      quantity.value = (parseInt(quantity.value, 10) || 1) + Number(button.dataset.cardStep);
      updateQuantity();
    });
    select(form.querySelector('[name="variant_id"]:checked'));
    updateQuantity();
  });
})();
