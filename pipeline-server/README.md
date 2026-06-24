# AI DevSecOps Pipeline — Pipeline Server

A multi-agent security pipeline that automatically scans every Pull Request for vulnerabilities before it can be merged into main.

> **Note:** The pipeline server currently lives on the `test-security-scan` branch. Merging this branch into `main` is the recommended next step before deploying to a permanent host.

---

## What it does

When a PR is opened or updated on GitHub, this server automatically runs 3 security agents and posts the results back to the PR as status checks. If any agent finds an issue, the merge is blocked automatically.

The 3 agents are:
- **Code Security Agent** — scans for code vulnerabilities using Semgrep (OWASP Top 10 ruleset). Catches issues like SQL injection, XSS, and unsafe eval() usage.
- **Secret Scan Agent** — detects hardcoded secrets and API keys using TruffleHog.
- **Dependency Scan Agent** — checks all npm dependencies in package.json for known CVEs using the OSV.dev API.

---

## Prerequisites

Before starting the server you need:

1. A **GitHub Personal Access Token (classic)** with `repo` scope
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token
   - Check the `repo` scope and set an expiry
   - Copy the token — you won't be able to see it again

2. A **Webhook Secret** — already configured on the repo under Settings → Webhooks. Ask a team member for the current value if needed.

---

## Setup

### 1. Create the .env file
Inside the `pipeline-server/` folder, create a file called `.env` with the following:

PIPELINE_GITHUB_TOKEN=your_github_token_here
WEBHOOK_SECRET=your_webhook_secret_here

This file is never committed to the repo — you need to create it manually every time.

### 2. Install dependencies and start the server
Run this command in the Codespaces terminal:

```bash
cd /workspaces/scout-pipeline-demo/pipeline-server && pip install -r requirements.txt --break-system-packages -q && pip install semgrep --break-system-packages -q && uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Install TruffleHog
TruffleHog needs to be reinstalled every time Codespaces restarts:

```bash
curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b ~/.local/bin && export PATH=$PATH:~/.local/bin
```

### 4. Set port to Public
Go to the **Ports tab** in Codespaces → right click port 8000 → set to **Public**.

This is required so GitHub can reach the server. If you skip this step, the webhook will time out.

---

## How GitHub triggers the scan

A webhook is configured on the repo under **Settings → Webhooks**. It points to the Codespaces server URL. Every time a PR is opened or a new commit is pushed, GitHub automatically sends a notification to the server — no manual action needed.

> **Important:** The Codespaces URL changes every time a new Codespace is created. If the URL changes, you need to update the webhook URL under Settings → Webhooks to match the new one.

---

## What happens if the server is offline?

If the server is not running, the agents won't post results and the PR will show a pending status. Since all 3 agents are configured as required checks, merges will be blocked until the server is restarted and the webhook is redelivered.

This is the main reason deploying to a permanent host is the recommended next step.

---

## How to add a new agent

All agents live in `pipeline-server/main.py`. To add a new one:

1. Add a `run_newagent()` function that returns a list of findings
2. Add a `create_newagent_status()` function that posts results to the PR using the GitHub Commit Statuses API
3. Call both inside the `run_security_scan()` function alongside the existing agents
4. Add the new agent as a required check under repo Settings → Branches

---

## Recommended next steps

- **Merge to main** — merge `test-security-scan` into `main` so the pipeline server is on the default branch
- **Deploy to a permanent host** — Azure Web App, so the server runs 24/7 without manual startup
- **Add a Master Agent** — aggregates all findings into a single weighted Risk Score (CRITICAL = 3pts, HIGH = 1.5pts, MEDIUM = 0.5pts, normalised 0-10)
- **More agents** — DAST scanning, code coverage, policy compliance
