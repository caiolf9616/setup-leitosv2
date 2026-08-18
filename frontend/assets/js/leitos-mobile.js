(() => {
  document.addEventListener('click', (event) => {
    const bedCard = event.target.closest('.bed-card');
    if (!bedCard || bedCard.disabled || !window.matchMedia('(max-width: 900px)').matches) return;

    requestAnimationFrame(() => {
      document.querySelector('.event-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
})();
