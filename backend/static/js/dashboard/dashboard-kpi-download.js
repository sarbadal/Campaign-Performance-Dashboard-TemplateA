(() => {
  const csvEscape = (value) => {
    const text = String(value ?? '');
    if (!/[",\n]/.test(text)) {
      return text;
    }
    return `"${text.replace(/"/g, '""')}"`;
  };

  const stripCurrencyPrefix = (value) => {
    let text = String(value ?? '').trim();
    if (!text) {
      return text;
    }

    // Remove leading currency symbols like $, EUR symbol variants, etc.
    text = text.replace(/^[\$€£¥₹₩₽₺₫₴₦฿₪₱₡₲₵₭₮₤₼₾₨]\s*/u, '');
    // Remove leading currency codes like RM, USD, EUR when followed by whitespace.
    text = text.replace(/^[A-Za-z]{1,4}\s+/, '');
    return text.trim();
  };

  const downloadKpiCsv = () => {
    const cards = Array.from(document.querySelectorAll('.kpi-grid .card'));
    if (!cards.length) {
      return;
    }

    const rows = [['KPI', 'Value'].join(',')];
    for (const card of cards) {
      if (!(card instanceof HTMLElement)) {
        continue;
      }

      const label = card.querySelector('.label')?.textContent?.trim() || '';
      const valueRaw = card.querySelector('.value')?.textContent?.trim() || '';
      const value = stripCurrencyPrefix(valueRaw);
      rows.push([csvEscape(label), csvEscape(value)].join(','));
    }

    const csv = `${rows.join('\n')}\n`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const timestamp = new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '_');
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `kpi_summary_${timestamp}.csv`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  if (!window.__dashboardKpiCsvBound) {
    window.__dashboardKpiCsvBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const button = target.closest('.kpi-download-btn');
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }

      event.preventDefault();
      downloadKpiCsv();
    });
  }
})();
