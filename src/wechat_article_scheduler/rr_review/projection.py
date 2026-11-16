"""Explicit frozen SSR projection of an allowlisted synthetic workbench instance."""
from html import escape
import os
from pathlib import Path
import re
import stat

from wechat_article_scheduler.web.queue_display import list_queue_jobs
from wechat_article_scheduler.web.article_detail import build_article_detail
from wechat_article_scheduler.web.user_copy import label_article_status
from .protocol import PROJECT, canonical, need, sha

INDEX = '/__rr/wechat/'
CSS_PATH = '/__rr/wechat/workbench.css'
JS_PATH = '/__rr/wechat/feedback.js'
PUBLIC_ARTICLES = [
    {'id': 1, 'title': '合成示例：把文章放进草稿工作台', 'summary': '演练文章导入、去重与排期核对。',
     'body': '这是一篇公开构造的演练文章。\n先核对标题和正文，再查看本地排期。\n未读取用户文章，未调用微信接口。', 'status': 'imported'},
    {'id': 2, 'title': '合成示例：草稿完成后的人工确认', 'summary': '本地演练草稿不代表公众号后台已有内容。',
     'body': '演练草稿只存在于本次合成数据库。\n最终发布须用户在公众号后台完成，再回填真实证明。', 'status': 'imported'},
]
CSS = '''/* Reuses the original workbench palette and system type stack. */
:root{color-scheme:light;--bg:#fbfbfa;--surface:#fff;--text:#202020;--muted:#73726e;--line:#e8e6e1;--accent:#2f3437}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 system-ui,"PingFang SC","Microsoft YaHei",sans-serif}
header,main,footer{max-width:1080px;margin:auto;padding:24px}header{border-bottom:1px solid var(--line)}nav{display:flex;gap:20px;flex-wrap:wrap}
a{color:var(--accent);text-underline-offset:4px}a:focus-visible{outline:3px solid #287a4b;outline-offset:4px}h1{font-size:28px;line-height:1.3}
.notice{background:#fbf3dd;padding:16px;border-radius:10px}section,article{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px;margin:20px 0}
.meta{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:16px}.grid article{margin:0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}li{margin:10px 0}@media(max-width:600px){header,main,footer{padding:16px}h1{font-size:24px}}
fieldset{border:0;padding:0;min-width:0}legend{font-weight:600;margin-bottom:12px}label{display:block;margin:14px 0 6px}
textarea,input[type=text]{display:block;width:100%;padding:10px;border:1px solid #73726e;border-radius:6px;font:inherit;background:white;color:var(--text)}
textarea{min-height:90px;resize:vertical}input[type=file]{max-width:100%;font:inherit}button{padding:10px 14px;margin:8px 6px 8px 0;font:inherit;border:1px solid #73726e;border-radius:6px;background:white;color:var(--text);cursor:pointer}
button:disabled{cursor:default;color:#73726e;background:#f6f6f4}button:focus-visible,input:focus-visible,textarea:focus-visible,summary:focus-visible{outline:3px solid #287a4b;outline-offset:3px}
.review-check{display:flex;gap:10px;align-items:flex-start}.review-check input{width:20px;height:20px;flex-shrink:0}.review-result{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px 0}summary{cursor:pointer}#feedback-status{font-weight:600}#feedback-identifiers{overflow-wrap:anywhere}
#review-feedback{min-width:0;overflow-wrap:anywhere}
'''.encode()


def document(title, body, build_id, *, current_profile=False):
    feedback = (Path(__file__).parent / 'feedback_template.html').read_text(encoding='utf-8')
    notice = ('现行本地 mock 工作台 · 只读审核选定文章与草稿状态；未连接真实公众号。'
              if current_profile else '合成演练实例 · 只读审核。以下文章、排期和草稿均为公开构造数据，未连接公众号。')
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<link rel="icon" href="data:,"><link rel="stylesheet" href="' + CSS_PATH + '">'
            '<meta name="rr-build" content="' + build_id + '"><script defer src="' + JS_PATH + '"></script>'
            '<title>' + escape(title) + ' · 微信公众号草稿工作台</title></head><body>'
            '<header><nav aria-label="主导航"><a href="' + INDEX + '">草稿工作台</a>'
            '<a href="' + INDEX + '#queue">排期队列</a><a href="#review-feedback">审核反馈</a></nav></header><main>'
            '<p class="notice">' + notice + '</p>'
            + body + feedback + '</main><footer>导入去重 → 本地排期 → 创建或更新草稿 → 导出 Agent 任务包 → 人工发布并回填真实证明。'
            '<p>此审核页仅展示选定内容与演练状态；不提供导入、调度、草稿写入或发布操作。</p></footer></body></html>').encode()


