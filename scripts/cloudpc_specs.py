"""GraphMind workflow: search -> call for Cloud PC hardware specs."""
import json
import os

from dotenv import load_dotenv

load_dotenv()
os.environ["AUTH_MODE"] = "client_secret"

from graphmind.spec.filter import FilterIntent, apply_structural_filter
from graphmind.spec.loader import load_index
from graphmind.reranker.cross_encoder import rerank
from graphmind.utils.graph_client import call_graph

QUERY = "cloud PC hardware specs CPU memory disk size service plan"
REPO = os.getenv("SPEC_REPO_PATH", "./msgraph-metadata")

print("=== GraphMind: search_graph_api ===")
load_index(REPO, quiet=True)
candidates = apply_structural_filter(
    FilterIntent(api_version="v1.0", keyword="cloudPC", exclude_deprecated=True)
).endpoints
if len(candidates) > 20:
    top = rerank(QUERY, candidates, top_k=10)
else:
    top = candidates[:10]

print(f"Top endpoints ({len(top)}):")
for ep in top[:5]:
    print(f"  {ep.method} {ep.path} — {ep.summary}")

print("\n=== GraphMind: call_graph_api ===")
result = call_graph(
    "/deviceManagement/virtualEndpoint/cloudPCs",
    method="GET",
    api_version="v1.0",
    params={"$top": "999"},
)

if not result["ok"]:
    print("Error:", json.dumps(result, indent=2))
    raise SystemExit(1)

items = result["data"].get("value", [])
print(f"\nCloud PCs found: {len(items)}\n")
print(f"{'Name':<45} {'User':<40} {'CPU':<6} {'RAM':<8} {'Disk':<8} Service plan")
print("-" * 130)

for pc in items:
    name = pc.get("displayName") or "(unnamed)"
    user = pc.get("userPrincipalName") or "unassigned"
    plan = pc.get("servicePlanName") or ""
    cpu = ram = disk = "?"
    if plan:
        # e.g. "Cloud PC Enterprise 2vCPU/8GB/128GB"
        parts = plan.replace("Cloud PC Enterprise ", "").replace("Cloud PC ", "")
        for token in parts.replace("/", " ").split():
            if "vCPU" in token:
                cpu = token
            elif token.endswith("GB") and ram == "?":
                ram = token
            elif token.endswith("GB") and ram != "?":
                disk = token
    print(f"{name[:44]:<45} {user[:39]:<40} {cpu:<6} {ram:<8} {disk:<8} {plan}")

print("\nRaw servicePlanName values (from Graph):")
for pc in items:
    print(f"  - {pc.get('displayName', '(unnamed)')}: {pc.get('servicePlanName', 'n/a')}")
