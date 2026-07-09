"""
Phase 8 — privileged-action escalation to the n8n human-approval workflow.

When the account agent requests a privileged action (redeem_points), the backend POSTs the
request to the n8n webhook (N8N_ESCALATION_WEBHOOK). n8n presents an approve/deny FORM to a
human; only on approval does the redemption actually apply. This is why v1 tool-auth + escalation
beats a prompt: a privileged action can't self-execute even if the model is fully tricked.

Fire-and-tolerant: if n8n isn't configured/reachable, we still return APPROVAL_REQUIRED (the action
is NOT performed), so the demo never breaks. Set the webhook URL in backend-v1/.env:
  N8N_ESCALATION_WEBHOOK=https://<your-n8n-cloud>/webhook/verde-redeem-approval
"""
import os
import time

import requests


def request_approval(user_id, name, reward, points):
    url = os.environ.get("N8N_ESCALATION_WEBHOOK", "").strip()
    payload = {
        "customer_id": user_id,
        "customer_name": name,
        "reward": reward or "reward",
        "points_balance": points,
        "requested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": "redeem_points",
    }
    if not url:
        return {"sent": False, "reason": "N8N_ESCALATION_WEBHOOK not set", "payload": payload}
    try:
        r = requests.post(url, json=payload, timeout=6)
        return {"sent": r.ok, "status": r.status_code, "payload": payload}
    except Exception as e:
        return {"sent": False, "reason": str(e), "payload": payload}
