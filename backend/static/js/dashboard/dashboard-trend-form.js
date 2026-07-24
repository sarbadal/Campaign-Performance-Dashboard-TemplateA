(() => {
  const form = document.querySelector('.dual-axis-form');
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  document.addEventListener('submit', async (event) => {
    const targetForm = event.target;
    if (!(targetForm instanceof HTMLFormElement) || !targetForm.classList.contains('dual-axis-form')) {
      return;
    }

    event.preventDefault();

    const submitter = event.submitter;
    const buttons = Array.from(targetForm.querySelectorAll('button'));
    for (const button of buttons) {
      if (button instanceof HTMLButtonElement) {
        button.disabled = true;
      }
    }

    if (submitter instanceof HTMLButtonElement) {
      submitter.setAttribute('aria-busy', 'true');
    }

    const previousScrollY = window.scrollY;

    try {
      const params = new URLSearchParams();
      const formData = new FormData(targetForm);
      for (const [key, value] of formData.entries()) {
        params.append(key, String(value));
      }

      const actionRaw = targetForm.getAttribute('action') || window.location.href;
      const actionUrl = new URL(actionRaw, window.location.href);
      const hash = actionUrl.hash || '#dual-axis-trend';
      actionUrl.hash = '';
      actionUrl.search = params.toString();

      const response = await fetch(actionUrl.toString(), {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (!response.ok) {
        throw new Error(`Trend update failed with status ${response.status}`);
      }

      const html = await response.text();
      const parser = new DOMParser();
      const nextDoc = parser.parseFromString(html, 'text/html');
      const nextTrendPanel = nextDoc.querySelector('#dual-axis-trend');
      const currentTrendPanel = document.querySelector('#dual-axis-trend');

      if (!(nextTrendPanel instanceof HTMLElement) || !(currentTrendPanel instanceof HTMLElement)) {
        throw new Error('Unable to update trend panel');
      }

      currentTrendPanel.replaceWith(nextTrendPanel);

      if (window.DashboardCharts && typeof window.DashboardCharts.renderDualAxisChart === 'function') {
        window.DashboardCharts.renderDualAxisChart(document);
      }
      if (window.DashboardSync && typeof window.DashboardSync.syncTopChartHiddenTrendFields === 'function') {
        window.DashboardSync.syncTopChartHiddenTrendFields(nextDoc);
      }

      const nextUrl = `${actionUrl.pathname}${actionUrl.search}${hash}`;
      window.history.replaceState({}, '', nextUrl);
      window.scrollTo({ top: previousScrollY, left: 0, behavior: 'auto' });
    } catch (_err) {
      targetForm.submit();
      return;
    }

    for (const button of buttons) {
      if (button instanceof HTMLButtonElement) {
        button.disabled = false;
      }
    }

    if (submitter instanceof HTMLButtonElement) {
      submitter.removeAttribute('aria-busy');
    }
  });
})();
