import hmac
import hashlib
import json
import os
import subprocess
import tempfile
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.background import BackgroundTasks
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

GITHUB_TOKEN = os.getenv("PIPELINE_GITHUB_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

def verify_signature(payload: bytes, signature: str) -> bool:
    secret = WEBHOOK_SECRET.encode()
    expected = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

def get_pr_files(repo: str, pr_number: int) -> list:
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    return response.json()

def get_file_content(repo: str, file_path: str, ref: str) -> str:
    url = f"https://api.github.com/repos/{repo}/contents/{file_path}?ref={ref}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        import base64
        content = response.json().get("content", "")
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    return ""

def run_semgrep(files: dict) -> list:
    findings = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for filepath, content in files.items():
            safe_path = os.path.join(tmpdir, os.path.basename(filepath))
            with open(safe_path, "w") as f:
                f.write(content)
        result = subprocess.run(
            ["semgrep", "--config=p/owasp-top-ten", "--json", tmpdir],
            capture_output=True, text=True
        )
        if result.stdout:
            data = json.loads(result.stdout)
            for r in data.get("results", []):
                findings.append({
                    "tool": "semgrep",
                    "file": r["path"],
                    "line": r["start"]["line"],
                    "severity": r["extra"]["severity"],
                    "message": r["extra"]["message"],
                    "rule": r["check_id"]
                })
    return findings

def create_commit_status(repo: str, sha: str, findings: list) -> None:
    url = f"https://api.github.com/repos/{repo}/statuses/{sha}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    state = "failure" if any(
        f["severity"] in ["ERROR", "WARNING"] for f in findings
    ) else "success"
    description = f"Found {len(findings)} issue(s)." if findings else "No issues found. PR is clear."
    if len(description) > 140:
        description = description[:137] + "..."
    payload = {
        "state": state,
        "description": description,
        "context": "Code Security Agent"
    }
    response = requests.post(url, headers=headers, json=payload)
    print(f"Status API response: {response.status_code}", flush=True)

def run_security_scan(repo: str, pr_number: int, sha: str, ref: str):
    pr_files = get_pr_files(repo, pr_number)
    file_contents = {}
    for f in pr_files:
        if f["filename"].endswith((".ts", ".js", ".py", ".html")):
            content = get_file_content(repo, f["filename"], ref)
            if content:
                file_contents[f["filename"]] = content
    findings = run_semgrep(file_contents) if file_contents else []
    create_commit_status(repo, sha, findings)

@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    if not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    event = request.headers.get("X-GitHub-Event", "")
    if event != "pull_request":
        return {"status": "ignored"}
    data = json.loads(body)
    action = data.get("action", "")
    if action not in ["opened", "synchronize", "reopened"]:
        return {"status": "ignored"}
    repo = data["repository"]["full_name"]
    pr_number = data["pull_request"]["number"]
    sha = data["pull_request"]["head"]["sha"]
    ref = data["pull_request"]["head"]["ref"]
    background_tasks.add_task(run_security_scan, repo, pr_number, sha, ref)
    return {"status": "accepted"}

@app.get("/")
def root():
    return {"status": "pipeline server running"}
