(() => {
  const gallery = document.querySelector('[data-product-gallery]');
  if (gallery) {
    const mainImage = gallery.querySelector('[data-product-main-image]');
    gallery.querySelectorAll('[data-product-image]').forEach((button) => {
      button.addEventListener('click', () => {
        mainImage.src = button.dataset.productImage;
        mainImage.alt = button.dataset.productAlt || mainImage.alt;
        gallery.querySelectorAll('[data-product-image]').forEach((item) => item.classList.remove('is-active'));
        button.classList.add('is-active');
      });
    });
  }

  const productForm = document.querySelector('.product-form');
  if (productForm) {
    // Browser formatting is presentation only; the server recalculates all prices.
    const money = value => 'Rs. ' + Number(value).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    const syncVariant = () => {
      const selected = productForm.querySelector('[name="variant_id"]:checked');
      if (!selected) return;
      document.querySelector('[data-product-price]').textContent = money(selected.dataset.price);
      document.querySelector('[data-product-compare]').textContent = money(selected.dataset.regular);
      document.querySelector('[data-product-compare-wrap]').hidden = Number(selected.dataset.regular) <= Number(selected.dataset.price);
      const quantity = productForm.querySelector('[name="quantity"]');
      const stock = Number(selected.dataset.stock);
      quantity.max = String(stock);
      if (stock > 0 && Number(quantity.value) > stock) quantity.value = String(stock);
      const submit = productForm.querySelector('button[type="submit"]');
      submit.disabled = stock < 1;
      submit.textContent = stock > 0 ? 'Add to Cart' : 'Out of Stock';
    };
    productForm.querySelectorAll('[name="variant_id"]').forEach(input => input.addEventListener('change', syncVariant));
    syncVariant();
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
