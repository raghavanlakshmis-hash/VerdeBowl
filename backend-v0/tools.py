from rag import search_menu
from seed_data import CUSTOMERS

# NOTE: v0 trusts the model-supplied user_id. That is the IDOR vulnerability.
def tool_search_menu(args, auth_user):
    return "\n".join(search_menu(args["query"]))

def tool_get_orders(args, auth_user):
    uid = args.get("user_id", auth_user)          # VULNERABLE: uses model-supplied id
    cust = CUSTOMERS.get(uid)
    if not cust:
        return "No such customer."
    return "; ".join(f'{o["item"]} (note: {o["note"]})' for o in cust["orders"])

def tool_get_points(args, auth_user):
    uid = args.get("user_id", auth_user)          # VULNERABLE
    cust = CUSTOMERS.get(uid)
    return f'{cust["name"]} has {cust["points"]} points.' if cust else "No such customer."

def tool_redeem(args, auth_user):
    uid = args.get("user_id", auth_user)          # VULNERABLE + no approval gate in v0
    cust = CUSTOMERS.get(uid)
    if not cust:
        return "No such customer."
    cust["points"] = max(0, cust["points"] - 300)
    return f'Redeemed reward for {cust["name"]}. Remaining points: {cust["points"]}.'

DISPATCH = {
    "search_menu": tool_search_menu,
    "get_orders": tool_get_orders,
    "get_points": tool_get_points,
    "redeem_points": tool_redeem,
}

TOOL_SCHEMAS = [
    {"name": "search_menu", "description": "Search the Verde Bowl menu.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "get_orders", "description": "Get a customer's past orders.",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
    {"name": "get_points", "description": "Get a customer's loyalty points.",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}}}},
    {"name": "redeem_points", "description": "Redeem loyalty points for a reward.",
     "input_schema": {"type": "object", "properties": {"user_id": {"type": "string"}, "reward": {"type": "string"}}}},
]
