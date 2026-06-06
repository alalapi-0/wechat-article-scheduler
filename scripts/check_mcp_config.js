#!/usr/bin/env node
/**
 * 检查 .cursor/mcp.json 是否存在、可解析且符合项目 MCP 安全约定。
 * 不打印任何敏感值。
 */

const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..");
const MCP_PATH = path.join(ROOT, ".cursor", "mcp.json");

const REQUIRED_SERVERS = [
  "chrome-devtools",
  "context7",
  "filesystem",
  "github",
  "playwright",
  "stitch",
];

const SECRET_KEY_PATTERN = /(token|secret|password|api[_-]?key|authorization)/i;
const SECRET_VALUE_PATTERN = /^(ghp_|gho_|ghu_|ghs_|ghr_|sk-|Bearer\s)/i;

const DANGEROUS_PATH_EXACT = new Set(["/", "\\", "C:\\", "C:/", "~", "${userHome}"]);
const HOME_ROOT_PATTERN = /^(\/Users\/[^/]+|\/home\/[^/]+)$/;

function redactEnv(env) {
  const redacted = {};
  for (const [key, value] of Object.entries(env)) {
    if (
      SECRET_KEY_PATTERN.test(key) ||
      (typeof value === "string" && SECRET_VALUE_PATTERN.test(value.trim()))
    ) {
      redacted[key] = "<redacted>";
    } else if (typeof value === "string" && value.startsWith("${")) {
      redacted[key] = value;
    } else {
      redacted[key] = "<set>";
    }
  }
  return redacted;
}

function checkFilesystemArgs(args) {
  const issues = [];
  const pathArgs = args.filter((a) => typeof a === "string" && !a.startsWith("-"));
  for (const arg of pathArgs) {
    const normalized = arg.trim();
    if (DANGEROUS_PATH_EXACT.has(normalized)) {
      issues.push(`filesystem 授权路径过于宽泛: ${JSON.stringify(normalized)}`);
    } else if (HOME_ROOT_PATTERN.test(normalized)) {
      issues.push(`filesystem 指向用户主目录根路径: ${JSON.stringify(normalized)}`);
    }
  }
  if (
    pathArgs.length > 0 &&
    !pathArgs.includes("${workspaceFolder}") &&
    !pathArgs.includes(".")
  ) {
    issues.push(
      "filesystem 未使用 ${workspaceFolder} 或 '.'；请确认仅授权当前项目目录"
    );
  }
  return issues;
}

function summarizeServer(name, cfg) {
  const args = cfg.args ?? [];
  const env = cfg.env ?? {};
  const headers = cfg.headers ?? {};
  const parts = cfg.url
    ? [`${name}: url=${JSON.stringify(cfg.url)}`]
    : [`${name}: command=${JSON.stringify(cfg.command ?? "?")}`];
  if (args.length) {
    const safeArgs = args.map((a) =>
      typeof a === "string" && SECRET_VALUE_PATTERN.test(a.trim()) ? "<redacted>" : a
    );
    parts.push(`args=${JSON.stringify(safeArgs)}`);
  }
  if (Object.keys(env).length) {
    parts.push(`env=${JSON.stringify(redactEnv(env))}`);
  }
  if (Object.keys(headers).length) {
    parts.push(`headers=${JSON.stringify(Object.keys(headers).sort())}`);
  }
  return parts.join(", ");
}

function main() {
  const issues = [];
  const warnings = [];

  if (!fs.existsSync(MCP_PATH)) {
    console.log("check_mcp_config: FAIL");
    console.log(`  missing: ${path.relative(ROOT, MCP_PATH)}`);
    process.exit(1);
  }

  let data;
  try {
    data = JSON.parse(fs.readFileSync(MCP_PATH, "utf8"));
  } catch (err) {
    console.log("check_mcp_config: FAIL");
    console.log(`  invalid JSON: ${err.message}`);
    process.exit(1);
  }

  const servers = data.mcpServers || {};
  if (!Object.keys(servers).length) {
    console.log("check_mcp_config: FAIL");
    console.log("  mcpServers is empty");
    process.exit(1);
  }

  for (const name of REQUIRED_SERVERS) {
    if (!(name in servers)) {
      issues.push(`缺少必需 MCP server: ${name}`);
    }
  }

  for (const [name, cfg] of Object.entries(servers)) {
    if (!cfg || typeof cfg !== "object") {
      issues.push(`server ${JSON.stringify(name)} 配置不是 object`);
      continue;
    }
    const env = cfg.env || {};
    for (const [key, value] of Object.entries(env)) {
      if (typeof value === "string" && SECRET_VALUE_PATTERN.test(value.trim())) {
        issues.push(
          `${name}: env.${key} 含疑似硬编码密钥，应改用 \${env:...} 或 \${GITHUB_PERSONAL_ACCESS_TOKEN}`
        );
      }
    }
    const headers = cfg.headers || {};
    for (const [key, value] of Object.entries(headers)) {
      if (
        SECRET_KEY_PATTERN.test(key) &&
        typeof value === "string" &&
        !value.startsWith("${env:") &&
        !value.startsWith("${input:")
      ) {
        issues.push(`${name}: header ${key} 疑似硬编码敏感值，应改用环境变量占位符`);
      }
    }
    if (name === "filesystem") {
      const args = cfg.args;
      if (!Array.isArray(args)) {
        issues.push("filesystem args 必须是数组");
      } else {
        issues.push(...checkFilesystemArgs(args));
      }
    }
  }

  if (servers.github) {
    const envStr = JSON.stringify(servers.github.env || {});
    if (
      !envStr.includes("GITHUB_TOKEN") &&
      !envStr.includes("GITHUB_PERSONAL_ACCESS_TOKEN")
    ) {
      warnings.push(
        "github MCP 未引用 GITHUB_TOKEN / GITHUB_PERSONAL_ACCESS_TOKEN 环境变量占位符"
      );
    }
  }

  console.log(issues.length ? "check_mcp_config: FAIL" : "check_mcp_config: PASS");
  console.log(`  path: ${path.relative(ROOT, MCP_PATH)}`);
  console.log(
    `  servers (${Object.keys(servers).length}): ${Object.keys(servers).sort().join(", ")}`
  );
  console.log(`  required: ${REQUIRED_SERVERS.join(", ")}`);
  for (const name of Object.keys(servers).sort()) {
    if (servers[name] && typeof servers[name] === "object") {
      console.log(`  - ${summarizeServer(name, servers[name])}`);
    }
  }
  for (const w of warnings) {
    console.log(`  warning: ${w}`);
  }
  for (const issue of issues) {
    console.log(`  issue: ${issue}`);
  }

  process.exit(issues.length ? 1 : 0);
}

main();
