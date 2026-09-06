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
