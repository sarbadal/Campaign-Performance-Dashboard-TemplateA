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

(() => {
  const canvas = document.getElementById('top-platforms-chart');
  if (!(canvas instanceof HTMLCanvasElement)) {
    return;
  }

  if (typeof Chart === 'undefined') {
    return;
  }

  const parseJsonArray = (raw) => {
    if (!raw) {
      return [];
    }

    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch (_err) {
      return [];
    }
  };

  const labelsRaw = parseJsonArray(canvas.dataset.labels);
  const valuesRaw = parseJsonArray(canvas.dataset.values);
  const displayValues = parseJsonArray(canvas.dataset.displayValues);
  const rowCount = Math.max(Number(canvas.dataset.rowCount) || 0, labelsRaw.length);
  const labels = labelsRaw.map((label) => String(label));
  const values = valuesRaw.map((value) => Number(value) || 0);

  if (!labels.length || !values.length) {
    return;
  }

  const kpiLabel = canvas.dataset.kpiLabel || 'KPI';
  const kpiKey = canvas.dataset.kpiKey || 'total_spend';
  const currencySymbol = (canvas.dataset.currencySymbol || '').trim();
  const styles = getComputedStyle(document.body);
  const barColor = (styles.getPropertyValue('--accent') || '#0b6e4f').trim() || '#0b6e4f';

  const isMoneyKpi = ['total_spend', 'avg_cpc', 'cpm', 'cvv'].includes(kpiKey);
  const isPercentKpi = kpiKey === 'avg_ctr_percent';
  const numberFormatInt = new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 });
  const numberFormatTwoDecimals = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const numberFormatCompact = new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  });

  const formatAxisValue = (rawValue) => {
    const value = Number(rawValue) || 0;

    if (isPercentKpi) {
      return `${numberFormatTwoDecimals.format(value)}%`;
    }

    if (isMoneyKpi) {
      const prefix = currencySymbol ? `${currencySymbol} ` : '';
      return `${prefix}${numberFormatCompact.format(value)}`;
    }

    return numberFormatCompact.format(value);
  };

  const barThickness = rowCount <= 3 ? 22 : rowCount <= 6 ? 18 : rowCount <= 8 ? 14 : 12;
  const categoryPercentage = rowCount <= 4 ? 0.9 : rowCount <= 7 ? 0.84 : 0.78;
  const barPercentage = rowCount <= 4 ? 0.92 : rowCount <= 7 ? 0.88 : 0.82;
  const wrapper = canvas.closest('.platform-chart-wrap');
  if (wrapper instanceof HTMLElement) {
    const perRow = barThickness + 14;
    const axisAndMargins = 64;
    const targetHeight = Math.max(160, (rowCount * perRow) + axisAndMargins);
    wrapper.style.height = `${targetHeight}px`;
  }

  // eslint-disable-next-line no-new
  new Chart(canvas, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: kpiLabel,
          data: values,
          backgroundColor: barColor,
          borderColor: '#2e8f74',
          borderWidth: 1,
          borderRadius: 6,
          borderSkipped: false,
          barThickness,
          maxBarThickness: barThickness,
          categoryPercentage,
          barPercentage,
        },
      ],
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      layout: {
        padding: {
          top: 8,
          right: 2,
          bottom: 8,
          left: 1,
        },
      },
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const idx = context.dataIndex;
              const pretty = displayValues[idx];
              if (typeof pretty === 'string' && pretty.trim()) {
                return `${kpiLabel}: ${pretty}`;
              }
              return `${kpiLabel}: ${context.formattedValue}`;
            },
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          grid: {
            color: '#e3e9e4',
          },
          ticks: {
            color: '#56605b',
            padding: 0,
            maxTicksLimit: 4,
            callback: (value) => formatAxisValue(value),
          },
        },
        y: {
          offset: true,
          grid: {
            display: false,
          },
          ticks: {
            color: '#23302a',
            font: {
              size: 12,
            },
          },
        },
      },
    },
  });
})();
