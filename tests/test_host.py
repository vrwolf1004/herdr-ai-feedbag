import os
import tempfile
import unittest
from unittest import mock

import support  # noqa: F401  (src 경로 준비)
import feedbag
import providers


class AtomicWriteTest(unittest.TestCase):
    def test_write_replaces_value_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as directory:
            state = feedbag.State(directory)
            state.write("heartbeat", "1")
            state.write("heartbeat", "2")
            self.assertEqual(state.read("heartbeat"), "2")
            self.assertFalse(os.path.exists(state.path("heartbeat") + ".tmp"))

    def test_failed_write_keeps_previous_value(self):
        with tempfile.TemporaryDirectory() as directory:
            state = feedbag.State(directory)
            state.write("pane.id", "old")
            with mock.patch.object(feedbag.os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    state.write("pane.id", "new")
            self.assertEqual(state.read("pane.id"), "old")


class FetchIsolationTest(unittest.TestCase):
    def make_host(self, usages, next_fetch):
        host = feedbag.Host.__new__(feedbag.Host)
        host.state = mock.Mock(read=mock.Mock(return_value=None), remove=mock.Mock())
        host.config_dir = None
        host.usages = usages
        host.next_fetch = next_fetch
        host.updated_at = None
        host.config_changed = mock.Mock(return_value=False)
        return host

    def test_provider_exception_becomes_error_and_keeps_last_numbers(self):
        window = providers.Window("5h", 34.0, None)
        previous = providers.Usage("claude", windows=[window])
        host = self.make_host({"claude": previous}, {"claude": 0.0})
        with mock.patch.object(feedbag.providers, "fetch", side_effect=ValueError("bad shape")):
            host.fetch_due(now=100.0)
        usage = host.usages["claude"]
        self.assertEqual(usage.error, "ValueError")
        self.assertEqual(usage.windows, [window])

    def test_other_providers_still_fetch_after_one_fails(self):
        host = self.make_host(
            {"claude": providers.Usage("claude"), "codex": providers.Usage("codex")},
            {"claude": 0.0, "codex": 0.0},
        )
        ok = providers.Usage("codex", windows=[providers.Window("wk", 10.0, None)])

        def fake_fetch(name, config_dir=None):
            if name == "claude":
                raise RuntimeError("boom")
            return ok

        with mock.patch.object(feedbag.providers, "fetch", side_effect=fake_fetch):
            host.fetch_due(now=100.0)
        self.assertEqual(host.usages["codex"], ok)
        self.assertEqual(host.usages["claude"].error, "RuntimeError")


class PaneAliveTest(unittest.TestCase):
    def test_missing_pane_is_not_alive(self):
        from unittest import mock
        with mock.patch.object(feedbag.herdr_api, "cli", return_value=None):
            self.assertFalse(feedbag.pane_alive("wN:p1"))

    def test_existing_pane_is_alive(self):
        from unittest import mock
        with mock.patch.object(feedbag.herdr_api, "cli", return_value={"pane": {"pane_id": "wN:p1"}}):
            self.assertTrue(feedbag.pane_alive("wN:p1"))

    def test_no_pane_id_is_not_alive(self):
        self.assertFalse(feedbag.pane_alive(None))


class RetryIntervalTest(unittest.TestCase):
    def fetch_once(self, fetched):
        host = FetchIsolationTest().make_host({"claude": providers.Usage("claude")}, {"claude": 0.0})
        with mock.patch.object(feedbag.providers, "fetch", return_value=fetched):
            host.fetch_due(now=100.0)
        return host.next_fetch["claude"] - 100.0

    def test_success_uses_normal_interval(self):
        self.assertEqual(self.fetch_once(providers.Usage("claude")), feedbag.FETCH_SECONDS["claude"])

    def test_error_without_numbers_retries_soon(self):
        self.assertEqual(self.fetch_once(providers.Usage("claude", error="network")), feedbag.RETRY_SECONDS)

    def test_rate_limit_backs_off(self):
        interval = self.fetch_once(providers.Usage("claude", error="rate_limited", rate_limited=True))
        self.assertEqual(interval, feedbag.FETCH_SECONDS["claude"] * feedbag.RATE_LIMIT_BACKOFF)


class ClearRemovedTokenTest(unittest.TestCase):
    def test_disabled_provider_token_is_cleared_at_once(self):
        host = FetchIsolationTest().make_host({"claude": providers.Usage("claude")}, {"claude": 0.0})
        host.pane_id = "p1"
        with mock.patch.object(feedbag.providers, "enabled_providers", return_value=[]), \
                mock.patch.object(feedbag.herdr_api, "cli") as cli:
            host.sync_providers()
        cli.assert_called_once_with(
            "pane", "report-metadata", "p1", "--source", feedbag.SOURCE, "--clear-token", "fb_claude", check=False,
        )
        self.assertEqual(host.usages, {})


