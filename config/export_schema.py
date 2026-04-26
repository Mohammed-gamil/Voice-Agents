import json
from pathlib import Path
from config.schema import TenantConfigFile

def main():
    schema = TenantConfigFile.model_json_schema()
    out_path = Path(__file__).parent / "tenant_config.schema.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Schema successfully exported to {out_path}")

if __name__ == "__main__":
    main()