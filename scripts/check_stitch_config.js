#!/usr/bin/env node
/**
 * Validate the repository's Stitch MCP setup without reading or printing .env.
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const MCP_PATH = path.join(ROOT, ".cursor", "mcp.json");
const ENV_EXAMPLE_PATH = path.join(ROOT, ".env.example");
const GITIGNORE_PATH = path.join(ROOT, ".gitignore");
const EXPECTED_URL = "https://stitch.googleapis.com/mcp";
const EXPECTED_HEADER_VALUE = "${env:STITCH_API_KEY}";

const REQUIRED_PATHS = [
  "docs/design/DESIGN.md",
  "docs/design/stitch/README.md",
  "docs/design/stitch/STITCH_MCP_SETUP.md",
  "docs/design/stitch/STITCH_WORKFLOW.md",
  "docs/design/stitch/UI_TASKS.md",
  "docs/design/stitch/PROMPT_TEMPLATES.md",
  "docs/design/stitch/EXPORT_GUIDE.md",
  "docs/design/stitch/exports",
  "docs/design/stitch/screenshots",
  "docs/design/stitch/prompts",
  "docs/design/stitch/reviews",
];

const TEXT_EXTENSIONS = new Set([
  ".json",
  ".js",
  ".md",
  ".mdc",
  ".toml",
  ".txt",
  ".yaml",
  ".yml",
]);
const GOOGLE_API_KEY_PATTERN = /AIza[0-9A-Za-z_-]{30,}/;
const SKIP_DIRS = new Set([
  ".git",
  ".idea",
  ".playwright-mcp",
  ".pytest_cache",
  ".venv",
  "node_modules",
]);

function readText(filePath, issues) {
  try {
    return fs.readFileSync(filePath, "utf8");
  } catch (error) {
    issues.push(`无法读取 ${path.relative(ROOT, filePath)}: ${error.code || "error"}`);
    return "";
  }
}

function walkTextFiles(dirPath, output) {
  for (const entry of fs.readdirSync(dirPath, { withFileTypes: true })) {
    if (SKIP_DIRS.has(entry.name) || entry.name === ".env") {
      continue;
    }
    const fullPath = path.join(dirPath, entry.name);
    if (entry.isDirectory()) {
      walkTextFiles(fullPath, output);
    } else if (
      entry.isFile() &&
      (entry.name === ".env.example" || TEXT_EXTENSIONS.has(path.extname(entry.name)))
    ) {
      output.push(fullPath);
    }
  }
}

function main() {
  const issues = [];
  const warnings = [];

  let mcp = null;
  if (!fs.existsSync(MCP_PATH)) {
    issues.push("缺少 .cursor/mcp.json");
  } else {
    try {
      mcp = JSON.parse(readText(MCP_PATH, issues));
    } catch {
      issues.push(".cursor/mcp.json 不是有效 JSON");
    }
  }

  const stitch = mcp?.mcpServers?.stitch;
  if (!stitch || typeof stitch !== "object") {
    issues.push("缺少 mcpServers.stitch");
  } else {
    if (stitch.url !== EXPECTED_URL) {
      issues.push("stitch.url 不是预期的 Google Stitch MCP endpoint");
    }
    const headerValue = stitch.headers?.["X-Goog-Api-Key"];
    if (headerValue !== EXPECTED_HEADER_VALUE) {
      issues.push(
        "stitch 的 X-Goog-Api-Key 必须引用 ${env:STITCH_API_KEY}，不得硬编码"
      );
    }
  }

  const envExample = fs.existsSync(ENV_EXAMPLE_PATH)
    ? readText(ENV_EXAMPLE_PATH, issues)
    : "";
  if (!envExample.match(/^STITCH_API_KEY=/m)) {
    issues.push(".env.example 缺少 STITCH_API_KEY");
  }

  const gitignore = fs.existsSync(GITIGNORE_PATH)
    ? readText(GITIGNORE_PATH, issues)
    : "";
  for (const rule of [".env", ".env.*", "!.env.example"]) {
    if (!gitignore.split(/\r?\n/).includes(rule)) {
      issues.push(`.gitignore 缺少规则: ${rule}`);
    }
  }

  for (const relativePath of REQUIRED_PATHS) {
    if (!fs.existsSync(path.join(ROOT, relativePath))) {
      issues.push(`缺少 Stitch 设计路径: ${relativePath}`);
    }
  }

  const textFiles = [];
  walkTextFiles(ROOT, textFiles);
  const suspectFiles = [];
  for (const filePath of textFiles) {
    const text = readText(filePath, issues);
    if (GOOGLE_API_KEY_PATTERN.test(text)) {
      suspectFiles.push(path.relative(ROOT, filePath));
    }
  }
  if (suspectFiles.length) {
    issues.push(
      `发现疑似硬编码 Google API Key（未输出内容）: ${suspectFiles.join(", ")}`
    );
  }

  if (!process.env.STITCH_API_KEY) {
    warnings.push(
      "当前进程未设置 STITCH_API_KEY；静态配置可通过，但无法验证远端认证"
    );
  }

  console.log(issues.length ? "check_stitch_config: FAIL" : "check_stitch_config: PASS");
  console.log(`  transport: remote (${EXPECTED_URL})`);
  console.log("  auth: X-Goog-Api-Key from environment placeholder");
  console.log(`  design paths: ${REQUIRED_PATHS.length}`);
  console.log(`  scanned text files: ${textFiles.length} (excluded .env)`);
  for (const warning of warnings) {
    console.log(`  warning: ${warning}`);
  }
  for (const issue of issues) {
    console.log(`  issue: ${issue}`);
  }

  process.exit(issues.length ? 1 : 0);
}

main();
