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
      if (control.open) controls.filter((item) => item !== control).forEach((item) => { item.open = false; });
    });
  });
  mobileFilterForm.querySelectorAll('select').forEach((select) => {
    select.addEventListener('change', () => mobileFilterForm.requestSubmit());
  });
})();
