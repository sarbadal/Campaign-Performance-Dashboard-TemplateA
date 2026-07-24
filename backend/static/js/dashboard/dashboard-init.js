(() => {
  if (window.DashboardCharts && typeof window.DashboardCharts.renderTopEntityCharts === 'function') {
    window.DashboardCharts.renderTopEntityCharts(document);
  }

  if (window.DashboardCharts && typeof window.DashboardCharts.renderDualAxisChart === 'function') {
    window.DashboardCharts.renderDualAxisChart(document);
  }
})();
