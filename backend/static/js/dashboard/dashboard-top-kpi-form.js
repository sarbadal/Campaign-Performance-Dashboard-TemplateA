(() => {
  const forms = Array.from(document.querySelectorAll('.top-chart-kpi-form'));
  if (!forms.length) {
    return;
  }

  document.addEventListener('submit', async (event) => {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.classList.contains('top-chart-kpi-form')) {
      return;
    }

    event.preventDefault();

    const submitter = event.submitter;
    const buttons = Array.from(form.querySelectorAll('button'));
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
      const formData = new FormData(form);
      for (const [key, value] of formData.entries()) {
        params.append(key, String(value));
      }

      const actionRaw = form.getAttribute('action') || window.location.href;
      const actionUrl = new URL(actionRaw, window.location.href);
      const hash = actionUrl.hash || '#insights-top';
      actionUrl.hash = '';
      actionUrl.search = params.toString();

      const response = await fetch(actionUrl.toString(), {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (!response.ok) {
        throw new Error(`KPI update failed with status ${response.status}`);
      }

      const html = await response.text();
      const parser = new DOMParser();
      const nextDoc = parser.parseFromString(html, 'text/html');
      const nextInsights = nextDoc.querySelector('#insights-top');
      const currentInsights = document.querySelector('#insights-top');

      if (!(nextInsights instanceof HTMLElement) || !(currentInsights instanceof HTMLElement)) {
        throw new Error('Unable to update insights panel');
      }

      currentInsights.replaceWith(nextInsights);

      if (window.DashboardCharts && typeof window.DashboardCharts.renderTopEntityCharts === 'function') {
        window.DashboardCharts.renderTopEntityCharts(document);
      }
      if (window.DashboardSync && typeof window.DashboardSync.syncDualAxisHiddenTopKpis === 'function') {
        window.DashboardSync.syncDualAxisHiddenTopKpis(nextDoc);
      }

      const nextUrl = `${actionUrl.pathname}${actionUrl.search}${hash}`;
      window.history.replaceState({}, '', nextUrl);
      window.scrollTo({ top: previousScrollY, left: 0, behavior: 'auto' });
    } catch (_err) {
      form.submit();
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
