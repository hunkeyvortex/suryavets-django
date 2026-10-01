(() => {
  const sheet = document.querySelector('#sv-category-sheet');
  const opener = document.querySelector('[data-category-sheet-open]');
  if (!sheet || !opener) return;
  opener.addEventListener('click', () => {
    sheet.showModal();
    document.body.classList.add('sv-sheet-open');
    opener.setAttribute('aria-expanded', 'true');
    sheet.querySelector('[data-category-sheet-close]').focus();
  });
  sheet.querySelector('[data-category-sheet-close]').addEventListener('click', () => sheet.close());
  sheet.addEventListener('click', event => {
    const rect = sheet.getBoundingClientRect();
    if (event.target === sheet && (event.clientY < rect.top || event.clientX < rect.left || event.clientX > rect.right)) sheet.close();
  });
  sheet.addEventListener('close', () => {
    document.body.classList.remove('sv-sheet-open');
    opener.setAttribute('aria-expanded', 'false');
    opener.focus();
  });
  matchMedia('(min-width:761px)').addEventListener('change', event => {
    if (event.matches && sheet.open) sheet.close();
  });
})();
