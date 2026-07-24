(() => {
  const dropdowns = Array.from(document.querySelectorAll('.multi-dropdown'));
  if (!dropdowns.length) {
    return;
  }

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

(() => {
  const canvases = Array.from(document.querySelectorAll('.top-entity-chart'));
  if (!canvases.length) {
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

  const parseJsonObject = (raw) => {
    if (!raw) {
      return {};
    }

    try {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        return parsed;
      }
      return {};
    } catch (_err) {
      return {};
    }
  };

  const styles = getComputedStyle(document.body);
  const defaultBarColor = (styles.getPropertyValue('--accent') || '#0b6e4f').trim() || '#0b6e4f';
  const maxItemLabelLength = 22;

  const truncateLabel = (value) => {
    const text = String(value || '').trim();
    if (!text) {
      return '';
    }
    if (text.length <= maxItemLabelLength) {
      return text;
    }
    return `${text.slice(0, maxItemLabelLength - 1)}…`;
  };

  for (const canvas of canvases) {
    if (!(canvas instanceof HTMLCanvasElement)) {
      continue;
    }

    const labelsRaw = parseJsonArray(canvas.dataset.labels);
    const valuesRaw = parseJsonArray(canvas.dataset.values);
    const displayValues = parseJsonArray(canvas.dataset.displayValues);
    const configuredEntityColors = parseJsonObject(canvas.dataset.entityColors);
    const configuredDefaultColor = String(canvas.dataset.defaultColor || '').trim();
    const rowCount = Math.max(Number(canvas.dataset.rowCount) || 0, labelsRaw.length);
    const labels = labelsRaw.map((label) => String(label));
    const values = valuesRaw.map((value) => Number(value) || 0);

    if (!labels.length || !values.length) {
      continue;
    }

    const kpiLabel = canvas.dataset.kpiLabel || 'KPI';
    const kpiKey = canvas.dataset.kpiKey || 'total_spend';
    const currencySymbol = (canvas.dataset.currencySymbol || '').trim();
    const resolvedDefaultBarColor = configuredDefaultColor || defaultBarColor;

    const normalizedEntityColors = new Map(
      Object.entries(configuredEntityColors)
        .filter(([entity, color]) => typeof entity === 'string' && typeof color === 'string')
        .map(([entity, color]) => [entity.trim().toLowerCase(), color.trim()])
        .filter(([entity, color]) => entity && color)
    );

    const resolveEntityColor = (entityLabel) => {
      const key = String(entityLabel || '').trim().toLowerCase();
      if (!key) {
        return resolvedDefaultBarColor;
      }
      return normalizedEntityColors.get(key) || resolvedDefaultBarColor;
    };

    const barColors = labels.map((label) => resolveEntityColor(label));

    const isMoneyKpi = ['total_spend', 'avg_cpc', 'cpm', 'cvv'].includes(kpiKey);
    const isPercentKpi = kpiKey === 'avg_ctr_percent';
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
    const wrapper = canvas.closest('.top-entity-chart-wrap');
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
            backgroundColor: barColors,
            borderColor: barColors,
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
              title: (items) => {
                const first = Array.isArray(items) ? items[0] : null;
                return first?.label ? String(first.label) : '';
              },
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
              callback: (_value, index) => {
                const label = labels[index] || '';
                return truncateLabel(label);
              },
            },
          },
        },
      },
    });
  }
})();

(() => {
  const canvas = document.getElementById('dual-axis-kpi-chart');
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

  const labels = parseJsonArray(canvas.dataset.labels).map((item) => String(item));
  const leftValues = parseJsonArray(canvas.dataset.leftValues).map((item) => Number(item) || 0);
  const rightValues = parseJsonArray(canvas.dataset.rightValues).map((item) => Number(item) || 0);

  if (!labels.length || !leftValues.length || !rightValues.length) {
    return;
  }

  const leftKpiKey = canvas.dataset.leftKpiKey || 'total_spend';
  const rightKpiKey = canvas.dataset.rightKpiKey || 'total_impressions';
  const leftKpiLabel = canvas.dataset.leftKpiLabel || 'Left KPI';
  const rightKpiLabel = canvas.dataset.rightKpiLabel || 'Right KPI';
  const currencySymbol = (canvas.dataset.currencySymbol || '').trim();

  const isMoneyKpi = (kpiKey) => ['total_spend', 'avg_cpc', 'cpm', 'cvv'].includes(kpiKey);
  const isPercentKpi = (kpiKey) => kpiKey === 'avg_ctr_percent';

  const numberFormatTwoDecimals = new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const numberFormatCompact = new Intl.NumberFormat('en-US', {
    notation: 'compact',
    compactDisplay: 'short',
    maximumFractionDigits: 1,
  });

  const formatValue = (value, kpiKey) => {
    const numeric = Number(value) || 0;

    if (isPercentKpi(kpiKey)) {
      return `${numberFormatTwoDecimals.format(numeric)}%`;
    }

    if (isMoneyKpi(kpiKey)) {
      const prefix = currencySymbol ? `${currencySymbol} ` : '';
      return `${prefix}${numberFormatCompact.format(numeric)}`;
    }

    return numberFormatCompact.format(numeric);
  };

  const lineStyles = getComputedStyle(document.body);
  const leftLineColor = (lineStyles.getPropertyValue('--accent') || '#0b6e4f').trim() || '#0b6e4f';
  const rightLineColor = '#d97706';
  const wrapper = canvas.closest('.dual-axis-chart-wrap');
  if (wrapper instanceof HTMLElement) {
    wrapper.style.height = '340px';
  }

  // eslint-disable-next-line no-new
  new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: leftKpiLabel,
          data: leftValues,
          yAxisID: 'yLeft',
          borderColor: leftLineColor,
          backgroundColor: 'rgba(11, 110, 79, 0.16)',
          cubicInterpolationMode: 'monotone',
          tension: 0.58,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4,
        },
        {
          label: rightKpiLabel,
          data: rightValues,
          yAxisID: 'yRight',
          borderColor: rightLineColor,
          backgroundColor: 'rgba(217, 119, 6, 0.16)',
          cubicInterpolationMode: 'monotone',
          tension: 0.58,
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 4,
        },
      ],
    },
    options: {
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      plugins: {
        legend: {
          display: true,
          position: 'top',
        },
        tooltip: {
          callbacks: {
            label: (context) => {
              const kpiKey = context.dataset.yAxisID === 'yLeft' ? leftKpiKey : rightKpiKey;
              return `${context.dataset.label}: ${formatValue(context.parsed.y, kpiKey)}`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            color: '#e3e9e4',
          },
          ticks: {
            color: '#56605b',
            maxTicksLimit: 10,
          },
        },
        yLeft: {
          type: 'linear',
          position: 'left',
          beginAtZero: true,
          grid: {
            color: '#e3e9e4',
          },
          ticks: {
            color: leftLineColor,
            callback: (value) => formatValue(value, leftKpiKey),
          },
        },
        yRight: {
          type: 'linear',
          position: 'right',
          beginAtZero: true,
          grid: {
            drawOnChartArea: false,
          },
          ticks: {
            color: rightLineColor,
            callback: (value) => formatValue(value, rightKpiKey),
          },
        },
      },
    },
  });
})();
