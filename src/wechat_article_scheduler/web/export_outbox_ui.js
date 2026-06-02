/** 作品卡与详情页共用的 export-outbox 成功 toast 文案（由 /assets/export-outbox-ui.js 提供）。 */
window.ExportOutboxUi = (function () {
  const WARN_TEXT =
    '未自动发布：仅生成本地 outbox，需您人工上传到目标平台。';

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(
      /[&<>"']/g,
      (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]),
    );
  }

  function resolvePlatformLabel(data, platformLabel) {
    return platformLabel || data.platform_label || data.platform || '通用';
  }

  function buildSuccessHtml(data, platformLabel, esc) {
    const escFn = esc || escapeHtml;
    const label = escFn(resolvePlatformLabel(data, platformLabel));
    const path = data.relative_path || data.outbox_path || '';
    const pathBlock = path
      ? `<div class="export-toast-path">路径：<code>${escFn(path)}</code></div>`
      : '';
    return (
      '<div class="alert ok export-outbox-toast">' +
      `<div class="export-toast-title">已导出 <b>「${label}」</b> outbox 包</div>` +
      `<div class="export-toast-warn"><b>⚠ ${escFn(WARN_TEXT)}</b></div>` +
      pathBlock +
      '</div>'
    );
  }

  function buildSuccessPlainText(data, platformLabel) {
    const label = resolvePlatformLabel(data, platformLabel);
    const path = data.relative_path || data.outbox_path || '';
    return [
      `已导出「${label}」outbox 包`,
      WARN_TEXT,
      path ? `路径：${path}` : '',
    ]
      .filter(Boolean)
      .join('\n');
  }

  function showInElement(element, data, platformLabel, esc) {
    if (!element) return;
    element.innerHTML = buildSuccessHtml(data, platformLabel, esc);
    element.hidden = false;
  }

  return {
    WARN_TEXT,
    buildSuccessHtml,
    buildSuccessPlainText,
    showInElement,
  };
})();
