// Progressive enhancement: the normal Update POST remains available without JS.
(() => {
  const forms = [...document.querySelectorAll('[data-basket-quantity]')];
  if (!forms.length || !window.fetch) return;
  const feedback = document.querySelector('[data-basket-feedback]');
  const status = document.querySelector('[data-basket-status]');
  const retry = document.querySelector('[data-basket-retry]');
  const checkout = document.querySelector('.basket-summary .basket-checkout');
  const pending = new Map(), states = new Map();
  let running = false, failed = false, timer;
  let purchaseBlocked = document.querySelector('.basket-page').dataset.purchaseBlocked === '1';
  const announce = (message, error = false) => {
    feedback.hidden = false;
    feedback.classList.toggle('is-error', error);
    status.textContent = message;
  };
  const busy = () => running || [...states.values()].some(s => s.dirty);
  const sync = () => {
    checkout?.setAttribute('aria-disabled', String(busy() || purchaseBlocked));
    document.querySelector('.basket-page').dataset.purchaseBlocked = purchaseBlocked ? '1' : '0';
    if (checkout) checkout.firstChild.textContent = purchaseBlocked ? 'Resolve unavailable items ' : 'Proceed to checkout ';
    document.querySelector('.basket-summary')?.setAttribute('aria-busy', String(running));
    document.querySelectorAll('.basket-line-total button').forEach(b => { b.disabled = running || pending.size > 0; });
    states.forEach(s => s.form.querySelectorAll('[data-step]').forEach(button => {
      button.disabled = Number(button.dataset.step) < 0 ? s.input.valueAsNumber <= 1 : s.input.valueAsNumber >= 10000;
    }));
    retry.hidden = !failed;
  };
  const apply = (data, sent, revision) => {
    purchaseBlocked = data.checkout_allowed === false;
    data.items.forEach(item => {
      const state = states.get(String(item.id));
      if (!state) return;
      const row = state.form.closest('.basket-product');
      row.querySelector('.basket-line-total > strong').textContent = item.line_total;
      row.querySelector('.basket-unit').textContent = `${item.unit_price} each`;
      if (!state.dirty || (state === sent && state.revision === revision)) {
        state.input.value = item.quantity;
        state.dirty = false;
      }
    });
    document.querySelector('.basket-products-heading > span').textContent = `${data.total_items} item${data.total_items === 1 ? '' : 's'}`;
    const summary = document.querySelectorAll('.basket-summary-card dl dd');
    summary[0].textContent = data.subtotal;
    summary[1].textContent = data.free_delivery ? 'Free' : data.shipping;
    summary[1].classList.toggle('basket-free', data.free_delivery);
    document.querySelector('[data-basket-total]').textContent = data.total;
    const delivery = document.querySelector('.basket-delivery');
    delivery.querySelector('strong').textContent = data.free_delivery ? 'Your delivery is on us' : 'A little closer to free delivery';
    delivery.querySelector('p').textContent = data.free_delivery ? "You've unlocked free delivery for this basket." : `Add ${data.delivery_remaining} more to your basket.`;
    delivery.querySelector('progress').max = data.threshold;
    delivery.querySelector('progress').value = data.progress;
    document.querySelectorAll('.cart-badge').forEach(b => { b.textContent = data.total_items; });
    document.querySelector('.header-action--cart')?.setAttribute('aria-label', `Cart, ${data.total_items} items`);
    document.querySelectorAll('.sv-dock-badge').forEach(b => { b.textContent = data.total_items; });
  };
  const flush = async () => {
    if (running || failed || !pending.size) return;
    running = true;
    const [state, desired] = pending.entries().next().value;
    pending.delete(state);
    const revision = state.revision;
    announce('Updating your basket…');
    sync();
    const payload = new FormData(state.form);
    payload.set('quantity', desired);
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(state.form.action, {method:'POST', body:payload, credentials:'same-origin',
        headers:{'X-Requested-With':'XMLHttpRequest', 'Accept':'application/json'}, signal:controller.signal});
      const data = await response.json();
      if ((!response.ok && response.status !== 400) || !Array.isArray(data.items)) throw new Error('Unable to save');
      apply(data, state, revision);
      announce(purchaseBlocked ? data.purchase_issues.join(' ') : data.message, !data.ok || purchaseBlocked);
    } catch (error) {
      // Keep edits and block checkout when the save outcome is uncertain.
      // An explicit retry sends an absolute quantity, never an increment.
      failed = true;
      if (!pending.has(state)) pending.set(state, state.input.value);
      announce("We couldn't confirm this change. Retry saving, or refresh your basket before checkout.", true);
    } finally {
      clearTimeout(timeout);
      running = false;
      sync();
      if (!failed && pending.size) flush();
    }
  };
  const changed = state => {
    state.dirty = true;
    state.revision += 1;
    if (state.input.checkValidity()) pending.set(state, state.input.value);
    else pending.delete(state);
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (!state.input.checkValidity()) announce('Enter a whole quantity between 1 and 10000.', true);
      flush();
    }, 350);
    sync();
  };
  forms.forEach(form => {
    const input = form.querySelector('[name="quantity"]');
    const state = {form, input, dirty:false, revision:0};
    states.set(form.closest('[data-basket-item]').dataset.basketItem, state);
    form.querySelector('.basket-update').hidden = true;
    form.querySelectorAll('[data-step]').forEach(button => {
      button.hidden = false;
      button.addEventListener('click', () => {
        if (!Number.isFinite(input.valueAsNumber)) input.value = 1;
        if (Number(button.dataset.step) > 0) input.stepUp(); else input.stepDown();
        changed(state);
      });
    });
    input.addEventListener('input', () => changed(state));
    input.addEventListener('change', () => { if (state.dirty && input.checkValidity()) { clearTimeout(timer); flush(); } });
    form.addEventListener('submit', event => { event.preventDefault(); changed(state); clearTimeout(timer); flush(); });
  });
  retry.addEventListener('click', () => {
    failed = false;
    states.forEach(state => { if (state.dirty && state.input.checkValidity()) pending.set(state, state.input.value); else pending.delete(state); });
    flush(); sync();
  });
  checkout?.addEventListener('click', event => {
    if (purchaseBlocked) {
      event.preventDefault();
      announce('Your basket has unavailable items. Remove them or contact SuryaVets before checkout.', true);
      return;
    }
    if (!busy()) return;
    event.preventDefault();
    announce(failed ? 'Please retry saving before checkout.' : 'Please wait for your quantity changes to save before checkout.', failed);
    clearTimeout(timer); flush();
  });
  window.addEventListener('beforeunload', event => { if (busy()) { event.preventDefault(); event.returnValue = ''; } });
  sync();
})();
