(() => {
  const closeAll = (except) => {
    const dropdowns = Array.from(document.querySelectorAll('.multi-dropdown'));
    for (const dropdown of dropdowns) {
      if (dropdown !== except) {
        dropdown.removeAttribute('open');
      }
    }
  };

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) {
      return;
    }

    const clearButton = target.closest('.multi-clear-filter');
    if (clearButton instanceof HTMLButtonElement) {
      const dropdown = clearButton.closest('.multi-dropdown');
      if (dropdown instanceof HTMLElement) {
        const checkboxes = dropdown.querySelectorAll('input[type="checkbox"]');
        for (const checkbox of checkboxes) {
          if (checkbox instanceof HTMLInputElement) {
            checkbox.checked = false;
          }
        }
      }
      return;
    }

    const owner = target.closest('.multi-dropdown');
    if (!owner) {
      closeAll();
      return;
    }

    closeAll(owner);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      closeAll();
    }
  });
})();
