import http.client
import json
import argparse
import ssl
from datetime import datetime, timezone

NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
PC_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"


def get_conn():
    context = ssl._create_unverified_context()
    return http.client.HTTPSConnection(NTNX_PRISMCENTRAL_IP, context=context)


def api_request(method, url, payload=None):
    conn = get_conn()
    headers = {
        "Accept": "application/json",
        "Authorization": PC_TOKEN,
        "Content-Type": "application/json"
    }

    body = None
    if payload is not None:
        body = payload if isinstance(payload, str) else json.dumps(payload)

    conn.request(method, url, body=body, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8")

    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        data = {"raw": raw}

    if res.status >= 400:
        raise RuntimeError(f"API error {res.status} on {url}: {data}")

    return data


def list_entities(kind, endpoint, page_size=100):
    offset = 0
    results = []

    while True:
        payload = {
            "kind": kind,
            "length": page_size,
            "offset": offset
        }

        data = api_request("POST", endpoint, payload)
        entities = data.get("entities", [])

        if not entities:
            break

        results.extend(entities)

        metadata = data.get("metadata", {})
        total_matches = metadata.get("total_matches")

        offset += page_size

        if total_matches is not None and offset >= total_matches:
            break

    return results


def safe_get(data, *paths):
    for path in paths:
        current = data
        for key in path:
            if not isinstance(current, dict):
                current = None
                break
            current = current.get(key)
        if current not in (None, ""):
            return current
    return None


def discover_clusters():
    entities = list_entities("cluster", "/api/nutanix/v3/clusters/list")
    clusters = []

    for item in entities:
        name = safe_get(
            item,
            ("spec", "name"),
            ("status", "name"),
            ("metadata", "name")
        )

        uuid = safe_get(
            item,
            ("metadata", "uuid"),
            ("spec", "uuid"),
            ("status", "uuid")
        )

        external_ip = safe_get(
            item,
            ("status", "resources", "network", "external_ip"),
            ("spec", "resources", "network", "external_ip"),
            ("status", "resources", "config", "service_list", "external_ip")
        )

        clusters.append({
            "name": name,
            "uuid": uuid,
            "external_ip": external_ip,
            "raw": item
        })

    return clusters


def discover_subnets():
    entities = list_entities("subnet", "/api/nutanix/v3/subnets/list")
    subnets = []

    for item in entities:
        name = safe_get(
            item,
            ("spec", "name"),
            ("status", "name"),
            ("metadata", "name")
        )

        uuid = safe_get(
            item,
            ("metadata", "uuid"),
            ("spec", "uuid"),
            ("status", "uuid")
        )

        vlan_id = safe_get(
            item,
            ("spec", "resources", "vlan_id"),
            ("status", "resources", "vlan_id"),
            ("spec", "resources", "vlanId"),
            ("status", "resources", "vlanId")
        )

        cluster_uuid = safe_get(
            item,
            ("spec", "cluster_reference", "uuid"),
            ("status", "cluster_reference", "uuid"),
            ("spec", "resources", "cluster_reference", "uuid"),
            ("status", "resources", "cluster_reference", "uuid")
        )

        cluster_name = safe_get(
            item,
            ("spec", "cluster_reference", "name"),
            ("status", "cluster_reference", "name"),
            ("spec", "resources", "cluster_reference", "name"),
            ("status", "resources", "cluster_reference", "name")
        )

        subnets.append({
            "name": name,
            "uuid": uuid,
            "vlan_id": vlan_id,
            "cluster_uuid": cluster_uuid,
            "cluster_name": cluster_name,
            "raw": item
        })

    return subnets


def print_table(title, rows, columns):
    print(f"\n{title}")
    print("-" * len(title))

    if not rows:
        print("No entries found.")
        return

    widths = {}
    for key, label in columns:
        values = [str(row.get(key, "") or "") for row in rows]
        widths[key] = max(len(label), *(len(value) for value in values))

    header = "  ".join(label.ljust(widths[key]) for key, label in columns)
    print(header)
    print("  ".join("-" * widths[key] for key, _ in columns))

    for row in rows:
        print("  ".join(str(row.get(key, "") or "").ljust(widths[key]) for key, _ in columns))


def print_config_blocks(clusters, subnets):
    print("\nPython Configuration Blocks")
    print("---------------------------")

    print("\nCLUSTER_UUIDS = {")
    for cluster in clusters:
        name = cluster.get("name") or "cluster-name"
        uuid = cluster.get("uuid") or "cluster-uuid"
        key = str(name).lower().replace(" ", "_").replace("-", "_")
        print(f'    "{key}": "{uuid}",')
    print("}")

    print("\nSUBNET_UUIDS = {")
    grouped = {}
    for subnet in subnets:
        cluster_key = (
            str(subnet.get("cluster_name") or subnet.get("cluster_uuid") or "cluster")
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )
        grouped.setdefault(cluster_key, []).append(subnet)

    for cluster_key, items in grouped.items():
        print(f'    "{cluster_key}": {{')
        for subnet in items:
            vlan_id = subnet.get("vlan_id")
            name = subnet.get("name")
            uuid = subnet.get("uuid")
            key = str(vlan_id if vlan_id is not None else name)
            print(f'        "{key}": "{uuid}",')
        print("    },")
    print("}")


def write_json_file(path, clusters, subnets):
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prism_central": NTNX_PRISMCENTRAL_IP,
        "clusters": [
            {key: value for key, value in cluster.items() if key != "raw"}
            for cluster in clusters
        ],
        "subnets": [
            {key: value for key, value in subnet.items() if key != "raw"}
            for subnet in subnets
        ]
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"\nJSON output written to: {path}")


def main():
    parser = argparse.ArgumentParser(
        description="Discover Nutanix cluster and subnet UUIDs from Prism Central."
    )
    parser.add_argument(
        "--output",
        choices=["table", "config", "json", "all"],
        default="all",
        help="Output format"
    )
    parser.add_argument(
        "--json-file",
        required=False,
        help="Optional path to write discovery results as JSON"
    )

    args = parser.parse_args()

    clusters = discover_clusters()
    subnets = discover_subnets()

    if args.output in ("table", "all"):
        print_table(
            "Clusters",
            clusters,
            [
                ("name", "Name"),
                ("uuid", "UUID"),
                ("external_ip", "External IP"),
            ]
        )

        print_table(
            "Subnets",
            subnets,
            [
                ("name", "Name"),
                ("uuid", "UUID"),
                ("vlan_id", "VLAN"),
                ("cluster_name", "Cluster"),
                ("cluster_uuid", "Cluster UUID"),
            ]
        )

    if args.output in ("config", "all"):
        print_config_blocks(clusters, subnets)

    if args.output == "json":
        print(json.dumps({
            "clusters": [
                {key: value for key, value in cluster.items() if key != "raw"}
                for cluster in clusters
            ],
            "subnets": [
                {key: value for key, value in subnet.items() if key != "raw"}
                for subnet in subnets
            ]
        }, indent=2, ensure_ascii=False))

    if args.json_file:
        write_json_file(args.json_file, clusters, subnets)


if __name__ == "__main__":
    main()
