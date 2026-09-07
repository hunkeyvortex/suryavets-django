(() => {
  const gallery = document.querySelector('[data-product-gallery]');
  if (gallery) {
    const mainImage = gallery.querySelector('[data-product-main-image]');
    gallery.querySelectorAll('[data-product-image]').forEach((button) => {
      button.addEventListener('click', () => {
        mainImage.src = button.dataset.productImage;
        mainImage.hidden = false;
        const notice = gallery.querySelector('[data-variant-image-missing]');
        if (notice) notice.hidden = true;
        mainImage.alt = button.dataset.productAlt || mainImage.alt;
        gallery.querySelectorAll('[data-product-image]').forEach((item) => {
          item.classList.remove('is-active'); item.setAttribute('aria-pressed', 'false');
        });
        button.classList.add('is-active');
        button.setAttribute('aria-pressed', 'true');
      });
    });
  }

  const productForm = document.querySelector('.product-form');
  if (productForm) {
    // Browser formatting is presentation only; the server recalculates all prices.
    const money = value => '₹' + Number(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const mainImage = document.querySelector('[data-product-main-image]');
    const defaultImage = mainImage ? {src: mainImage.src, alt: mainImage.alt} : null;
    const syncVariant = () => {
      const selected = productForm.querySelector('[name="variant_id"]:checked');
      if (!selected) return;
      document.querySelector('[data-product-price]').textContent = money(selected.dataset.price);
      document.querySelector('[data-product-compare]').textContent = money(selected.dataset.regular);
      document.querySelector('[data-product-compare-wrap]').hidden = Number(selected.dataset.regular) <= Number(selected.dataset.price);
      document.querySelector('[data-product-discount]').textContent = selected.dataset.discount + '% OFF';
      const saving = document.querySelector('[data-product-saving]');
      saving.hidden = Number(selected.dataset.regular) <= Number(selected.dataset.price);
      saving.textContent = 'You save ₹' + selected.dataset.saving + ' on MRP';
      document.querySelector('[data-product-sku]').textContent = selected.dataset.sku || 'Not supplied';
      document.querySelector('[data-selected-pack]').textContent = selected.dataset.name;
      document.querySelector('[data-product-unit]').textContent = selected.dataset.unit;
      if (mainImage) {
        mainImage.hidden = selected.dataset.imageMissing === '1';
        const notice = gallery.querySelector('[data-variant-image-missing]');
        if (notice) notice.hidden = !mainImage.hidden;
        mainImage.src = selected.dataset.image || defaultImage.src;
        mainImage.alt = selected.dataset.alt || defaultImage.alt;
        gallery.querySelectorAll('[data-product-image]').forEach(button => {
          const active = button.dataset.productImage === mainImage.getAttribute('src');
          button.classList.toggle('is-active', active); button.setAttribute('aria-pressed', String(active));
        });
      }
      const quantity = productForm.querySelector('[name="quantity"]');
      const stock = Number(selected.dataset.stock);
      quantity.max = String(stock);
      if (stock > 0 && Number(quantity.value) > stock) quantity.value = String(stock);
      const submit = productForm.querySelector('[data-add-to-cart]');
      productForm.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = stock < 1; });
      submit.textContent = stock > 0 ? 'Add to Cart' : 'Out of Stock';
      document.querySelector('[data-product-stock]').textContent = stock > 0 ? 'In stock · ready to add' : 'Out of stock';
    };
    productForm.querySelectorAll('[name="variant_id"]').forEach(input => input.addEventListener('change', syncVariant));
    syncVariant();
    productForm.querySelectorAll('[data-quantity-step]').forEach(button => button.addEventListener('click', () => {
      const input = productForm.querySelector('[name="quantity"]');
      input.value = String(Math.max(1, Math.min(Number(input.max) || 10000, (Number(input.value) || 1) + Number(button.dataset.quantityStep))));
      input.dispatchEvent(new Event('change', {bubbles: true}));
    }));
  }

  const mobileFilterForm = document.querySelector('[data-mobile-filter-form]');
  if (!mobileFilterForm) return;
  const controls = [...mobileFilterForm.querySelectorAll('details')];
  controls.forEach((control) => {
    control.addEventListener('toggle', () => {
      if (!control.open) return;
      controls.filter((item) => item !== control).forEach((item) => { item.open = false; });
      const panel = control.querySelector('.catalog-mobile-control__panel');
      const anchor = control.querySelector('summary').getBoundingClientRect();
      panel.style.left = Math.max(14, Math.min(anchor.left, innerWidth - panel.offsetWidth - 14)) + 'px';
      panel.style.top = Math.min(anchor.bottom + 6, Math.max(14, innerHeight - panel.offsetHeight - 14)) + 'px';
    });
  });
  mobileFilterForm.querySelectorAll('select').forEach((select) => {
    select.addEventListener('change', () => mobileFilterForm.requestSubmit());
  });
  document.addEventListener('click', (event) => {
    if (!mobileFilterForm.contains(event.target)) controls.forEach((item) => { item.open = false; });
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') controls.forEach((item) => { item.open = false; });
  });
})();
