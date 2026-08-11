# External Agent Task Packages

This package exports auditable, read-only inspection bundles for external browser Agents.

It does not:

- run browser automation
- call an LLM
- store WeChat backend cookies or passwords
- bypass QR login, captcha, or platform risk controls
- change fields or save a draft
- click the final publish button

The exported files live under `outbox/wechat_agent_tasks/job-xxxxxx/` and are
intended for a user-approved external browser tool or a human operator. Agents may locate
and compare an existing draft, take screenshots, and report differences; all backend
changes remain a human operation.
