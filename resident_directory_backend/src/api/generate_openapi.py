import json
import os

from src.api.main import app

"""
Entrypoint: generate OpenAPI schema for the backend and write it to interfaces/openapi.json.

This is used by other containers (e.g., frontend) to integrate against the latest API contract.
"""

openapi_schema = app.openapi()

output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
