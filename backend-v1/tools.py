"""
v1 SECURE tools — the headline defense (Layer 3: backend authorization).

The difference from v0 is one idea: the tool NEVER trusts a model-supplied user_id.
Account tools operate ONLY on the authenticated session user. Even if the model is fully
jailbroken and calls get_orders(user_id="cust_1002"), the backend ignores that argument and
serves the authenticated user's own data — so cross-customer IDOR is impossible below the model.

This is the layer that proves: guardrails != authorization. A prompt can be tricked; this cannot.
"""
from rag import search_menu
from seed_data import CUSTOMERS

# Privileged actions that must go through the n8n human-approval gate (Phase 8).
PRIVILEGED = {"redeem_points"}


def _auth_customer(auth_user):
    return CUSTOMERS.get(auth_user)


def tool_search_menu(args, auth_user):
    # Public, safe — no auth needed.
    return "\n".join(search_menu(args["query"]))


def tool_get_orders(args, auth_user):
    # SECURE: model-supplied user_id (if any) is ignored. Only the session user's data.
    cust = _auth_customer(auth_user)
    if not cust:
        return "No authenticated account."
    if args.get("user_id") and args["user_id"] != auth_user:
        return ("ACCESS DENIED: you can only view your own orders. "
                f"(Requested {args['user_id']!r}, authenticated as {auth_user!r}.)")
    return "; ".join(f'{o["item"]} (note: {o["note"]})' for o in cust["orders"])


def tool_get_points(args, auth_user):
    cust = _auth_customer(auth_user)
    if not cust:
        return "No authenticated account."
    if args.get("user_id") and args["user_id"] != auth_user:
        return ("ACCESS DENIED: you can only view your own loyalty points. "
                f"(Requested {args['user_id']!r}, authenticated as {auth_user!r}.)")
    return f'You ({cust["name"]}) have {cust["points"]} points.'


def tool_redeem(args, auth_user):
    # SECURE + privileged: own account only, AND gated behind human approval (n8n, Phase 8).
    cust = _auth_customer(auth_user)
    if not cust:
        return "No authenticated account."
    if args.get("user_id") and args["user_id"] != auth_user:
        return ("ACCESS DENIED: you can only redeem from your own account. "
                f"(Requested {args['user_id']!r}, authenticated as {auth_user!r}.)")
    # The redemption is NOT executed inline. Route to the n8n human-approval workflow.
    import escalation
    res = escalation.request_approval(auth_user, cust["name"], args.get("reward"), cust["points"])
    note = "sent for approval" if res.get("sent") else "queued for approval"
    return ("APPROVAL_REQUIRED: redeeming loyalty points is a privileged action and has been "
            f"{note}. Your points are unchanged until a staff member approves it.")


DISPATCH = {
    "search_menu": tool_search_menu,
    "get_orders": tool_get_orders,
    "get_points": tool_get_points,
    "redeem_points": tool_redeem,
}

# Identical tool SURFACE to v0 (same schemas) so the red-team comparison is fair —
# only the enforcement behind them changes. user_id is accepted but ignored for auth.
TOOL_SCHEMAS = [
    {"name": "search_menu", "description": "Search the Verde Bowl menu.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_orders", "description": "Get the authenticated customer's past orders.",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
    {"name": "get_points", "description": "Get the authenticated customer's loyalty points.",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
    {"name": "redeem_points", "description": "Redeem the authenticated customer's loyalty points (requires approval).",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}, "reward": {"type": "string"}}}},
]
