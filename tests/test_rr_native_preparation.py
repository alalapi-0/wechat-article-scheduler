"""Metadata/guard checks only: no business rows, migrations, listeners or keys."""
import pytest
from wechat_article_scheduler.rr_review.native_runtime import DATABASE, current_config
from wechat_article_scheduler.rr_review.projection import Snapshot, document
from wechat_article_scheduler.rr_review.protocol import Refused


def test_current_profile_requires_explicit_selection_before_any_query():
    class NoDatabaseReads:
        def execute(self, *_):
            raise AssertionError('must reject before querying data')
    config = current_config()
    assert config.database_path == DATABASE and config.wechat_mode == 'mock'
    assert config.dry_run and not config.web_auto_run_due
    for ids in ((True,), (1, 1), tuple(range(1, 22))):
        with pytest.raises(Refused):
            Snapshot(config, NoDatabaseReads(), source_root='/unused', commit='a'*40,
                     selected_article_ids=ids, synthetic_instance=None, current_profile=True)
    with pytest.raises(Refused):
        Snapshot(config, NoDatabaseReads(), source_root='/unused', commit='a'*40,
                 selected_article_ids=(1,), synthetic_instance='rr-public-fixture-v1', current_profile=True)
    assert '现行本地 mock 工作台'.encode() in document('标题', '', 'a'*64, current_profile=True)
    assert '合成演练实例'.encode() in document('标题', '', 'a'*64)
    from wechat_article_scheduler.rr_review.native_runtime import ROOT, source_identity
    empty = Snapshot(config, NoDatabaseReads(), source_root=ROOT, commit=source_identity()['commit'],
                     selected_article_ids=(), synthetic_instance=None, current_profile=True)
    assert empty.selection['articles'] == [] and empty.selection['instance'] == 'linux_mock_no_legacy_state_load'
    assert '当前明确选择为空'.encode() in empty.output['/__rr/wechat/'][2]
