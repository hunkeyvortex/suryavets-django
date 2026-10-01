/* Isolated card controls. Prices are precomputed by Django; cart POSTs remain authoritative. */
(() => {
  document.querySelectorAll('[data-product-card]').forEach(card => {
    const form = card.querySelector('[data-card-form]');
    const add = form.querySelector('[data-card-add]');
    const photo = card.querySelector('[data-card-image]');
    const missing = card.querySelector('[data-card-photo-missing]');
    const showMissing = () => { photo.hidden = true; missing.hidden = false; };
    photo.addEventListener('error', showMissing);
    if (photo.getAttribute('src') && photo.complete && !photo.naturalWidth) showMissing();
    let available = !add.disabled;
    const updateAvailability = () => {
      add.disabled = !available;
      add.textContent = available ? 'Add to Cart' : 'Unavailable';
    };
    const select = input => {
      if (!input || input.disabled) return;
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
    // Move the existing form, not cloned inputs: one authoritative variant selection.
    const sizes = form.querySelector('.sv-card__sizes');
    if (sizes && form.querySelectorAll('[name="variant_id"]').length > 1 && typeof HTMLDialogElement !== 'undefined') {
      const trigger = document.createElement('button');
      trigger.type = 'button'; trigger.className = 'sv-card__choose-size';
      trigger.textContent = 'Choose size'; trigger.disabled = !available; trigger.setAttribute('aria-haspopup', 'dialog');
      const dialog = document.createElement('dialog'); dialog.className = 'sv-size-dialog';
      const heading = document.createElement('h2'); heading.textContent = card.querySelector('h3').textContent.trim();
      dialog.setAttribute('aria-label', 'Choose size for ' + heading.textContent);
      const close = document.createElement('button'); close.type = 'button';
      close.className = 'sv-size-dialog__close'; close.textContent = 'Close';
      close.addEventListener('click', () => dialog.close());
      const anchor = document.createComment('Product purchase form');
      form.before(anchor);
      dialog.append(close, heading); card.append(dialog);
      const open = () => {
        dialog.append(form); card.classList.add('sv-card--choosing');
        sizes.querySelector('details')?.setAttribute('open', '');
        dialog.showModal();
      };
      dialog.addEventListener('close', () => {
        anchor.after(form); card.classList.remove('sv-card--choosing'); trigger.focus();
      });
      dialog.addEventListener('click', event => { if (event.target === dialog) {
        const box = dialog.getBoundingClientRect();
        if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) dialog.close();
      }});
      // Keep the price visible on the card while the full purchase form is collapsed.
      const preview = document.createElement('div'); preview.className = 'sv-card__price-preview';
      const refresh = () => {
        preview.replaceChildren();
        const price = document.createElement('strong'); price.textContent = form.querySelector('[data-card-price]').textContent;
        const regular = form.querySelector('[data-card-regular]');
        preview.append(price);
        if (!regular.hidden) { const mrp = document.createElement('del'); mrp.textContent = regular.textContent; preview.append(mrp); }
        const context = document.createElement('small'); context.textContent = form.querySelector('[data-card-selected]').textContent;
        preview.append(context);
      };
      refresh(); form.addEventListener('change', refresh);
      trigger.addEventListener('click', open);
      anchor.before(preview, trigger); card.classList.add('sv-card--size-picker');
    }
  });
})();
