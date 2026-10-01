(() => {
  const node = document.getElementById('surya-commerce-events');
  if (!node) return;
  // Local event bus only. No analytics provider, identifiers, cookies or network calls.
  window.suryaCommerceEvents = window.suryaCommerceEvents || [];
  for (const detail of JSON.parse(node.textContent)) {
    if (detail.event === 'purchase') {
      try {
        const key = 'surya-purchase-event:' + detail.transaction_id;
        if (sessionStorage.getItem(key)) continue;
        sessionStorage.setItem(key, '1');
      } catch (_) { continue; }
    }
    window.suryaCommerceEvents.push(detail);
    window.dispatchEvent(new CustomEvent('surya:commerce', {detail}));
  }
})();
