'use strict';
(() => {
  const PROJECT = 'wechat-article-scheduler';
  const API = '/__rr/v1/feedback';
  const KEY = 'rr-feedback:' + PROJECT + ':' + location.pathname;
  const $ = id => document.getElementById('feedback-' + id);
  const fields = ['description', 'expected', 'actual', 'steps'];
  const hex = /^[a-f0-9]{64}$/;
  const uuid = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
  const opaque = /^[A-Za-z0-9_-]{1,128}$/;
  const types = ['text/plain', 'image/png', 'image/jpeg', 'image/webp'];
  const encoder = new TextEncoder();
  let pending = null, blobs = [], busy = false, retryAllowed = false, synced = false, ready = false;
  const fail = message => { throw new Error(message); };
  const canonical = value => {
    if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
    return JSON.stringify(value);
  };
  const digest = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), n => n.toString(16).padStart(2, '0')).join('');
  const same = (a, b) => canonical(a) === canonical(b);
  function validPayload(p) {
    if (!p || p.schema !== 1 || p.project_id !== PROJECT || !uuid.test(p.client_request_id) ||
        p.page_path !== location.pathname || !p.source || !/^[a-f0-9]{40}(?:[a-f0-9]{24})?$/.test(p.source.commit) ||
        !hex.test(p.source.build_id) || typeof p.source.dirty !== 'boolean' || !p.resource ||
        !opaque.test(p.resource.id) || !hex.test(p.resource.sha256) || p.resource.mode !== 'readonly' ||
        typeof p.resource.preview_version !== 'string' || p.resource.preview_version.length > 128 ||
        typeof p.submitted_at !== 'string' || !p.submitted_at.endsWith('Z') || !Number.isFinite(Date.parse(p.submitted_at)) ||
        !Array.isArray(p.attachments) || p.attachments.length > 2 ||
        !fields.every(k => typeof p[k] === 'string' && p[k].length <= 6000 && !/[\u0000\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(p[k])) || !p.description.trim() ||
        !p.attachments.every(a => a && opaque.test(a.attachment_id) && Number.isInteger(a.size) && a.size >= 0 && a.size <= 1048576 && hex.test(a.sha256)) ||
        new Set(p.attachments.map(a => a.attachment_id)).size !== p.attachments.length ||
        encoder.encode(canonical(p)).length > 16384) fail('固定反馈格式无效；原存储不会被覆盖。');
  }
  function persist() {
    const previous = localStorage.getItem(KEY);
    if (previous && pending) {
      const stored = JSON.parse(previous);
      if (stored.payload.client_request_id !== pending.payload.client_request_id) fail('另一个页面保存了不同请求。请先恢复核对，避免覆盖。');
    }
    localStorage.setItem(KEY, JSON.stringify(pending));
  }
  function controls() {
    $('fields').disabled = busy || !!pending;
    $('prepare').disabled = busy || !!pending || !ready;
    $('new').disabled = busy;
    $('files').disabled = busy || synced;
    $('confirm').disabled = busy || !pending || synced;
    $('save').disabled = busy || !ready || !pending || synced || !$('confirm').checked ||
      blobs.length !== pending.payload.attachments.length || (pending.attempted && !retryAllowed);
    $('save').textContent = synced ? '已保存到项目' : (pending && pending.attempted ? '确认原请求未保存并重试' : '保存反馈到项目');
    $('reconcile').disabled = busy || !pending;
    $('refresh').disabled = busy;
  }
  function showContext() {
    if (!pending) return;
    $('context').textContent = JSON.stringify({正文与提交来源: pending.payload, 附件显示信息: pending.files}, null, 2);
    $('identifiers').textContent = '原请求：' + pending.payload.client_request_id + (pending.feedback_id ? '\n反馈编号：' + pending.feedback_id : '');
    $('preview').open = true;
    for (const name of fields) $(name).value = pending.payload[name];
    $('file-note').textContent = pending.payload.attachments.length ? '固定附件摘要已保留。刷新后须重新选择相同文件，校验通过才可重试。' : '本次固定反馈没有附件。';
  }
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 8000);
    try {
      const response = await fetch(path, {...options, signal: controller.signal, credentials: 'omit', cache: 'no-store', redirect: 'error'});
      if (response.status === 404) return {missing: true};
      if (!response.ok) fail('项目响应 ' + response.status + '；请保留原请求核对。');
      return await response.json();
    } finally { clearTimeout(timer); }
  }
  async function currentBinding() {
    const manifest = await request('/__rr/v1/manifest');
    const route = manifest.routes?.pages?.find(r => r.method === 'GET' && r.path === location.pathname);
    const asset = manifest.resources?.find(r => r.id === route?.resource_id);
    if (manifest.project_id !== PROJECT || !route || !asset ||
        manifest.source?.build_id !== document.querySelector('meta[name="rr-build"]').content) fail('页面版本已变化，请保留原反馈来源；重新加载后再开始新的反馈。');
    return {source: manifest.source, resource: Object.fromEntries(['id', 'sha256', 'mode', 'preview_version'].map(k => [k, asset[k]]))};
  }
  async function checkVersion() {
    const binding = await currentBinding();
    if (pending && (!same(binding.source, pending.payload.source) || !same(binding.resource, pending.payload.resource))) {
      fail('提交来源与当前页面版本不同，已保留旧来源，不能重新绑定或提交；仍可按原请求或反馈编号查询。');
    }
    return binding;
  }
  async function readFiles() {
    const files = Array.from($('files').files);
    if (files.length > 2) fail('最多选择两件附件。');
    const result = [];
    for (const file of files) {
      const mime = file.type || (/\.txt$/i.test(file.name) ? 'text/plain' : '');
      if (file.size > 1048576 || !types.includes(mime)) fail('附件大小或类型不符合限制。');
      const bytes = await file.arrayBuffer();
      if (mime === 'text/plain') new TextDecoder('utf-8', {fatal: true}).decode(bytes);
      result.push({blob: new Blob([bytes], {type: mime}), name: file.name, mime, size: file.size, sha256: await digest(bytes)});
    }
    return result;
  }
  async function verifyReceipt(value, expected = null) {
    if (!value || !uuid.test(value.feedback_id) || value.project_id !== PROJECT || value.schema !== 1 ||
        value.revision !== 1 || !hex.test(value.body_sha256) || !Array.isArray(value.attachments)) fail('项目回执格式无效，不能标记为已同步或已读。');
    const payload = Object.fromEntries(['schema', 'client_request_id', 'project_id', 'page_path', 'source', 'resource', ...fields, 'submitted_at'].map(k => [k, value[k]]));
    payload.attachments = value.attachments.map(a => ({attachment_id: a.attachment_id, size: a.size, sha256: a.sha256}));
    const hash = await digest(encoder.encode(canonical(payload)));
    if (hash !== value.body_sha256 || hash !== value.payload_sha256 || (expected && !same(payload, expected))) fail('回执正文、附件或来源与原请求不符；仍需核对。');
    if (!['pending', 'agent_read', 'processed'].includes(value.status)) fail('未知项目状态。');
    if (value.status !== 'pending') {
      const ack = value.ack;
      if (!ack || ack.revision !== value.revision || ack.body_sha256 !== hash ||
          !same(ack.attachments, value.attachments.map(a => ({attachment_id: a.attachment_id, sha256: a.sha256})))) fail('缺少匹配正文及附件的实际Agent确认。');
    }
    if (value.status === 'processed' && (!value.result || value.result.revision !== value.revision || typeof value.result.description !== 'string')) fail('缺少项目保存的处理结果。');
    return value;
  }
  function statusText(receipt) {
    return {pending: '已同步待Agent读取', agent_read: 'Agent已读', processed: 'Agent已处理'}[receipt.status];
  }
  function resultText(value) {
    return value.result ? '处理说明：' + value.result.description + '\n结果引用：' + value.result.reference + '\n处理时间：' + value.result.processed_at : '';
  }
  async function accept(value) {
    await verifyReceipt(value, pending.payload);
    if (pending.feedback_id && value.feedback_id !== pending.feedback_id) fail('回执反馈编号与原已保存编号不同，仍需核对。');
    pending.feedback_id = value.feedback_id;
    persist(); synced = true; retryAllowed = false;
    $('status').textContent = statusText(value);
    $('result').textContent = resultText(value);
    $('lookup').value = value.feedback_id;
    $('version').textContent = '提交来源：' + value.source.build_id.slice(0, 12) + '（完整版本见固定内容）；查询不会改写来源或重复保存。';
    showContext();
  }
  async function action(fn, target = 'status') {
    if (busy) return;
    busy = true; controls();
    try { await fn(); }
    catch (error) { $(target).textContent = (pending?.attempted && target === 'status' ? '失败待核对：' : '') + (error instanceof Error ? error.message : '请求失败，请手动核对。'); }
    finally { busy = false; controls(); }
  }
  $('prepare').addEventListener('click', () => action(async () => {
    if (!$('form').reportValidity()) return;
    const binding = await checkVersion();
    const selected = await readFiles();
    const payload = {schema: 1, project_id: PROJECT, client_request_id: crypto.randomUUID(), page_path: location.pathname,
      ...binding, ...Object.fromEntries(fields.map(k => [k, $(k).value])), submitted_at: new Date().toISOString(),
      attachments: selected.map(f => ({attachment_id: crypto.randomUUID(), size: f.size, sha256: f.sha256}))};
    validPayload(payload);
    pending = {payload, payload_sha256: await digest(encoder.encode(canonical(payload))),
      files: selected.map(({name, mime}) => ({name, mime})), attempted: false};
    try { persist(); } catch (error) { pending = null; throw error; }
    blobs = selected.map(f => f.blob); synced = false; retryAllowed = false;
    $('status').textContent = '未同步：已固定本次反馈，请检查并确认保存。'; showContext();
  }));
  $('confirm').addEventListener('change', controls);
  $('files').addEventListener('change', () => { if (pending) action(async () => {
    blobs = [];
    const selected = await readFiles();
    if (selected.length !== pending.payload.attachments.length || !selected.every((f, i) =>
      f.size === pending.payload.attachments[i].size && f.sha256 === pending.payload.attachments[i].sha256 && f.mime === pending.files[i].mime)) fail('重新选择的附件与原摘要/类型不一致，原反馈未更改。');
    blobs = selected.map(f => f.blob); $('file-note').textContent = '相同附件已重新选择，全部长度、SHA和类型匹配。';
  }); });
  $('form').addEventListener('submit', event => { event.preventDefault(); if ($('save').disabled) return; action(async () => {
    await checkVersion();
    if (pending.attempted && !retryAllowed) fail('请先按原请求核对，不能直接重发。');
    pending.attempted = true; persist(); retryAllowed = false;
    $('status').textContent = '同步中：正在等待项目持久回执。';
    const data = new FormData(); data.append('feedback', new Blob([canonical(pending.payload)], {type: 'application/json'}));
    blobs.forEach((blob, i) => data.append('attachment.' + i, blob, 'selected-' + i));
    const receipt = await request(API, {method: 'POST', body: data});
    if (receipt.missing) fail('项目未提供保存回执；请按原请求核对。');
    await accept(receipt);
  }); });
  $('reconcile').addEventListener('click', () => action(async () => {
    retryAllowed = false;
    const value = await request(API + '/by-request/' + pending.payload.client_request_id);
    if (value.missing) {
      synced = false;
      try { await checkVersion(); retryAllowed = true; }
      catch (error) { $('version').textContent = error.message; throw error; }
      $('status').textContent = '未同步：按原请求查询未找到记录。可明确选择按相同请求重试；不会自动重发。';
    } else await accept(value);
  }));
  $('refresh').addEventListener('click', () => action(async () => {
    $('lookup-result').textContent = '';
    const id = $('lookup').value.trim();
    if (!opaque.test(id)) fail('请输入有效反馈编号。');
    $('lookup-status').textContent = '正在查询项目保存的状态。';
    const value = await request(API + '/' + encodeURIComponent(id));
    if (value.missing) fail('没有查到该设备的此条反馈；未核实状态。');
    if (value.feedback_id !== id) fail('回执反馈编号与查询编号不同；未核实状态。');
    await verifyReceipt(value);
    if (pending && value.client_request_id === pending.payload.client_request_id) await accept(value);
    $('lookup-status').textContent = statusText(value);
    $('lookup-result').textContent = '反馈编号：' + value.feedback_id + '\n提交页面：' + value.page_path + '\n提交来源：' + value.source.build_id +
      (value.source.build_id === document.querySelector('meta[name="rr-build"]').content ? '\n当前页面版本' : '\n此前版本；保留原提交来源') +
      '\n问题：' + value.description + '\n' + resultText(value);
  }, 'lookup-status'));
  $('new').addEventListener('click', () => {
    if (pending && !confirm('开始新的反馈会清除本浏览器保存的这份核对上下文。项目已保存的反馈仍可按编号查询。确定继续？')) return;
    localStorage.removeItem(KEY); pending = null; blobs = []; synced = false; retryAllowed = false; ready = true;
    $('form').reset(); $('context').textContent = '尚未固定反馈。'; $('identifiers').textContent = '尚无请求。';
    $('result').textContent = ''; $('status').textContent = '未同步：尚未固定反馈。'; $('version').textContent = ''; controls();
  });
  action(async () => {
    const saved = localStorage.getItem(KEY);
    if (saved) {
      const record = JSON.parse(saved); validPayload(record.payload);
      if (record.payload_sha256 !== await digest(encoder.encode(canonical(record.payload))) ||
          !Array.isArray(record.files) || record.files.length !== record.payload.attachments.length ||
          !record.files.every(f => typeof f.name === 'string' && types.includes(f.mime)) || typeof record.attempted !== 'boolean') fail('恢复上下文校验失败；不会覆盖原存储。');
      pending = record; showContext();
      $('status').textContent = record.attempted ? '失败待核对：已恢复原请求，请手动按原请求核对。' : '未同步：已恢复固定请求，请检查；附件需重新选择。';
    }
    ready = true;
    try { await checkVersion(); }
    catch (error) { $('version').textContent = error.message; }
  });
})();
