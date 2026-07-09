# Phase 8 — n8n Automation (workflow layer)

Two workflows, both importable into **n8n Cloud**:
| File | What it does |
|---|---|
| `escalation_workflow.json` | Human-approval gate for the privileged `redeem_points` action |
| `nightly_regression_workflow.json` | Nightly schedule that triggers the red-team regression canary + alerts on drift |

Host: **local n8n** (`npx n8n` → http://localhost:5678) · Approval channel: **web form in the n8n UI**.

> Why local, not Cloud: n8n Cloud needs a paid workspace, AND it can't reach your local
> `localhost:8001` backend. Local n8n is free, needs no account, and reaches the backend directly —
> so the escalation webhook and nightly trigger work with no tunnel. Start it with `npx n8n`
> (or `docker run -it --rm -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n`).

---

## A. Escalation approval gate (the high-value one)

**Flow:** v1 backend (privileged `redeem_points`) → POST to n8n webhook → n8n shows an **approve/deny
form** to a human → decision branch. The redemption never self-executes — even a fully jailbroken model
can only *request* it. This is the "workflow = human-in-the-loop safety" control.

**Setup (5 min):**
0. Start n8n: `npx n8n` → open http://localhost:5678 → create the local owner login.
1. **Workflows → Import from File** → `escalation_workflow.json`.
2. Open the **Redeem Webhook** node → copy its **Production URL**
   (`http://localhost:5678/webhook/verde-redeem-approval`).
3. Put it in `backend-v1/.env`:
   ```
   N8N_ESCALATION_WEBHOOK=http://localhost:5678/webhook/verde-redeem-approval
   ```
   Restart the v1 server.
4. **Activate** the workflow (toggle top-right).

**Demo:** in the widget (v1), say *"redeem my points for a free bowl"* → bot replies *"sent for
approval, points unchanged"* → in n8n, open the running execution's **form URL** → pick **Approve/Deny**
→ the branch records the decision. Screenshot the form + the branch for the submission.

> Note: the backend does not wait on the human; it returns APPROVAL_REQUIRED immediately (points
> untouched), and the human approves asynchronously in the n8n form. With local n8n, both backend and
> n8n are on localhost, so this (and any callback) works directly — no tunnel, no cloud workspace.

---

## B. Nightly regression canary

The actual regression runner is **local** (it must reach the local v1 bot and read the corpus):
```
python redteam/nightly_regression.py --url http://localhost:8001/api/chat
```
It replays all 100 corpus cases against v1, computes **attack-block-rate** + **over-block-rate**, and
appends a dated entry to `redteam/regression_log.json` (the dashboard's drift data).

**Schedule it locally (Windows Task Scheduler):**
```powershell
schtasks /Create /SC DAILY /ST 03:00 /TN "VerdeBowlRegression" ^
  /TR "C:\Users\laksh\Documents\verde-bowl\backend-v1\.venv\Scripts\python.exe C:\Users\laksh\Documents\verde-bowl\redteam\nightly_regression.py"
```

**n8n orchestration layer** (`nightly_regression_workflow.json`): a **Schedule Trigger (03:00)** →
**HTTP Request** to a runner webhook (`VERDE_REGRESSION_RUNNER`) → **IF block-rate < 90%** → raise
alert / else log OK. With **local** n8n this can reach a local runner directly; simplest is still the
Task Scheduler entry above running the canary, with this workflow as the schedule+alerting layer.
