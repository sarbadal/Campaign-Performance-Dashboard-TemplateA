(() => {
  const form = document.querySelector('.filters-form');
  if (!(form instanceof HTMLFormElement)) {
    return;
  }

  const replaceSection = (nextDoc, selector) => {
    const nextNode = nextDoc.querySelector(selector);
    const currentNode = document.querySelector(selector);
    if (!(nextNode instanceof HTMLElement) || !(currentNode instanceof HTMLElement)) {
      return false;
    }
    currentNode.replaceWith(nextNode);
    return true;
  };

  document.addEventListener('submit', async (event) => {
    const targetForm = event.target;
    if (!(targetForm instanceof HTMLFormElement) || !targetForm.classList.contains('filters-form')) {
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
      actionUrl.hash = '';
      actionUrl.search = params.toString();

      const response = await fetch(actionUrl.toString(), {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });

      if (!response.ok) {
        throw new Error(`Filter update failed with status ${response.status}`);
      }

      const html = await response.text();
      const parser = new DOMParser();
      const nextDoc = parser.parseFromString(html, 'text/html');

      const replacedFilters = replaceSection(nextDoc, '.filters-panel');
      const replacedKpis = replaceSection(nextDoc, '.kpi-grid');
      const replacedInsights = replaceSection(nextDoc, '#insights-top');
      const replacedTrend = replaceSection(nextDoc, '#dual-axis-trend');
      const replacedFooter = replaceSection(nextDoc, '.footer');
      const currentHeader = document.querySelector('.page-header');
      const nextHeader = nextDoc.querySelector('.page-header');
      const replacedHeader =
        (!(currentHeader instanceof HTMLElement) && !(nextHeader instanceof HTMLElement))
        || replaceSection(nextDoc, '.page-header');

      if (!replacedFilters || !replacedKpis || !replacedInsights || !replacedTrend || !replacedFooter || !replacedHeader) {
        throw new Error('Unable to update all dashboard sections');
      }

      if (window.DashboardCharts && typeof window.DashboardCharts.renderTopEntityCharts === 'function') {
        window.DashboardCharts.renderTopEntityCharts(document);
      }
      if (window.DashboardCharts && typeof window.DashboardCharts.renderDualAxisChart === 'function') {
        window.DashboardCharts.renderDualAxisChart(document);
      }

      const nextUrl = `${actionUrl.pathname}${actionUrl.search}${window.location.hash}`;
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
