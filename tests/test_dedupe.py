from wechat_article_scheduler import db
from wechat_article_scheduler.dedupe import is_duplicate
from wechat_article_scheduler.parser import ParsedArticle


def test_duplicate_by_content_hash(tmp_path) -> None:
    db_path = tmp_path / "test.sqlite3"
    db.init_db(db_path)
    article = ParsedArticle(
        source_path="/tmp/a.md",
        title="标题A",
        summary="摘要",
        body="相同正文",
        content_hash="abc123hash",
    )
    rules = {"dedupe": {"by_content_hash": True, "by_normalized_title": False}}

    with db.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO articles (source_path, title, summary, body, content_hash, status) "
            "VALUES (?, ?, ?, ?, ?, 'imported')",
            (article.source_path, article.title, article.summary, article.body, article.content_hash),
        )
        conn.commit()
        dup, reason = is_duplicate(conn, article, rules)
        assert dup is True
        assert "content_hash" in reason
