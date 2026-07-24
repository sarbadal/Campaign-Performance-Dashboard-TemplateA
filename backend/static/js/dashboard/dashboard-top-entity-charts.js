(() => {
  const registry = window.DashboardCharts || {};

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

  const csvEscape = (value) => {
    const text = String(value ?? '');
    if (!/[",\n]/.test(text)) {
      return text;
    }
    return `"${text.replace(/"/g, '""')}"`;
  };

  registry.renderTopEntityCharts = (root = document) => {
    const canvases = Array.from(root.querySelectorAll('.top-entity-chart'));
    if (!canvases.length || typeof Chart === 'undefined') {
      return;
    }

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
      return `${text.slice(0, maxItemLabelLength - 1)}...`;
    };

    for (const canvas of canvases) {
      if (!(canvas instanceof HTMLCanvasElement)) {
        continue;
      }

      if (canvas.dataset.chartInitialized === '1') {
        continue;
      }

      canvas.dataset.chartInitialized = '1';

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
  };

  const downloadTopEntityCsv = (chartKey) => {
    const safeKey = String(chartKey || '').trim();
    if (!safeKey) {
      return;
    }

    const canvas = document.querySelector(`#top-entity-chart-${CSS.escape(safeKey)}`);
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }

    const labels = parseJsonArray(canvas.dataset.labels).map((item) => String(item));
    const values = parseJsonArray(canvas.dataset.values).map((item) => Number(item) || 0);
    if (!labels.length || !values.length) {
      return;
    }

    const panel = canvas.closest('.panel');
    const title = panel?.querySelector('.panel-header')?.textContent?.trim() || safeKey;
    const entityColumn = title.match(/^Top\s+\d+\s+(.+?)\s+by\s+/i)?.[1] || 'Entity';
    const kpiLabel = (canvas.dataset.kpiLabel || 'KPI').trim() || 'KPI';

    const rowCount = Math.min(labels.length, values.length);
    const lines = [
      [csvEscape(entityColumn), csvEscape(kpiLabel)].join(','),
    ];

    for (let i = 0; i < rowCount; i += 1) {
      lines.push([
        csvEscape(labels[i]),
        csvEscape(values[i]),
      ].join(','));
    }

    const csv = `${lines.join('\n')}\n`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '_');
    const normalizedKey = safeKey.replace(/[^a-zA-Z0-9_-]/g, '_');
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `top_${normalizedKey}_${timestamp}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  if (!window.__dashboardTopEntityCsvBound) {
    window.__dashboardTopEntityCsvBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const downloadButton = target.closest('.top-entity-download-btn');
      if (!(downloadButton instanceof HTMLButtonElement)) {
        return;
      }

      event.preventDefault();
      downloadTopEntityCsv(downloadButton.dataset.chartKey || '');
    });
  }

  window.DashboardCharts = registry;
})();
