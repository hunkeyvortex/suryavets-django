document.querySelectorAll('[data-password-toggle]').forEach((button) => {
  button.addEventListener('click', () => {
    const input = document.getElementById(button.getAttribute('aria-controls'));
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.textContent = visible ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(visible));
    const label = document.querySelector(`label[for="${input.id}"]`);
    button.setAttribute('aria-label', `${visible ? 'Hide' : 'Show'} ${label ? label.textContent.toLowerCase() : 'password'}`);
  });
});
