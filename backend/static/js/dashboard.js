(() => {
  const dropdowns = Array.from(document.querySelectorAll('.multi-dropdown'));
  if (!dropdowns.length) {
    return;
  }

  const sizeDropdownMenus = () => {
    const viewportMax = Math.max(280, Math.floor(window.innerWidth * 0.92));

    for (const dropdown of dropdowns) {
      const summary = dropdown.querySelector('summary');
      const menu = dropdown.querySelector('.multi-menu');
      const labels = Array.from(dropdown.querySelectorAll('.multi-option span'));

      if (!(summary instanceof HTMLElement) || !(menu instanceof HTMLElement)) {
        continue;
      }

      let longest = 0;
      for (const label of labels) {
        if (!(label instanceof HTMLElement)) {
          continue;
        }
        const width = Math.ceil(label.getBoundingClientRect().width);
        if (width > longest) {
          longest = width;
        }
      }

      const summaryWidth = Math.ceil(summary.getBoundingClientRect().width);
      const checkboxAndPadding = 64;
      const contentWidth = longest + checkboxAndPadding;
      const desired = Math.max(summaryWidth, contentWidth, 280);
      const finalWidth = Math.min(desired, viewportMax);

      menu.style.width = `${finalWidth}px`;
    }
  };

  const closeAll = (except) => {
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

  window.addEventListener('resize', sizeDropdownMenus);
  sizeDropdownMenus();
})();
