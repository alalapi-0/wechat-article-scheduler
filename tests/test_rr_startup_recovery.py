"""Stdlib public-fault tests: no DB, native credentials or service startup."""
import asyncio
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import subprocess

from wechat_article_scheduler.rr_review import native_runtime as runtime

from wechat_article_scheduler.rr_review.identity import SupplyNotReady, receive_key
from wechat_article_scheduler.rr_review.native_runtime import acquire_startup, guard_running, ClockGuard, STARTUP_DELAYS
from wechat_article_scheduler.rr_review.protocol import Refused


class PublicKey:
    def __init__(self): self.closed = False
    def close(self): self.closed = True


def report(*, missing=False, invalid=False, permanent=None):
    remaining = [permanent] if permanent else ['native_batch_not_ready'] if missing or invalid else []
    return {'ready': not remaining, 'remaining': remaining,
            'native': {'project': {'ready': not (missing or invalid), 'transient': missing}}}


class RecoveryTests(unittest.TestCase):
    def test_git_timeouts_are_permanent_before_key_request(self):
        for index in (0, 1):
            with self.subTest(git_call=index + 1):
                async def check():
                    outcomes = [subprocess.TimeoutExpired('git', 3)] if index == 0 else ['a'*40, subprocess.TimeoutExpired('git', 3)]
                    sleeps = []
                    async def sleep(delay): sleeps.append(delay)
                    with patch.object(runtime, 'physical'), patch.object(runtime, 'ROOT') as root, patch.object(runtime.subprocess, 'check_output', side_effect=outcomes) as git:
                        root.stat.return_value = SimpleNamespace(st_uid=1000, st_mode=0o40755)
                        with self.assertRaises(Refused) as error:
                            await acquire_startup(inspect_fn=runtime.source_identity, key_factory=lambda: self.fail('must not request key'), sleep=sleep)
                        self.assertEqual(error.exception.code, 'source_git_timeout')
                        self.assertEqual(sleeps, [])
                        self.assertEqual(git.call_count, index + 1)
                        self.assertTrue(all(call.kwargs['timeout'] == 3 for call in git.call_args_list))
                asyncio.run(check())

    def test_live_git_timeout_closes_guard(self):
        async def check():
            class Server: should_exit = False
            class Snapshot:
                def current(self): pass
            class Key:
                def value(self): pass
            sleeps = []
            async def sleep(delay): sleeps.append(delay)
            server = Server()
            with patch.object(runtime, 'physical'), patch.object(runtime, 'ROOT') as root, patch.object(runtime.subprocess, 'check_output', side_effect=subprocess.TimeoutExpired('git', 3)) as git:
                root.stat.return_value = SimpleNamespace(st_uid=1000, st_mode=0o40755)
                await guard_running(Snapshot(), Key(), {}, server, ClockGuard(), sleep=sleep, source_fn=runtime.source_identity)
                self.assertTrue(server.should_exit)
                self.assertEqual((git.call_count, sleeps), (1, [1]))
        asyncio.run(check())

    @unittest.skipUnless(sys.platform.startswith('linux'), 'requires Linux Unix metadata/connect semantics')
    def test_preconnection_classification(self):
        with tempfile.TemporaryDirectory(prefix='rr-rec-') as temporary:
            directory = Path(temporary) / 'public'; directory.mkdir(mode=0o750); directory.chmod(0o750)
            path = directory / 'key.sock'
            with self.assertRaises(SupplyNotReady):
                receive_key(str(path), provider_uid=os.getuid(), provider_gid=os.getgid())
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET)
            try:
                sock.bind(str(path)); path.chmod(0o660)
                with self.assertRaises(SupplyNotReady):
                    receive_key(str(path), provider_uid=os.getuid(), provider_gid=os.getgid())
                path.chmod(0o600)
                with self.assertRaises(Refused) as error:
                    receive_key(str(path), provider_uid=os.getuid(), provider_gid=os.getgid())
                self.assertNotIsInstance(error.exception, SupplyNotReady)
            finally:
                sock.close(); path.unlink()

    def test_transient_then_success(self):
        async def check():
            calls, factories, sleeps = [], [], []
            key = PublicKey()
            def inspect(): calls.append(1); return report(missing=len(calls) == 1)
            def factory():
                factories.append(1)
                if len(factories) == 1: raise SupplyNotReady()
                return key
            async def sleep(delay): sleeps.append(delay)
            value, actual = await acquire_startup(inspect_fn=inspect, key_factory=factory, sleep=sleep)
            self.assertTrue(value['ready']); self.assertIs(actual, key)
            self.assertEqual((len(calls), len(factories), sleeps), (3, 2, [1, 2]))
            key.close()
        asyncio.run(check())

    def test_attempt_limit(self):
        async def check():
            calls, sleeps = [], []
            def inspect(): calls.append(1); return report(missing=True)
            async def sleep(delay): sleeps.append(delay)
            with self.assertRaises(Refused) as error:
                await acquire_startup(inspect_fn=inspect, key_factory=lambda: self.fail('no key request'), sleep=sleep)
            self.assertEqual(error.exception.code, 'startup_supply_attempts_exhausted')
            self.assertEqual((len(calls), sleeps, sum(sleeps)), (5, list(STARTUP_DELAYS), 15))
        asyncio.run(check())

    def test_permanent_failures(self):
        failures = [Refused(503, c) for c in ('key_peer_invalid', 'key_fd_invalid', 'key_packet_invalid',
                    'key_supply_changed', 'lease_expired', 'revoked')]
        for failure in failures + [TimeoutError(), ConnectionResetError(), PermissionError()]:
            with self.subTest(failure=type(failure).__name__, code=getattr(failure, 'code', '')):
                async def check():
                    calls, sleeps = [], []
                    def factory(): calls.append(1); raise failure
                    async def sleep(delay): sleeps.append(delay)
                    with self.assertRaises(type(failure)):
                        await acquire_startup(inspect_fn=report, key_factory=factory, sleep=sleep)
                    self.assertEqual((calls, sleeps), ([1], []))
                asyncio.run(check())

    def test_permanent_preflight(self):
        for value in (report(permanent='schema_invalid'), report(invalid=True)):
            with self.subTest(value=value):
                async def check():
                    async def sleep(_): self.fail('no retry')
                    with self.assertRaises(Refused):
                        await acquire_startup(inspect_fn=lambda: value, key_factory=lambda: self.fail('no key request'), sleep=sleep)
                asyncio.run(check())

    def test_clock_rollback(self):
        async def check():
            wall, mono, calls = [100.0], [20.0], []
            clock = ClockGuard(wall=lambda: wall[0], monotonic=lambda: mono[0])
            def inspect(): calls.append(1); return report(missing=True)
            async def sleep(delay): wall[0] -= 1; mono[0] += delay
            with self.assertRaises(Refused) as error:
                await acquire_startup(inspect_fn=inspect, sleep=sleep, clock=clock)
            self.assertEqual((error.exception.code, calls), ('clock_rollback', [1]))
        asyncio.run(check())

    def test_clock_failure_after_acquisition_closes_key(self):
        async def check():
            wall, mono, calls = [100.0], [20.0], []
            clock = ClockGuard(wall=lambda: wall[0], monotonic=lambda: mono[0]); key = PublicKey()
            def factory(): calls.append(1); wall[0] -= 1; return key
            with self.assertRaises(Refused):
                await acquire_startup(inspect_fn=report, key_factory=factory, clock=clock)
            self.assertTrue(key.closed); self.assertEqual(calls, [1])
        asyncio.run(check())

    def test_live_failure_closes_without_recovery(self):
        for failure in (SupplyNotReady(), Refused(503, 'key_supply_changed'), Refused(503, 'lease_expired')):
            with self.subTest(failure=failure.code):
                async def check():
                    class Server: should_exit = False
                    class Snapshot:
                        def current(self): pass
                    calls, sleeps = [], []
                    class Key:
                        def value(self): calls.append(1); raise failure
                    async def sleep(delay): sleeps.append(delay)
                    server = Server()
                    await guard_running(Snapshot(), Key(), {}, server, ClockGuard(), sleep=sleep, source_fn=lambda: {})
                    self.assertTrue(server.should_exit); self.assertEqual((calls, sleeps), ([1], [1]))
                asyncio.run(check())


if __name__ == '__main__':
    unittest.main()
