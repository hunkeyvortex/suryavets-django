// Normal POST forms still work without JavaScript. Use Update to save changes.
document.querySelectorAll('[data-basket-quantity]').forEach(form => {
  const input = form.querySelector('input[name="quantity"]');
  const buttons = [...form.querySelectorAll('[data-step]')];
  const refresh = () => buttons.forEach(button => {
    button.disabled = Number(button.dataset.step) < 0
      ? input.valueAsNumber <= Number(input.min)
      : input.valueAsNumber >= Number(input.max);
  });
  buttons.forEach(button => {
    button.hidden = false;
    button.addEventListener('click', () => {
      if (!Number.isFinite(input.valueAsNumber)) input.value = input.min;
      if (Number(button.dataset.step) > 0) input.stepUp(); else input.stepDown();
      refresh();
    });
  });
  input.addEventListener('input', refresh);
  refresh();
});
