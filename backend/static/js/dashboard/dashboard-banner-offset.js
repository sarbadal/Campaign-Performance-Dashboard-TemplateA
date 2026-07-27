(() => {
  const applyBannerOffset = () => {
    const banner = document.querySelector('.top-banner');
    if (!(banner instanceof HTMLElement)) {
      return;
    }

    const height = Math.max(banner.offsetHeight, 0);
    document.documentElement.style.setProperty('--banner-offset', `${height}px`);
  };

  const scheduleApply = () => {
    window.requestAnimationFrame(applyBannerOffset);
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', scheduleApply, { once: true });
  } else {
    scheduleApply();
  }

  window.addEventListener('resize', scheduleApply);

  const banner = document.querySelector('.top-banner');
  if (banner instanceof HTMLElement && typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(() => {
      scheduleApply();
    });
    observer.observe(banner);
  }
})();
