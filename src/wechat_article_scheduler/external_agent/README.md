# External Agent Task Packages

This package exports auditable task bundles for external browser Agents.

It does not:

- run browser automation
- call an LLM
- store WeChat backend cookies or passwords
- bypass QR login, captcha, or platform risk controls
- click the final publish button

The exported files live under `outbox/wechat_agent_tasks/job-xxxxxx/` and are
intended for Hermes, Cursor Agent, Playwright MCP, Browser Use, or a human
operator. Completion still requires proof supplied by the user.
