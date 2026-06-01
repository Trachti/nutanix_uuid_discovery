# Nutanix UUID Discovery Script

A Python script for discovering Nutanix cluster UUIDs and subnet UUIDs from Prism Central.

The script connects to Nutanix Prism Central, lists clusters and subnets, and can print the results as tables, JSON, or ready-to-copy Python configuration blocks.

## Features

- Discovers Nutanix cluster UUIDs
- Discovers Nutanix subnet UUIDs
- Shows subnet VLAN IDs
- Shows subnet cluster references
- Prints readable tables
- Prints ready-to-copy Python configuration blocks
- Can export discovery results as JSON
- Uses only the Python standard library

## Requirements

- Python 3.8 or newer
- Network access to Nutanix Prism Central
- A valid Nutanix Prism Central API token

No external Python packages are required.

## Configuration

Before running the script, update these values in `nutanix_uuid_discovery.py`:

```python
NTNX_PRISMCENTRAL_IP = "YOUR_IP:9440"
PC_TOKEN = "YOUR GENERATED TOKEN FROM nutanix_auth.py"
```

## Usage

Print tables and Python configuration blocks:

```bash
python nutanix_uuid_discovery.py
```

Print only tables:

```bash
python nutanix_uuid_discovery.py --output table
```

Print only ready-to-copy Python configuration blocks:

```bash
python nutanix_uuid_discovery.py --output config
```

Print JSON output:

```bash
python nutanix_uuid_discovery.py --output json
```

Write JSON output to a file:

```bash
python nutanix_uuid_discovery.py --json-file nutanix-uuid-discovery.json
```

## Example Output

```text
Clusters
--------
Name       UUID                                  External IP
---------  ------------------------------------  -----------
cluster01  00000000-0000-0000-0000-000000000000  10.0.0.10

Subnets
-------
Name        UUID                                  VLAN  Cluster
----------  ------------------------------------  ----  --------
vlan-80     00000000-0000-0000-0000-000000000000  80    cluster01
```

Example configuration block:

```python
CLUSTER_UUIDS = {
    "cluster01": "00000000-0000-0000-0000-000000000000",
}

SUBNET_UUIDS = {
    "cluster01": {
        "80": "00000000-0000-0000-0000-000000000000",
    },
}
```

## Security Notes

Do not commit real API tokens, passwords, cluster UUIDs, subnet UUIDs, Prism Central addresses, or internal infrastructure details to a public GitHub repository.

The script currently disables SSL certificate verification by using:

```python
ssl._create_unverified_context()
```

This may be useful in lab environments, but it is not recommended for production. For production use, configure proper certificate validation.

## Disclaimer

This script is provided as an example. Test it in a safe environment before using it against production Nutanix infrastructure.
