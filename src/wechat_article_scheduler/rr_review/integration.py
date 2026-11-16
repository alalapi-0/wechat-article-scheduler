"""Explicit same-process lifespan hook; no default runtime/management route changes."""
from contextlib import asynccontextmanager
from wechat_article_scheduler import db
from .server import ReviewService


def attach_review(app, snapshot, key, *, fixture_paths=None):
    """Caller must serialize native adoption; never invoke on the existing live DB in this phase.

    Existing project lifespan owns the process. Only it starts the two RR sockets;
    Agent CLI/B never opens SQLite. Migration belongs to the project's normal DB
    initialization, not the platform or a second writer. This hook does not migrate.
    """
    original = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        async with original(app):
            connection = db.connect(snapshot.config.database_path)
            service = ReviewService(snapshot, connection, key, _fixture_paths=fixture_paths)
            try:
                await service.start()
                app.state.rr_review = service
                yield
            finally:
                await service.close()
                connection.close()

    app.router.lifespan_context = lifespan
