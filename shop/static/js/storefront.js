document.addEventListener('DOMContentLoaded', () => {
  const navigation = document.querySelector('[data-primary-navigation]');
  const menuToggle = document.querySelector('[data-menu-toggle]');

  if (navigation && menuToggle) {
    menuToggle.addEventListener('click', () => {
      const isOpen = navigation.classList.toggle('is-open');
      menuToggle.setAttribute('aria-expanded', String(isOpen));
      menuToggle.setAttribute('aria-label', isOpen ? 'Close navigation' : 'Open navigation');
    });
  }

  const closeSubmenus = (except = null) => {
    document.querySelectorAll('[data-submenu-toggle]').forEach((toggle) => {
      const parent = toggle.closest('.primary-navigation__item');
      if (parent !== except) {
        parent?.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  };

  document.querySelectorAll('[data-submenu-toggle]').forEach((toggle) => {
    toggle.addEventListener('click', () => {
      const parent = toggle.closest('.primary-navigation__item');
      const isOpen = parent.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(isOpen));
      if (isOpen) closeSubmenus(parent);
    });
  });

  document.addEventListener('click', (event) => {
    if (navigation && !navigation.contains(event.target)) closeSubmenus();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    closeSubmenus();
    if (navigation?.classList.contains('is-open')) {
      navigation.classList.remove('is-open');
      menuToggle?.setAttribute('aria-expanded', 'false');
      menuToggle?.focus();
    }
  });

  const newsletterForm = document.querySelector('[data-newsletter-form]');
  if (newsletterForm) {
    newsletterForm.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = newsletterForm.querySelector('[data-newsletter-message]');
      const submit = newsletterForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      try {
        const response = await fetch(newsletterForm.action, {method: 'POST', body: new FormData(newsletterForm), headers: {'X-Requested-With': 'XMLHttpRequest'}});
        const result = await response.json();
        message.textContent = result.message || 'Thank you for subscribing!';
        if (result.success) newsletterForm.reset();
      } catch (error) {
        message.textContent = 'Please try again in a moment.';
      } finally {
        submit.disabled = false;
      }
    });
  }

  const hero = document.querySelector('[data-hero-slider]');
  if (hero) {
    const slides = Array.from(hero.querySelectorAll('.home-hero__slide'));
    const dots = hero.querySelector('[data-hero-dots]');
    let activeIndex = 0;
    let timer;

    const showSlide = (nextIndex) => {
      activeIndex = (nextIndex + slides.length) % slides.length;
      slides.forEach((slide, index) => slide.classList.toggle('is-active', index === activeIndex));
      dots?.querySelectorAll('button').forEach((dot, index) => {
        dot.classList.toggle('is-active', index === activeIndex);
        dot.setAttribute('aria-current', String(index === activeIndex));
      });
    };
    const restart = () => {
      window.clearInterval(timer);
      if (slides.length > 1) timer = window.setInterval(() => showSlide(activeIndex + 1), 5500);
    };

    slides.forEach((_, index) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.setAttribute('aria-label', `Show offer ${index + 1}`);
      dot.addEventListener('click', () => { showSlide(index); restart(); });
      dots?.appendChild(dot);
    });
    hero.querySelector('[data-hero-previous]')?.addEventListener('click', () => { showSlide(activeIndex - 1); restart(); });
    hero.querySelector('[data-hero-next]')?.addEventListener('click', () => { showSlide(activeIndex + 1); restart(); });
    showSlide(0);
    restart();
  }

  document.querySelectorAll('[data-product-carousel]').forEach((carousel) => {
    const track = carousel.querySelector('[data-product-track]');
    if (!track) return;
    const scrollProducts = (direction) => {
      const firstCard = track.querySelector('.store-product-card');
      const amount = firstCard ? firstCard.getBoundingClientRect().width + 20 : track.clientWidth * .8;
      track.scrollBy({left: direction * amount, behavior: 'smooth'});
    };
    carousel.querySelector('[data-product-previous]')?.addEventListener('click', () => scrollProducts(-1));
    carousel.querySelector('[data-product-next]')?.addEventListener('click', () => scrollProducts(1));
  });
});
