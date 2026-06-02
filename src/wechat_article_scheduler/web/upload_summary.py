"""上传结果摘要（与 scan / chain_summary 联动）。"""

from __future__ import annotations

from typing import Any

from wechat_article_scheduler.web.scan_summary import chain_hint_after_scan


def format_upload_summary(payload: dict[str, Any]) -> dict[str, Any]:
    scan = payload.get("scan") or {}
    saved_articles = int(payload.get("saved_articles") or 0)
    saved_covers = int(payload.get("saved_covers") or 0)
    imported = int(scan.get("imported") or 0)
    matched = int(payload.get("matched_covers") or 0)
    parts: list[str] = []
    if saved_articles:
        parts.append(f"上传 {saved_articles} 个文稿")
    if saved_covers:
        parts.append(f"封面 {saved_covers} 张")
    if imported:
        parts.append(f"入库 {imported} 篇")
    elif saved_articles and not imported:
        parts.append("扫描未新收录（可能重复或已存在）")
    if matched:
        parts.append(f"绑定封面 {matched} 篇")
    if not parts:
        parts.append("无有效上传")
    return {
        "saved_articles": saved_articles,
        "saved_covers": saved_covers,
        "imported": imported,
        "matched_covers": matched,
        "summary_label": " · ".join(parts),
    }


def enrich_upload_response(
    result: dict[str, Any],
    config: Any,
    conn: Any,
) -> dict[str, Any]:
    """附加 upload_summary、chain_summary 与人话链路提示。"""
    from wechat_article_scheduler.wechat_chain_summary import build_wechat_chain_summary

    out = dict(result)
    out["upload_summary"] = format_upload_summary(out)
    scan = out.get("scan") or {}
    if int(out.get("saved_articles") or 0) > 0 or int(scan.get("imported") or 0) > 0:
        chain = build_wechat_chain_summary(config, conn)
        out["chain_summary"] = chain
        hint = chain_hint_after_scan(chain)
        if hint:
            out["chain_hint"] = hint
            human = list(out.get("human") or [])
            if hint not in human:
                human.append(hint)
            out["human"] = human
    if int(scan.get("scanned") or 0) > 0 and out.get("upload_summary"):
        sl = out["upload_summary"]["summary_label"]
        scan_note = f"已联动扫描：{sl}"
        human = list(out.get("human") or [])
        if not any("联动扫描" in h for h in human):
            human.insert(0, scan_note)
        out["human"] = human
    out["ok"] = True
    return out
