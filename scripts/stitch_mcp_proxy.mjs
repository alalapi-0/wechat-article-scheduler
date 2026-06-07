#!/usr/bin/env node
/**
 * Local stdio MCP proxy for Google Stitch.
 * Reads STITCH_API_KEY from the environment; never prints the key.
 * Used by .cursor/mcp.json — not part of application runtime.
 */

import { StitchProxy } from "@google/stitch-sdk";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const apiKey = process.env.STITCH_API_KEY?.trim();
if (!apiKey) {
  process.stderr.write(
    "stitch_mcp_proxy: STITCH_API_KEY 未设置。请在 Cursor 进程环境或 .env 中配置后重启 Cursor。\n"
  );
  process.exit(1);
}

const proxy = new StitchProxy({ apiKey });
const transport = new StdioServerTransport();
await proxy.start(transport);
