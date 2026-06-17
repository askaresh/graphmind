import os

from dotenv import load_dotenv

load_dotenv()
os.environ["AUTH_MODE"] = "client_secret"

from graphmind.utils.pagination import paginate_graph

result = paginate_graph(
    "/deviceManagement/virtualEndpoint/cloudPCs",
    params={
        "$select": "id,displayName,userPrincipalName,servicePlanName,"
        "provisioningPolicyName,managedDeviceName,lastModifiedDateTime",
    },
    aggregate=False,
    max_pages=10,
)

if not result["ok"]:
    err = result.get("error") or {}
    print(f"Failed: {result['status_code']} — {err.get('code')}: {err.get('message')}")
else:
    pcs = result["data"].get("value", [])
    print(f"Cloud PCs ({len(pcs)} total)\n")
    header = f"{'Name':<42} {'User':<38} {'Policy':<28} {'Plan'}"
    print(header)
    print("-" * 130)
    for pc in pcs:
        name = pc.get("displayName") or "(unnamed)"
        user = pc.get("userPrincipalName") or "unassigned"
        policy = pc.get("provisioningPolicyName") or "-"
        plan = pc.get("servicePlanName") or "-"
        print(f"{name[:41]:<42} {user[:37]:<38} {policy[:27]:<28} {plan}")
