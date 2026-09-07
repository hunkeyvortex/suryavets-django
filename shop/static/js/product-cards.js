/* Isolated card controls. Prices are precomputed by Django; cart POSTs remain authoritative. */
(() => {
  document.querySelectorAll('[data-product-card]').forEach(card => {
    const form = card.querySelector('[data-card-form]');
    const add = form.querySelector('[data-card-add]');
    let available = !add.disabled;
    const updateAvailability = () => {
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
      const image = card.querySelector('[data-card-image]');
      image.hidden = !data.image;
      if (data.image) { image.src = data.image; image.alt = data.alt; }
      else { image.removeAttribute('src'); image.alt = ''; }
      card.querySelector('[data-card-photo-missing]').hidden = Boolean(data.image);
      const more = input.closest('details');
      if (more) more.open = true;
      updateAvailability();
    };
    form.addEventListener('change', event => {
      if (event.target.matches('[name="variant_id"]')) select(event.target);
    });
    select(form.querySelector('[name="variant_id"]:checked'));
    updateAvailability();
  });
})();
