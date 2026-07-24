(() => {
  const registry = window.DashboardSync || {};

  registry.syncTopChartHiddenTrendFields = (sourceDoc) => {
    if (!(sourceDoc instanceof Document)) {
      return;
    }

    const nextDualAxisForm = sourceDoc.querySelector('.dual-axis-form');
    if (!(nextDualAxisForm instanceof HTMLFormElement)) {
      return;
    }

    const names = ['line_kpi_left', 'line_kpi_right', 'line_granularity'];
    const currentTopForms = Array.from(document.querySelectorAll('.top-chart-kpi-form'));
    for (const form of currentTopForms) {
      if (!(form instanceof HTMLFormElement)) {
        continue;
      }

      for (const name of names) {
        const currentInput = form.querySelector(`input[name="${name}"]`);
        const nextInput = nextDualAxisForm.querySelector(`select[name="${name}"]`);
        if (currentInput instanceof HTMLInputElement && nextInput instanceof HTMLSelectElement) {
          currentInput.value = nextInput.value;
        }
      }
    }
  };

  registry.syncDualAxisHiddenTopKpis = (sourceDoc) => {
    if (!(sourceDoc instanceof Document)) {
      return;
    }

    const currentDualAxisForm = document.querySelector('.dual-axis-form');
    if (!(currentDualAxisForm instanceof HTMLFormElement)) {
      return;
    }

    const nextDualAxisForm = sourceDoc.querySelector('.dual-axis-form');
    if (!(nextDualAxisForm instanceof HTMLFormElement)) {
      return;
    }

    const names = ['top_kpi_adset', 'top_kpi_platform'];
    for (const name of names) {
      const currentInput = currentDualAxisForm.querySelector(`input[name="${name}"]`);
      const nextInput = nextDualAxisForm.querySelector(`input[name="${name}"]`);
      if (currentInput instanceof HTMLInputElement && nextInput instanceof HTMLInputElement) {
        currentInput.value = nextInput.value;
      }
    }
  };

  window.DashboardSync = registry;
})();
