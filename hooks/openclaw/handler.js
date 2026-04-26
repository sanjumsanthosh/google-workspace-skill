import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SKILL_ROOT = path.resolve(__dirname, "../..");
const HELPER = path.join(SKILL_ROOT, "scripts", "google_helper.py");

function loadDotenv(root) {
  const envPath = path.join(root, ".env");
  if (!fs.existsSync(envPath)) {
    return {};
  }

  const result = {};
  for (const line of fs.readFileSync(envPath, "utf8").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const index = trimmed.indexOf("=");
    const key = trimmed.slice(0, index).trim();
    let value = trimmed.slice(index + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    result[key] = value;
  }
  return result;
}

export default async function handler(ctx) {
  const { command, args = [] } = ctx.input || {};

  if (!command) {
    return ctx.reply({ error: "No command provided. Use list_tasks, create_task, search_emails, etc." });
  }

  try {
    const env = { ...process.env, ...loadDotenv(SKILL_ROOT) };
    const output = execFileSync("python3", [HELPER, command, ...args.map(String)], {
      env,
      encoding: "utf8",
      timeout: 30000
    });
    return ctx.reply(JSON.parse(output));
  } catch (err) {
    const stderr = err.stderr ? String(err.stderr) : "";
    const stdout = err.stdout ? String(err.stdout) : "";
    let detail = stdout || stderr || err.message;

    try {
      detail = JSON.parse(detail);
    } catch {
      // Keep raw detail if the helper failed before producing JSON.
    }

    return ctx.reply({ error: "google-workspace command failed", detail });
  }
}

