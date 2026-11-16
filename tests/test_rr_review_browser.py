"""Real isolated Chrome renders of SSR bytes obtained via B's real Unix HTTP client.

The browser route bridge and UID1000 sockets are public fixture substitutes, not
native UID996/mTLS/production adoption. No management page or TCP port is exposed.
"""
import asyncio
import json
import os
from pathlib import Path
import sys
import time

from wechat_article_scheduler.rr_review.fixture import PUBLIC_KEY, PublicFixtureKey, create_fixture
from wechat_article_scheduler.rr_review.integration import attach_review
from wechat_article_scheduler.rr_review.projection import INDEX
from wechat_article_scheduler.rr_review.protocol import ORIGIN, PROJECT, sha
from wechat_article_scheduler.web.app import create_app

SOURCE = Path(__file__).resolve().parents[1]


def test_isolated_browser(tmp_path, rr_socket_dir):
    asyncio.run(check_browser(tmp_path, rr_socket_dir))


async def check_browser(tmp_path, rr_socket_dir):
    from playwright.async_api import async_playwright
    sys.path.insert(0, '/home/alalapi/Projects/desktop-tool/remote-project-review')
    from rr_review.pch_client import PchClient
    from rr_review.http_core import Peer
    cfg, snapshot = create_fixture(tmp_path / 'public', SOURCE)
    directory = rr_socket_dir
    browser_path, agent_path = str(directory / 'b.sock'), str(directory / 'a.sock')
    peer = Peer(PROJECT, 'rr-' + PROJECT + '.invalid', 'a'*64, 'public-fixture',
                time.time() + 300, snapshot.current)
    class Client(PchClient):
        async def _connect(self):
            return await asyncio.open_unix_connection(browser_path, limit=16384)
    client = Client(lambda: PUBLIC_KEY, os.getgid(), asyncio.Semaphore(1),
                    manifest_source=lambda: snapshot.manifest, project_id=PROJECT)
    app = create_app(cfg)
    attach_review(app, snapshot, PublicFixtureKey(), fixture_paths=(browser_path, agent_path))
    errors, network = [], []
    tracked = {}
    def remember(pid):
        try:
            fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
            tracked[int(pid)] = fields[19]
        except FileNotFoundError:
            pass
    initial_children = set(Path('/proc/self/task/' + str(os.getpid()) + '/children').read_text().split())
    evidence = SOURCE / 'evidence'; evidence.mkdir(exist_ok=True)
    async with app.router.lifespan_context(app), async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True, executable_path='/usr/bin/google-chrome',
                                                    chromium_sandbox=True)
        try:
            for child in set(Path('/proc/self/task/' + str(os.getpid()) + '/children').read_text().split()) - initial_children:
                remember(child)
            context = await browser.new_context(service_workers='block', reduced_motion='reduce')
            async def bridge(route):
                request = route.request
                if not request.url.startswith(ORIGIN + '/') or request.method != 'GET':
                    errors.append('unexpected_browser_request'); await route.abort(); return
                path = request.url[len(ORIGIN):]
                reply = await client.request(peer, 'GET', path, b'', None)
                try:
                    network.append({'path': path, 'status': reply.status, 'size': len(reply.body), 'sha256': sha(reply.body)})
                    await route.fulfill(status=reply.status, headers={'Content-Type': reply.headers['content-type']}, body=reply.body)
                finally:
                    reply.close()
            await context.route('**/*', bridge)
            page = await context.new_page()
            page.on('pageerror', lambda error: errors.append('pageerror:' + str(error)))
            page.on('console', lambda message: errors.append(message.type + ':' + message.text)
                    if message.type in ('error', 'warning') else None)
            checks = []
            for width, label in ((1280, 'desktop'), (390, 'mobile')):
                await page.set_viewport_size({'width': width, 'height': 900})
                await page.goto(ORIGIN + INDEX)
                assert await page.title() == '作品与草稿 · 微信公众号草稿工作台'
                assert await page.get_by_text('合成演练实例', exact=False).count() == 1
                assert await page.get_by_role('link', name='合成示例：把文章放进草稿工作台').count() == 1
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                await page.keyboard.press('Tab')
                assert await page.evaluate('document.activeElement.tagName') == 'A'
                await page.screenshot(path=str(evidence / ('workbench-' + label + '.png')), full_page=True)
                await page.get_by_role('link', name='合成示例：把文章放进草稿工作台').click()
                assert await page.get_by_role('heading', level=1).inner_text() == '合成示例：把文章放进草稿工作台'
                assert await page.get_by_text('未读取用户文章，未调用微信接口。', exact=False).count() == 1
                assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                await page.screenshot(path=str(evidence / ('article-' + label + '.png')), full_page=True)
                await page.get_by_role('link', name='草稿工作台', exact=True).click()
                await page.get_by_role('link', name='合成示例：草稿完成后的人工确认').click()
                assert await page.get_by_role('heading', level=1).inner_text() == '合成示例：草稿完成后的人工确认'
                checks.append({'viewport': label, 'width': width, 'navigation': 'passed', 'overflow': False, 'keyboard_link': 'passed'})
            assert not errors, errors
            assert network and all(row['status'] == 200 for row in network)
            session = await browser.new_browser_cdp_session()
            for process in (await session.send('SystemInfo.getProcessInfo'))['processInfo']:
                remember(process['id'])
            await session.detach()
            await context.close()
        finally:
            await browser.close()
    assert not Path(browser_path).exists() and not Path(agent_path).exists()
    remaining = []
    for pid, start in tracked.items():
        try:
            fields = Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()
            if fields[19] == start and fields[0] != 'Z': remaining.append(pid)
        except FileNotFoundError:
            pass
    assert not remaining, remaining
    (evidence / 'browser.json').write_text(json.dumps({'checks': checks, 'console_errors_warnings': errors,
                                                     'network': network, 'source': snapshot.source,
                                                     'owned_processes_checked': len(tracked), 'remaining_owned_processes': remaining,
                                                     'scope': 'isolated Chrome, public fixture route bridge, real B Unix client parser'},
                                                    ensure_ascii=False, indent=2))
