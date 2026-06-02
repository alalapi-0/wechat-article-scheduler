# Local Blog

`eval_workflow.py` / `plans.py` 提供 Round 28 评估干跑（static_site、wordpress、local_files）。默认 dry-run，不写入、不调用 REST。

```bash
python -m wechat_article_scheduler.cli local-blog-plan --destination static_site
```

详见 `docs/local_blog_adapter_assessment.md`。
