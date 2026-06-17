import os

from dotenv import load_dotenv

load_dotenv()
os.environ["AUTH_MODE"] = "client_secret"

from graphmind.auth.token import get_granted_permissions
from graphmind.utils.pagination import paginate_graph

perms = get_granted_permissions()
print("Roles:", sorted(p for p in perms if p))

result = paginate_graph("/users/$count")
if result["ok"]:
    print("Total Entra ID users:", result["data"].get("count", result["pagination"].get("total_items")))
else:
    err = result.get("error") or {}
    print("Count failed:", result["status_code"], err.get("code"), err.get("message"))
    result = paginate_graph("/users", params={"$select": "id"}, aggregate=True, max_pages=100)
    if result["ok"]:
        print("Total (paginated):", result["pagination"]["total_items"])
    else:
        err = result.get("error") or {}
        print("Paginate failed:", result["status_code"], err.get("code"), err.get("message"))
