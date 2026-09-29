"""Write the API's OpenAPI schema to a file (input for the TypeScript type generator)."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dining_planner.api.app import create_app  # noqa: E402

with open(sys.argv[1], "w") as f:
    json.dump(create_app(serve_web=False).openapi(), f, indent=2)
    f.write("\n")
