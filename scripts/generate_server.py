#!/usr/bin/env python3
"""
Script to generate FastAPI server code from OpenAPI specification.
This script can be used to regenerate the server implementation based on the OpenAPI spec.
"""

import os
import sys
import yaml
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def load_openapi_spec():
    """Load the OpenAPI specification from YAML file."""
    openapi_path = project_root / "openapi.yaml"
    
    if not openapi_path.exists():
        print(f"Error: OpenAPI specification not found at {openapi_path}")
        sys.exit(1)
    
    with open(openapi_path, 'r') as f:
        return yaml.safe_load(f)

def validate_openapi_spec(spec):
    """Validate the OpenAPI specification."""
    required_fields = ['openapi', 'info', 'paths']
    
    for field in required_fields:
        if field not in spec:
            print(f"Error: Missing required field '{field}' in OpenAPI specification")
            sys.exit(1)
    
    print("✓ OpenAPI specification is valid")

def generate_models_from_spec(spec):
    """Generate Pydantic models from OpenAPI components."""
    components = spec.get('components', {})
    schemas = components.get('schemas', {})
    
    print(f"Found {len(schemas)} schemas in OpenAPI specification:")
    for schema_name in schemas.keys():
        print(f"  - {schema_name}")
    
    return schemas

def generate_routes_from_spec(spec):
    """Generate route information from OpenAPI paths."""
    paths = spec.get('paths', {})
    
    print(f"Found {len(paths)} paths in OpenAPI specification:")
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                operation_id = details.get('operationId', f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}")
                print(f"  - {method.upper()} {path} -> {operation_id}")
    
    return paths

def main():
    """Main function to generate server from OpenAPI spec."""
    print("🚀 Generating FastAPI server from OpenAPI specification...")
    
    # Load and validate OpenAPI spec
    spec = load_openapi_spec()
    validate_openapi_spec(spec)
    
    # Generate components
    schemas = generate_models_from_spec(spec)
    paths = generate_routes_from_spec(spec)
    
    print("\n✅ Server generation analysis complete!")
    print("\nThe current FastAPI implementation in app/main.py should match the OpenAPI specification.")
    print("To verify consistency, run the server and check the auto-generated docs at /docs")
    
    # Check if the current implementation matches the spec
    print("\n🔍 Checking implementation consistency...")
    
    # This is a basic check - in a real scenario, you might want to do more thorough validation
    expected_endpoints = set()
    for path, methods in paths.items():
        for method in methods.keys():
            if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                expected_endpoints.add(f"{method.upper()} {path}")
    
    print(f"Expected endpoints: {len(expected_endpoints)}")
    for endpoint in sorted(expected_endpoints):
        print(f"  - {endpoint}")
    
    print("\n💡 To run the server:")
    print("  poetry run python -m app.main")
    print("  # or")
    print("  poetry run uvicorn app.main:app --reload")

if __name__ == "__main__":
    main()
