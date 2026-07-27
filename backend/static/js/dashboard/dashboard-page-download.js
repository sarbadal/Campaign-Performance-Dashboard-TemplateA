(() => {
  const rootSelector = 'main.container';

  const makeTimestamp = () => (
    new Date().toISOString().replace(/[-:]/g, '').replace(/\..+/, '').replace('T', '_')
  );

  const setButtonBusy = (button, busy, format) => {
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    if (!button.dataset.labelIdle) {
      button.dataset.labelIdle = button.textContent || '';
    }

    button.disabled = busy;
    if (busy) {
      button.textContent = `Preparing ${String(format || '').toUpperCase()}...`;
    } else {
      button.textContent = button.dataset.labelIdle || 'Download';
    }
  };

  const capturePageCanvas = async () => {
    const target = document.querySelector(rootSelector);
    if (!(target instanceof HTMLElement)) {
      throw new Error('Capture target not found.');
    }

    if (typeof window.html2canvas !== 'function') {
      throw new Error('html2canvas is not available.');
    }

    return window.html2canvas(target, {
      backgroundColor: '#f7f8f4',
      scale: 2,
      useCORS: true,
      scrollX: 0,
      scrollY: -window.scrollY,
      windowWidth: document.documentElement.scrollWidth,
      windowHeight: document.documentElement.scrollHeight,
    });
  };

  const downloadDataUrl = (dataUrl, filename) => {
    const anchor = document.createElement('a');
    anchor.href = dataUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
  };

  const downloadPng = async () => {
    const canvas = await capturePageCanvas();
    const dataUrl = canvas.toDataURL('image/png');
    downloadDataUrl(dataUrl, `dashboard_page_${makeTimestamp()}.png`);
  };

  const downloadPdf = async () => {
    const canvas = await capturePageCanvas();
    const dataUrl = canvas.toDataURL('image/png');

    const jsPdf = window.jspdf && window.jspdf.jsPDF;
    if (typeof jsPdf !== 'function') {
      throw new Error('jsPDF is not available.');
    }

    const pdf = new jsPdf('p', 'mm', 'a4');
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const margin = 8;
    const printableWidth = pageWidth - (margin * 2);
    const printableHeight = pageHeight - (margin * 2);

    const imageWidth = printableWidth;
    const imageHeight = (canvas.height * imageWidth) / canvas.width;

    let heightLeft = imageHeight;
    let y = margin;

    pdf.addImage(dataUrl, 'PNG', margin, y, imageWidth, imageHeight, undefined, 'FAST');
    heightLeft -= printableHeight;

    while (heightLeft > 0) {
      pdf.addPage();
      y = margin - (imageHeight - heightLeft);
      pdf.addImage(dataUrl, 'PNG', margin, y, imageWidth, imageHeight, undefined, 'FAST');
      heightLeft -= printableHeight;
    }

    pdf.save(`dashboard_page_${makeTimestamp()}.pdf`);
  };

  const handleBannerPageDownload = async (button) => {
    const format = String(button.dataset.downloadFormat || '').toLowerCase();
    if (!format) {
      return;
    }

    setButtonBusy(button, true, format);

    try {
      if (format === 'png') {
        await downloadPng();
      } else if (format === 'pdf') {
        await downloadPdf();
      }
    } catch (error) {
      // eslint-disable-next-line no-console
      console.error(error);
      window.alert('Unable to export page right now. Please try again.');
    } finally {
      setButtonBusy(button, false, format);
    }
  };

  if (!window.__dashboardPageDownloadBound) {
    window.__dashboardPageDownloadBound = true;
    document.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const button = target.closest('.banner-page-download-btn');
      if (!(button instanceof HTMLButtonElement)) {
        return;
      }

      event.preventDefault();
      void handleBannerPageDownload(button);
    });
  }
})();