def source_inputs(root):
    root = Path(root)
    need(root.is_absolute(), 503, 'source_changed')
    for item in (root, *root.parents):
        need(not item.is_symlink(), 503, 'source_changed')
    for directory in ('src', 'migrations'):
        need((root / directory).is_dir() and not (root / directory).is_symlink(), 503, 'source_changed')
        for item in (root / directory).rglob('*'):
            need(not item.is_symlink(), 503, 'source_changed')
    # Explicit code directories; never walk data, .env, storage, articles or the Git index.
    names = sorted([p.relative_to(root).as_posix() for directory in ('src', 'migrations')
                    for p in (root / directory).rglob('*') if p.suffix in ('.py', '.html', '.sql', '.js', '.css')])
    names.append('pyproject.toml')
    result = {}
    for name in names:
        path = root / name
        need(path.is_file() and not path.is_symlink() and path.stat().st_nlink == 1, 503, 'source_changed')
        result[name] = sha(path.read_bytes())
    return result


class Snapshot:
    def __init__(self, config, connection, *, source_root, commit, selected_article_ids,
                 synthetic_instance, current_profile=False):
        need(config.wechat_mode == 'mock', 503, 'mock_profile_required')
        if current_profile:
            need(synthetic_instance is None and config.database_path == Path(
                '/home/alalapi/ProjectData/wechat-article-scheduler/linux-local-profile/mock/data/app.sqlite3'),
                503, 'current_profile_binding')
            need(type(selected_article_ids) is tuple and 0 <= len(selected_article_ids) <= 20 and
                 all(type(i) is int and i > 0 for i in selected_article_ids) and
                 len(set(selected_article_ids)) == len(selected_article_ids), 503, 'explicit_article_selection_required')
        else:
            need(synthetic_instance == 'rr-public-fixture-v1' and selected_article_ids == (1, 2),
                 503, 'explicit_synthetic_selection_required')
        self.root = Path(source_root)
        info = self.root.stat()
        need(info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o022,
             503, 'source_root_invalid')
        need(type(commit) is str and re.fullmatch('[a-f0-9]{40}|[a-f0-9]{64}', commit))
        self.root_identity = (info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode)
        self.inputs = source_inputs(self.root)
        self.config, self.conn = config, connection
        records, hints = [], {}
        for aid in selected_article_ids:
            detail = build_article_detail(config, connection, aid)
            need(bool(detail), 503, 'projection_not_ready')
            hints[str(aid)] = {'workflow': detail['workflow_hint'], 'draft': detail['wechat_draft']['label']}
            # Only these selected article columns may leave the project; never paths/configs/proofs.
            row = connection.execute('SELECT id,title,summary,body,status FROM articles WHERE id=?', (aid,)).fetchone()
            records.append(dict(row))
        if not current_profile:
            need(records == PUBLIC_ARTICLES, 503, 'public_fixture_mismatch')
        queue = [{k: row[k] for k in ('article_id', 'title', 'status_label', 'scheduled_at_label', 'adapter_mode')}
                 for row in list_queue_jobs(connection, config) if row['article_id'] in selected_article_ids] if selected_article_ids else []
        self.selection = {'instance': 'linux_mock_no_legacy_state_load' if current_profile else synthetic_instance,
                          'articles': records, 'queue': queue, 'hints': hints}
        build_id = sha(canonical({'inputs': self.inputs, 'selection': self.selection}))
        self.source = {'commit': commit, 'build_id': build_id, 'dirty': True}
        cards = ''.join('<article><h2><a href="' + INDEX + 'articles/' + str(r['id']) + '">'
                        + escape(r['title']) + '</a></h2><p>' + escape(r['summary'] or '') + '</p><p class="meta">'
                        + escape(hints[str(r['id'])]['workflow']) + '</p></article>' for r in records) or '<p class="meta">当前明确选择为空，没有审核文章；未导出其他内容。</p>'
        jobs = ''.join('<li>' + escape(r['title']) + ' · ' + escape(r['scheduled_at_label']) + ' · '
                       + escape(r['status_label']) + '（演练）</li>' for r in queue) or '<li>没有选定文章的排期任务。</li>'
        self.output = {INDEX: ('workbench', 'text/html; charset=utf-8', document('作品与草稿',
                       '<h1>作品与草稿</h1><p>核对选定文章、排期和草稿状态。</p><div class="grid">' + cards
                       + '</div><section id="queue"><h2>草稿排期队列</h2><ul>' + jobs + '</ul></section>', build_id, current_profile=current_profile)),
                       CSS_PATH: ('workbench-css', 'text/css; charset=utf-8', CSS),
                       JS_PATH: ('feedback-js', 'text/javascript; charset=utf-8', (Path(__file__).parent / 'feedback.js').read_bytes())}
        for row in records:
            path = INDEX + 'articles/' + str(row['id'])
            self.output[path] = ('article-' + str(row['id']), 'text/html; charset=utf-8',
                                 document(row['title'], '<h1>' + escape(row['title']) + '</h1><article><p>'
                                          + escape(row['summary'] or '') + '</p><pre>' + escape(row['body'])
                                          + '</pre><p>状态：' + escape(hints[str(row['id'])]['workflow']) + '</p><p>'
                                          + escape(hints[str(row['id'])]['draft']) + '</p>'
                                          '<p>实际发布仍须用户在公众号后台完成，并回填真实证明。</p></article>', build_id, current_profile=current_profile))
        pages = [path for path, (_, mime, _) in self.output.items() if mime.startswith('text/html')]
        self.manifest = {'schema': 1, 'project_id': PROJECT, 'source': self.source, 'page_paths': pages,
                         'resources': [{'id': rid, 'sha256': sha(data), 'size': len(data), 'mode': 'readonly',
                                        'preview_version': 'ssr-current-profile-v1' if current_profile else 'ssr-public-fixture-v1', 'content_type': mime}
                                       for rid, mime, data in self.output.values()],
                         'transport': {'websocket': False, 'sse': False},
                         'purpose': ('微信公众号草稿工作台：现行mock实例明确选定文章、排期及草稿状态的只读审核'
                                     if current_profile else '微信公众号草稿工作台：明确选定合成文章、排期及演练草稿的只读审核'),
                         'routes': {'pages': [{'method': 'GET', 'path': p, 'resource_id': self.output[p][0]} for p in pages],
                                    'resources': [{'method': 'GET', 'path': CSS_PATH, 'resource_id': 'workbench-css'},
                                                  {'method': 'GET', 'path': JS_PATH, 'resource_id': 'feedback-js'}],
                                    'data': [{'method': 'GET', 'path': '/__rr/v1/data/workbench'}],
                                    'feedback': [{'method': 'POST', 'path': '/__rr/v1/feedback'},
                                                 {'method': 'GET', 'path': '/__rr/v1/feedback/by-request/{client_request_id}'},
                                                 {'method': 'GET', 'path': '/__rr/v1/feedback/{feedback_id}'},
                                                 {'method': 'GET', 'path': '/__rr/v1/feedback/{feedback_id}/attachments/{attachment_id}'}]}}

    def current(self):
        info = self.root.stat()
        need((info.st_dev, info.st_ino, info.st_uid, info.st_gid, info.st_mode) == self.root_identity,
             503, 'source_root_changed')
        need(source_inputs(self.root) == self.inputs, 503, 'source_changed')

    def data(self):
        return {'schema': 1, 'project_id': PROJECT, 'source': self.source, **self.selection}
