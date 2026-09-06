(() => {
  const drawer = document.querySelector('[data-mobile-navigation]');
  const opener = document.querySelector('[data-menu-toggle]');
  function setExpanded(item, expanded) {
    item.classList.toggle('is-expanded', expanded);
    const button = item.querySelector(':scope > [data-tree-toggle]');
    button?.setAttribute('aria-expanded', String(expanded));
    if (button) button.querySelector('span').textContent = expanded ? '−' : '+';
    if (!expanded) item.querySelectorAll('.is-expanded').forEach(child => setExpanded(child, false));
  }
  document.querySelectorAll('[data-tree-toggle]').forEach(button => {
    const item = button.parentElement;
    button.addEventListener('click', () => {
      const expanded = !item.classList.contains('is-expanded');
      [...item.parentElement.children].filter(sibling => sibling !== item).forEach(sibling => setExpanded(sibling, false));
      setExpanded(item, expanded);
    });
    if (item.closest('.category-tree--desktop')) {
      item.addEventListener('pointerenter', event => {
        if (event.pointerType === 'mouse') setExpanded(item, true);
      });
      item.addEventListener('pointerleave', event => {
        if (event.pointerType === 'mouse' && !item.contains(document.activeElement)) setExpanded(item, false);
      });
      item.addEventListener('focusout', () => setTimeout(() => {
        if (!item.contains(document.activeElement) && !item.matches(':hover')) setExpanded(item, false);
      }, 0));
    }
  });
  document.addEventListener('click', event => {
    if (!event.target.closest('[data-category-tree]')) document.querySelectorAll('.category-tree--desktop .is-expanded').forEach(item => setExpanded(item, false));
  });
  document.addEventListener('keydown', event => {
    if (event.key !== 'Escape') return;
    const item = document.activeElement?.closest('.is-expanded');
    if (item) { event.preventDefault(); setExpanded(item, false); item.querySelector(':scope > [data-tree-toggle]')?.focus(); }
  });
  opener?.addEventListener('click', () => {
    drawer.showModal(); opener.setAttribute('aria-expanded', 'true'); document.body.classList.add('navigation-open');
  });
  drawer?.querySelector('[data-mobile-close]').addEventListener('click', () => drawer.close());
  drawer?.addEventListener('click', event => { if (event.target === drawer && event.clientX > drawer.getBoundingClientRect().right) drawer.close(); });
  drawer?.addEventListener('close', () => { document.body.classList.remove('navigation-open'); opener.setAttribute('aria-expanded', 'false'); opener.focus(); });
  matchMedia('(min-width: 861px)').addEventListener('change', event => { if (event.matches && drawer.open) drawer.close(); });
})();
