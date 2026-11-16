"""Phase 2: actual browser feedback -> project transaction -> separate CLI -> browser.

Only public synthetic data and UID1000 Unix/route bridge fixtures. The native
UID996/mTLS/Owner browser/maintenance-chat Agent are explicitly not exercised.
"""
import asyncio
import base64
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import time
import uuid

from wechat_article_scheduler import db
from wechat_article_scheduler.rr_review.fixture import PUBLIC_KEY, PublicFixtureKey, create_fixture
from wechat_article_scheduler.rr_review.integration import attach_review
from wechat_article_scheduler.rr_review.projection import INDEX, JS_PATH
from wechat_article_scheduler.rr_review.protocol import ORIGIN, PROJECT, canonical, sha
from wechat_article_scheduler.rr_review.store import FeedbackStore
from wechat_article_scheduler.web.app import create_app

SOURCE = Path(__file__).resolve().parents[1]


def test_browser_feedback_recovery_and_version(tmp_path, rr_socket_dir):
    asyncio.run(scenario(tmp_path, rr_socket_dir))


async def scenario(tmp_path, rr_socket_dir):
    from playwright.async_api import async_playwright, expect
    sys.path.insert(0, '/home/alalapi/Projects/desktop-tool/remote-project-review')
    from rr_review.pch_client import PchClient
    from rr_review.http_core import Peer
    from rr_review.registry import Registry
    cfg, snapshot = create_fixture(tmp_path / 'public', SOURCE)
    Registry._api_manifest(None, PROJECT, snapshot.manifest)
    assert 'src/wechat_article_scheduler/rr_review/feedback.js' in snapshot.inputs
    assert any(r['path'] == JS_PATH for r in snapshot.manifest['routes']['resources'])
    directory = rr_socket_dir
    browser_path, agent_path = str(directory / 'b.sock'), str(directory / 'a.sock')
    peer = Peer(PROJECT, 'rr-' + PROJECT + '.invalid', 'a'*64, 'public-fixture', time.time() + 300, snapshot.current)
    class Client(PchClient):
        async def _connect(self):
            return await asyncio.open_unix_connection(browser_path, limit=16384)
    client = Client(lambda: PUBLIC_KEY, os.getgid(), asyncio.Semaphore(1),
                    manifest_source=lambda: snapshot.manifest, project_id=PROJECT)
    app = create_app(cfg)
    attach_review(app, snapshot, PublicFixtureKey(), fixture_paths=(browser_path, agent_path))
    network, console, failure_log, accepted = [], [], [], []
    fault = {'next_post': None}
    tracked = {}
    def remember(pid):
        try:
            fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
            tracked[int(pid)] = fields[19]
        except FileNotFoundError:
            pass
    child_path = Path('/proc/self/task/' + str(os.getpid()) + '/children')
    initial_children = set(child_path.read_text().split())
    evidence = SOURCE / 'evidence'
    blob = '明确选择的公开合成附件，不含用户文章或会话。'.encode()
    file = {'name': 'public-note.txt', 'mimeType': 'text/plain', 'buffer': blob}
    async def cli(*args):
        boot = 'import sys,runpy;sys.path.insert(0,' + repr(str(SOURCE / 'src')) + ');runpy.run_module("wechat_article_scheduler.rr_review.agent_cli",run_name="__main__")'
        process = await asyncio.create_subprocess_exec(sys.executable, '-I', '-B', '-c', boot, '--socket', agent_path,
                                                      *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            out, err = await asyncio.wait_for(process.communicate(), 15)
            assert process.returncode == 0, err.decode()
            return json.loads(out)
        finally:
            if process.returncode is None:
                try:
                    process.terminate()
                except ProcessLookupError:
                    pass
                try:
                    await asyncio.wait_for(process.wait(), 3)
                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    await process.wait()
            else:
                await process.wait()
    async with app.router.lifespan_context(app), async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path='/usr/bin/google-chrome', chromium_sandbox=True)
        try:
            for child in set(child_path.read_text().split()) - initial_children: remember(child)
            context = await browser.new_context(service_workers='block', reduced_motion='reduce')
            async def bridge(route):
                request = route.request
                if not request.url.startswith(ORIGIN + '/') or request.method not in ('GET', 'POST'):
                    failure_log.append({'unexpected_request': request.method}); await route.abort(); return
                path = request.url[len(ORIGIN):]
                mode = fault['next_post'] if request.method == 'POST' else None
                if mode: fault['next_post'] = None
                if mode == 'before_delivery':
                    failure_log.append({'fault': mode, 'path': path}); await route.abort('failed'); return
                reply = await client.request(peer, request.method, path, request.post_data_buffer or b'',
                                             request.headers.get('content-type') if request.method == 'POST' else None)
                try:
                    network.append({'method': request.method, 'path': path, 'status': reply.status,
                                    'size': len(reply.body), 'sha256': sha(reply.body)})
                    if request.method == 'POST' and reply.status in (200, 201): accepted.append(json.loads(reply.body))
                    if mode == 'after_commit':
                        failure_log.append({'fault': mode, 'feedback_id': accepted[-1]['feedback_id'], 'server_status': reply.status})
                        await route.abort('failed')
                    else:
                        body = reply.body
                        if fault.get('wrong_lookup_id') and path == fault['wrong_lookup_id']:
                            value = json.loads(body); value['feedback_id'] = str(uuid.uuid4())
                            body = canonical(value)
                            fault['wrong_lookup_id'] = None
                            failure_log.append({'fault': 'wrong_feedback_id_response', 'path': path})
                        await route.fulfill(status=reply.status, headers={'Content-Type': reply.headers['content-type']}, body=body)
                finally:
                    reply.close()
            await context.route('**/*', bridge)
            page = await context.new_page()
            page.set_default_timeout(7000)
            page.on('pageerror', lambda error: console.append({'kind': 'pageerror', 'text': str(error)}))
            page.on('console', lambda message: console.append({'kind': message.type, 'text': message.text})
                    if message.type in ('error', 'warning') else None)
            status = page.locator('#feedback-status')
            async def prepare(description, *, attachment=True):
                await expect(page.locator('#feedback-prepare')).to_be_enabled()
                for label, value in [('问题（必填）', description), ('预期表现', '显示演练状态'), ('实际表现', '公开合成检查'), ('复现步骤', '进入当前页面并查看排期')]:
                    await page.get_by_label(label, exact=True).fill(value)
                if attachment: await page.locator('#feedback-files').set_input_files(file)
                await page.locator('#feedback-prepare').click()
                await expect(status).to_contain_text('已固定本次反馈')
                await page.get_by_label('我已检查正文、附件和来源，确认保存到项目。', exact=True).check()
                await expect(page.locator('#feedback-save')).to_be_enabled()
                return await page.evaluate('JSON.parse(localStorage.getItem("rr-feedback:wechat-article-scheduler:"+location.pathname))')
            async def reset():
                page.once('dialog', lambda dialog: dialog.accept())
                await page.locator('#feedback-new').click()
                await expect(status).to_contain_text('尚未固定反馈')
            async def process_and_refresh(fid):
                read = await cli('read', fid)
                assert read['source'] == snapshot.source and base64.b64decode(read['attachment_bytes'][0]['base64']) == blob
                assert (await cli('ack', fid))['status'] == 'agent_read'
                await page.locator('#feedback-refresh').click()
                await expect(page.locator('#feedback-lookup-status')).to_have_text('Agent已读')
                result = '<img src=x onerror="window.badResult=true"> 合成处理完成'
                assert (await cli('result', fid, '--revision', '1', '--description', result, '--reference', 'public-fixture-only'))['status'] == 'processed'
                await page.locator('#feedback-refresh').click()
                await expect(page.locator('#feedback-lookup-status')).to_have_text('Agent已处理')
                await expect(page.locator('#feedback-lookup-result')).to_contain_text(result)
                assert await page.locator('#feedback-result img, #feedback-lookup-result img').count() == 0
                assert not await page.evaluate('window.badResult === true')
                return read

            # Desktop: actual article page/resource, explicit attachment, committed feedback and CLI round trip.
            await page.set_viewport_size({'width': 1280, 'height': 900})
            await page.goto(ORIGIN + INDEX + 'articles/1')
            pinned = await prepare('浏览器提交：核对合成排期提示')
            assert pinned['payload']['page_path'] == INDEX + 'articles/1'
            assert pinned['payload']['resource']['id'] == 'article-1'
            assert pinned['payload']['source'] == snapshot.source
            assert await status.get_attribute('aria-live') == 'polite'
            await page.locator('#feedback-save').click()
            await expect(status).to_have_text('已同步待Agent读取')
            await expect(page.locator('#feedback-save')).to_have_text('已保存到项目')
            await expect(page.locator('#feedback-files')).to_be_disabled()
            first = accepted[-1]
            assert first['client_request_id'] == pinned['payload']['client_request_id']
            assert first['payload_sha256'] == pinned['payload_sha256']
            read = await process_and_refresh(first['feedback_id'])
            assert read['description'] == pinned['payload']['description']
            fault['wrong_lookup_id'] = '/__rr/v1/feedback/' + first['feedback_id']
            await page.locator('#feedback-refresh').click()
            await expect(page.locator('#feedback-lookup-status')).to_contain_text('回执反馈编号与查询编号不同')
            await expect(page.locator('#feedback-lookup-result')).to_have_text('')
            await page.locator('#feedback-refresh').click()
            await expect(page.locator('#feedback-lookup-status')).to_have_text('Agent已处理')
            await page.locator('#feedback-preview').evaluate('(element) => element.open = false')
            await page.locator('#review-feedback').screenshot(path=str(evidence / 'feedback-desktop.png'))

            # Lost response after actual atomic commit: reload keeps request+source; GET recovers without POST.
            await reset()
            pinned2 = await prepare('已持久化但响应丢失的合成反馈')
            fault['next_post'] = 'after_commit'
            before = len(accepted)
            await page.locator('#feedback-save').click()
            await expect(status).to_contain_text('失败待核对')
            assert len(accepted) == before + 1
            second = accepted[-1]
            await page.reload()
            await expect(status).to_contain_text('已恢复原请求')
            restored = await page.evaluate('JSON.parse(localStorage.getItem("rr-feedback:wechat-article-scheduler:"+location.pathname))')
            assert restored['payload'] == pinned2['payload'] and restored['payload_sha256'] == pinned2['payload_sha256']
            await expect(page.locator('#feedback-save')).to_be_disabled()
            await expect(page.locator('#feedback-files')).to_be_enabled()
            await page.locator('#feedback-files').set_input_files({'name': 'wrong.txt', 'mimeType': 'text/plain', 'buffer': b'different'})
            await expect(status).to_contain_text('与原摘要/类型不一致')
            await page.locator('#feedback-files').set_input_files(file)
            await expect(page.locator('#feedback-file-note')).to_contain_text('全部长度、SHA和类型匹配')
            await page.locator('#feedback-reconcile').click()
            await expect(status).to_have_text('已同步待Agent读取')
            assert len(accepted) == before + 1
            await process_and_refresh(second['feedback_id'])

            # Mobile: unknown result before delivery, 404 lookup then explicit retry of the very same request.
            await page.set_viewport_size({'width': 390, 'height': 900})
            await reset()
            pinned3 = await prepare('未到达项目的合成反馈')
            fault['next_post'] = 'before_delivery'
            count = len(accepted)
            await page.locator('#feedback-save').click()
            await expect(status).to_contain_text('失败待核对')
            await page.reload()
            await expect(status).to_contain_text('已恢复原请求')
            await expect(page.locator('#feedback-files')).to_be_enabled()
            await page.locator('#feedback-files').set_input_files(file)
            await expect(page.locator('#feedback-file-note')).to_contain_text('全部长度、SHA和类型匹配')
            await page.locator('#feedback-confirm').check()
            await expect(page.locator('#feedback-save')).to_be_disabled()
            await page.locator('#feedback-reconcile').click()
            await expect(status).to_contain_text('查询未找到记录')
            assert len(accepted) == count
            await expect(page.locator('#feedback-save')).to_be_enabled()
            await page.locator('#feedback-save').click()
            await expect(status).to_have_text('已同步待Agent读取')
            assert accepted[-1]['client_request_id'] == pinned3['payload']['client_request_id']
            assert accepted[-1]['payload_sha256'] == pinned3['payload_sha256'] and len(accepted) == count + 1
            await page.locator('#feedback-preview').evaluate('(element) => element.open = false')
            assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            await page.locator('#feedback-lookup').focus()
            await page.keyboard.press('Tab')
            assert await page.evaluate('document.activeElement.id') == 'feedback-refresh'
            await page.locator('#review-feedback').screenshot(path=str(evidence / 'feedback-mobile.png'))

            # A published-version transition is a synthetic fixture state change; no source file is edited.
            await reset()
            old = await prepare('版本变化后不得重新绑定', attachment=False)
            original_manifest = copy.deepcopy(snapshot.manifest)
            snapshot.manifest['source'] = dict(snapshot.source, build_id='f'*64)
            count = len(accepted)
            await page.locator('#feedback-save').click()
            await expect(status).to_contain_text('页面版本已变化')
            after = await page.evaluate('JSON.parse(localStorage.getItem("rr-feedback:wechat-article-scheduler:"+location.pathname))')
            assert after['payload'] == old['payload'] and len(accepted) == count
            snapshot.manifest = copy.deepcopy(original_manifest)
            # Same-build resource change is also refused, with the fixed resource retained.
            for asset in snapshot.manifest['resources']:
                if asset['id'] == old['payload']['resource']['id']: asset['sha256'] = 'e'*64
            await page.locator('#feedback-save').click()
            await expect(status).to_contain_text('不能重新绑定或提交')
            assert len(accepted) == count
            snapshot.manifest = copy.deepcopy(original_manifest)
            # Current source drift (including the new JS input) closes the project response.
            old_hash = snapshot.inputs['src/wechat_article_scheduler/rr_review/feedback.js']
            snapshot.inputs['src/wechat_article_scheduler/rr_review/feedback.js'] = '0'*64
            reply = await client._exchange('GET', JS_PATH, b'', {}, 4096,
                                           peer=replace(peer, current=lambda: None))
            assert reply.status == 503
            reply.close(); snapshot.inputs['src/wechat_article_scheduler/rr_review/feedback.js'] = old_hash
            missing = [row for row in network if row['status'] == 404]
            assert len(missing) == 1 and missing[0]['path'] == '/__rr/v1/feedback/by-request/' + pinned3['payload']['client_request_id']
            failure_log.append({'fault': 'manual_lookup_not_found', 'path': missing[0]['path'], 'status': 404})
            missing_console = 'Failed to load resource: the server responded with a status of 404 (Not Found)'
            errors = [item for item in console if item['kind'] == 'pageerror' or not (item['kind'] == 'error' and
                       ('net::ERR_FAILED' in item['text'] or item['text'] == missing_console))]
            assert not errors, errors
            assert len([item for item in console if 'net::ERR_FAILED' in item['text']]) == 2
            assert len([item for item in console if item['text'] == missing_console]) == 1
            session = await browser.new_browser_cdp_session()
            for process in (await session.send('SystemInfo.getProcessInfo'))['processInfo']: remember(process['id'])
            await session.detach()
            await context.close()
        finally:
            await browser.close()
    remaining = []
    for pid, start in tracked.items():
        try:
            fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
            if fields[19] == start and fields[0] != 'Z': remaining.append(pid)
        except FileNotFoundError:
            pass
    assert not remaining and not Path(browser_path).exists() and not Path(agent_path).exists()
    with db.connect(cfg.database_path) as connection:
        assert connection.execute('SELECT COUNT(*) FROM rr_feedback').fetchone()[0] == 3
        for value in accepted:
            record = FeedbackStore(connection).get(value['feedback_id'])
            assert record['client_request_id'] == value['client_request_id']
    (evidence / 'feedback-browser.json').write_text(json.dumps({
        'source': snapshot.source, 'flow': 'actual Chrome -> B client Unix HTTP parser -> owning project SQLite -> separate CLI -> Chrome manual GET',
        'accepted': [{k: r[k] for k in ('feedback_id', 'client_request_id', 'payload_sha256')} for r in accepted],
        'viewports': [1280, 390], 'keyboard_label_live_region_and_overflow': 'passed',
        'expected_faults': failure_log, 'console_including_expected_network_faults': console, 'unexpected_console': errors,
        'network': network, 'owned_processes_checked': len(tracked), 'remaining_owned_processes': remaining,
        'limitations': 'public fixture routes/UID1000 only; version transition is explicit synthetic manifest state; no production mTLS/real Agent claim'}, ensure_ascii=False, indent=2))
