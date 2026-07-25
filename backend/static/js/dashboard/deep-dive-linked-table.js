(() => {
  const linkedBody = document.getElementById('deep-dive-linked-body');
  const linkedMeta = document.getElementById('deep-dive-linked-meta');
  const linkedTable = document.getElementById('deep-dive-linked-table');
  const linkedDownloadButton = document.getElementById('deep-dive-linked-download-btn');
  if (!(linkedBody instanceof HTMLElement) || !(linkedTable instanceof HTMLTableElement)) {
    return;
  }

  const sourceContainer = document.querySelector('.panel[aria-label="Deep dive data table"]');
  if (!(sourceContainer instanceof HTMLElement)) {
    return;
  }

  const buildStateKey = () => {
    const params = new URLSearchParams(window.location.search);
    params.delete('page');
    params.delete('page_size');
    const normalized = Array.from(params.entries())
      .sort(([aKey, aValue], [bKey, bValue]) => {
        const keyCompare = aKey.localeCompare(bKey);
        return keyCompare !== 0 ? keyCompare : aValue.localeCompare(bValue);
      })
      .map(([key, value]) => `${key}=${value}`)
      .join('&');
    return `deep-dive-linked-table:${normalized}`;
  };

  const stateKey = buildStateKey();
  const expandStateKey = `${stateKey}:expanded`;
  const shouldRestoreExpandedState = new URLSearchParams(window.location.search).get('keep_expanded') === '1';

  const saveState = (rows, sourceLabel) => {
    try {
      sessionStorage.setItem(
        stateKey,
        JSON.stringify({
          rows,
          sourceLabel,
        })
      );
    } catch (_err) {
      // Ignore storage failures.
    }
  };

  const loadState = () => {
    try {
      const raw = sessionStorage.getItem(stateKey);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.rows)) {
        return null;
      }
      return {
        rows: parsed.rows.filter((item) => Array.isArray(item)).map((item) => item.map((value) => String(value))),
        sourceLabel: String(parsed.sourceLabel || 'saved'),
      };
    } catch (_err) {
      return null;
    }
  };

  const loadExpandedState = () => {
    try {
      const raw = sessionStorage.getItem(expandStateKey);
      if (!raw) {
        return null;
      }
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) {
        return null;
      }
      return new Set(parsed.map((item) => String(item)));
    } catch (_err) {
      return null;
    }
  };

  const saveExpandedState = (keys) => {
    try {
      sessionStorage.setItem(expandStateKey, JSON.stringify(Array.from(keys)));
    } catch (_err) {
      // Ignore storage failures.
    }
  };

  const getRowsFromTable = (table) => {
    if (!(table instanceof HTMLTableElement)) {
      return [];
    }
    return Array.from(table.querySelectorAll('tbody tr.deep-dive-primary-row'));
  };

  const getRowValues = (row) => {
    return Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim() || '');
  };

  const csvEscape = (value) => {
    const normalized = String(value ?? '');
    if (normalized.includes('"') || normalized.includes(',') || normalized.includes('\n')) {
      return `"${normalized.replace(/"/g, '""')}"`;
    }
    return normalized;
  };

  const downloadLinkedTableCsv = () => {
    const headerCells = Array.from(linkedTable.querySelectorAll('thead th'));
    const bodyRows = Array.from(linkedTable.querySelectorAll('tbody tr'));

    const header = headerCells.map((cell) => csvEscape(cell.textContent?.trim() || '')).join(',');
    const lines = [header];

    for (const row of bodyRows) {
      const cells = Array.from(row.querySelectorAll('td'));
      if (cells.length === 1 && cells[0].classList.contains('empty-state')) {
        continue;
      }
      lines.push(cells.map((cell) => csvEscape(cell.textContent?.trim() || '')).join(','));
    }

    const csvContent = `${lines.join('\n')}\n`;
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `deep_dive_linked_table_${new Date().toISOString().replace(/[:.]/g, '-')}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  };

  const getDetailTitle = (detailsNode) => {
    if (!(detailsNode instanceof HTMLDetailsElement)) {
      return '';
    }
    const titleEl = detailsNode.querySelector(':scope > summary .drill-title');
    return titleEl?.textContent?.trim() || '';
  };

  const getDetailsKey = (detailsNode) => {
    if (!(detailsNode instanceof HTMLDetailsElement)) {
      return '';
    }

    const parts = [];
    let cursor = detailsNode;
    while (cursor instanceof HTMLDetailsElement) {
      const title = getDetailTitle(cursor);
      if (title) {
        parts.unshift(title);
      }
      const parentDetails = cursor.parentElement?.closest('details.drill-node');
      if (!(parentDetails instanceof HTMLDetailsElement)) {
        break;
      }
      cursor = parentDetails;
    }
    return parts.join(' > ');
  };

  const getExpandedDetailsKeys = () => {
    const detailsNodes = Array.from(sourceContainer.querySelectorAll('.drill-tree details.drill-node'));
    const keys = new Set();
    for (const node of detailsNodes) {
      if (!(node instanceof HTMLDetailsElement) || !node.open) {
        continue;
      }
      const key = getDetailsKey(node);
      if (key) {
        keys.add(key);
      }
    }
    return keys;
  };

  const restoreExpandedDetails = () => {
    const saved = loadExpandedState();
    if (!(saved instanceof Set) || saved.size === 0) {
      return;
    }

    const detailsNodes = Array.from(sourceContainer.querySelectorAll('.drill-tree details.drill-node'));
    for (const node of detailsNodes) {
      if (!(node instanceof HTMLDetailsElement)) {
        continue;
      }
      const key = getDetailsKey(node);
      if (key && saved.has(key)) {
        node.open = true;
      }
    }
  };

  const renderFromValues = (rows, sourceLabel, persist = true) => {
    linkedBody.innerHTML = '';

    if (rows.length === 0) {
      const colCount = Math.max(linkedTable.tHead?.rows?.[0]?.cells?.length || 1, 1);
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = colCount;
      td.className = 'empty-state';
      td.textContent = 'No rows selected. Expand nodes or click rows in the first table.';
      tr.appendChild(td);
      linkedBody.appendChild(tr);
      if (linkedMeta) {
        linkedMeta.textContent = 'Showing 0 rows from expanded or selected data';
      }
      if (persist) {
        saveState([], sourceLabel);
      }
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const values of rows) {
      const tr = document.createElement('tr');
      for (const value of values) {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
      }
      fragment.appendChild(tr);
    }
    linkedBody.appendChild(fragment);

    if (linkedMeta) {
      linkedMeta.textContent = `Showing ${rows.length} rows from ${sourceLabel} data`;
    }

    if (persist) {
      saveState(rows, sourceLabel);
    }
  };

  const isHierarchyVisible = () => {
    return !!sourceContainer.querySelector('.drill-tree');
  };

  const isRowInOpenDetailsPath = (row) => {
    let node = row.parentElement;
    while (node) {
      if (node instanceof HTMLDetailsElement && !node.open) {
        return false;
      }
      node = node.parentElement;
    }
    return true;
  };

  const collectExpandedHierarchyRows = () => {
    const rows = Array.from(sourceContainer.querySelectorAll('.drill-tree tbody tr.deep-dive-primary-row'));
    return rows.filter((row) => isRowInOpenDetailsPath(row));
  };

  const collectFlatRows = () => {
    const table = sourceContainer.querySelector('table[aria-label="Deep dive campaign data table"]');
    return getRowsFromTable(table);
  };

  const getSourceRows = () => {
    if (isHierarchyVisible()) {
      return collectExpandedHierarchyRows();
    }
    return collectFlatRows();
  };

  const renderLinkedRows = () => {
    const selectedRows = Array.from(sourceContainer.querySelectorAll('tr.deep-dive-primary-row.is-selected'));
    const sourceRows = selectedRows.length > 0 ? selectedRows : getSourceRows();
    const values = sourceRows.map((row) => getRowValues(row));
    const sourceLabel = selectedRows.length > 0 ? 'selected' : 'expanded';
    renderFromValues(values, sourceLabel, true);
  };

  sourceContainer.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    const row = target.closest('tr.deep-dive-primary-row');
    if (!(row instanceof HTMLTableRowElement)) {
      return;
    }
    row.classList.toggle('is-selected');
    renderLinkedRows();
  });

  sourceContainer.addEventListener('toggle', () => {
    saveExpandedState(getExpandedDetailsKeys());
    renderLinkedRows();
  }, true);

  if (linkedDownloadButton instanceof HTMLButtonElement) {
    linkedDownloadButton.addEventListener('click', () => {
      downloadLinkedTableCsv();
    });
  }

  if (shouldRestoreExpandedState) {
    restoreExpandedDetails();
  }

  const savedState = loadState();
  if (savedState && savedState.rows.length > 0) {
    renderFromValues(savedState.rows, savedState.sourceLabel || 'saved', false);
  } else {
    renderLinkedRows();
  }

  // Ensure an initial expansion snapshot exists for pagination persistence.
  saveExpandedState(getExpandedDetailsKeys());
})();
