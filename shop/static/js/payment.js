(() => {
  const button = document.getElementById('open-payment');
  if (!button) return;
  const message = document.getElementById('payment-message');
  button.addEventListener('click', () => {
    if (!window.Razorpay) { message.textContent = 'Payment checkout could not load. Refresh or contact support.'; return; }
    const options = JSON.parse(document.getElementById('gateway-options').textContent);
    options.handler = result => {
      const form = document.getElementById('payment-verification');
      for (const key of ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature']) form.elements[key].value = result[key] || '';
      button.disabled = true;
      message.textContent = 'Verifying payment with the server. Please do not pay again.';
      form.submit();
    };
    const checkout = new window.Razorpay(options);
    checkout.on('payment.failed', () => { message.textContent = 'Payment was not confirmed. No paid-order confirmation has been sent.'; });
    checkout.open();
  });
})();
