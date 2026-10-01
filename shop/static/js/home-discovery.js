(() => {
  document.querySelectorAll('[data-home-tabs]').forEach(section => {
    const tabs = [...section.querySelectorAll('[data-home-tab]')];
    const select = tab => {
      tabs.forEach(item => { const active = item === tab; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; });
      section.querySelectorAll('[data-home-panel]').forEach(panel => { panel.hidden = panel.dataset.homePanel !== tab.dataset.homeTab; });
    };
    tabs.forEach((tab, index) => {
      tab.addEventListener('click', () => select(tab));
      tab.addEventListener('keydown', event => {
        let next;
        if (event.key === 'ArrowRight') next = tabs[(index + 1) % tabs.length];
        if (event.key === 'ArrowLeft') next = tabs[(index + tabs.length - 1) % tabs.length];
        if (event.key === 'Home') next = tabs[0];
        if (event.key === 'End') next = tabs[tabs.length - 1];
        if (next) { event.preventDefault(); select(next); next.focus(); }
      });
    });
  });
})();
