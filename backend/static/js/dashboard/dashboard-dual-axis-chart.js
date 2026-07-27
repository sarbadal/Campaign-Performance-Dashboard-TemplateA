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

  const isoTimestamp = () => (
    new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '_')
  );

  const withAlpha = (color, alpha) => {
    const raw = String(color || '').trim();
    const match = raw.match(/^#([\da-f]{3}|[\da-f]{6})$/i);
    if (!match) {
      return raw;
    }

    const hex = match[1];
    const normalized = hex.length === 3 ? hex.split('').map((ch) => ch + ch).join('') : hex;
    const r = Number.parseInt(normalized.slice(0, 2), 16);
    const g = Number.parseInt(normalized.slice(2, 4), 16);
    const b = Number.parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  registry.renderDualAxisChart = (root = document) => {
    const canvas = root.querySelector('#dual-axis-kpi-chart');
    if (!(canvas instanceof HTMLCanvasElement) || typeof Chart === 'undefined') {
      return;
    }

    if (canvas.dataset.chartInitialized === '1') {
      return;
    }

    canvas.dataset.chartInitialized = '1';

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
    const leftLineColorBase = (lineStyles.getPropertyValue('--accent') || '#0b6e4f').trim() || '#0b6e4f';
    const leftLineColor = withAlpha(leftLineColorBase, 0.65);
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
            borderWidth: 3,
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
            borderWidth: 1.75,
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
              color: leftLineColorBase,
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
  };

  const csvEscape = (value) => {
    const text = String(value ?? '');
    if (!/[",\n]/.test(text)) {
      return text;
    }
    return `"${text.replace(/"/g, '""')}"`;
  };

  const downloadDualAxisCsv = () => {
    const canvas = document.querySelector('#dual-axis-kpi-chart');
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }

    const labels = parseJsonArray(canvas.dataset.labels).map((item) => String(item));
    const leftValues = parseJsonArray(canvas.dataset.leftValues).map((item) => Number(item) || 0);
    const rightValues = parseJsonArray(canvas.dataset.rightValues).map((item) => Number(item) || 0);

    if (!labels.length || !leftValues.length || !rightValues.length) {
      return;
    }

    const leftKpiLabel = (canvas.dataset.leftKpiLabel || 'Left KPI').trim() || 'Left KPI';
    const rightKpiLabel = (canvas.dataset.rightKpiLabel || 'Right KPI').trim() || 'Right KPI';

    const rowCount = Math.min(labels.length, leftValues.length, rightValues.length);
    const lines = [
      [
        csvEscape('Date Bucket'),
        csvEscape(leftKpiLabel),
        csvEscape(rightKpiLabel),
      ].join(','),
    ];

    for (let i = 0; i < rowCount; i += 1) {
      lines.push([
        csvEscape(labels[i]),
        csvEscape(leftValues[i]),
        csvEscape(rightValues[i]),
      ].join(','));
    }

    const csv = `${lines.join('\n')}\n`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const timestamp = isoTimestamp();
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `dual_axis_kpi_trend_${timestamp}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const downloadDualAxisChartImage = (format = 'png') => {
    if (typeof Chart === 'undefined' || typeof Chart.getChart !== 'function') {
      return;
    }

    const canvas = document.querySelector('#dual-axis-kpi-chart');
    if (!(canvas instanceof HTMLCanvasElement)) {
      return;
    }

    const chart = Chart.getChart(canvas);
    if (!chart || typeof chart.toBase64Image !== 'function') {
      return;
    }

    const normalizedFormat = String(format || 'png').toLowerCase() === 'jpg' ? 'jpg' : 'png';
    const mimeType = normalizedFormat === 'jpg' ? 'image/jpeg' : 'image/png';
    const imageUrl = chart.toBase64Image(mimeType, 0.92);
    if (!imageUrl) {
      return;
    }

    const timestamp = isoTimestamp();
    const anchor = document.createElement('a');
    anchor.href = imageUrl;
    anchor.download = `dual_axis_kpi_trend_${timestamp}.${normalizedFormat}`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  if (!window.__dashboardDualAxisCsvBound) {
    window.__dashboardDualAxisCsvBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const downloadButton = target.closest('.dual-axis-download-btn');
      if (!(downloadButton instanceof HTMLButtonElement)) {
        const downloadImageButton = target.closest('.dual-axis-download-image-btn');
        if (!(downloadImageButton instanceof HTMLButtonElement)) {
          return;
        }

        event.preventDefault();
        downloadDualAxisChartImage(downloadImageButton.dataset.format || 'png');
        return;
      }

      event.preventDefault();
      downloadDualAxisCsv();
    });
  }

  window.DashboardCharts = registry;
})();
