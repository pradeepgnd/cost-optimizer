"""Preview, then explicitly publish/register a pinned source bundle in a dedicated namespace."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.adapters.live_zetaris import ZetarisDataLayer
from app.source_contracts import StorageConfig
from app.source_registry import bundle_plan, register_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Publish to storage, register missing sources and query exact content.")
    parser.add_argument("--no-dotenv", action="store_true")
    parser.add_argument("--bindings-output", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    layer = None
    try:
        config = StorageConfig.model_validate_json(args.storage.read_text())
        report = bundle_plan(args.bundle, config)
        if args.apply:
            if not args.no_dotenv:
                from dotenv import load_dotenv
                load_dotenv(ROOT / ".env")
            layer = ZetarisDataLayer()
            report = register_bundle(layer, args.bundle, config)
            if args.bindings_output:
                serialized = json.dumps(report["bindings"], indent=2) + "\n"
                if args.bindings_output.exists() and json.loads(args.bindings_output.read_text()) != report["bindings"]:
                    raise ValueError("existing bindings differ; use a new output path")
                args.bindings_output.parent.mkdir(parents=True, exist_ok=True)
                args.bindings_output.write_text(serialized)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2) + "\n")
        summary = {key: value for key, value in report.items() if key != "bindings"}
        summary["bindings_output"] = str(args.bindings_output) if args.bindings_output and args.apply else None
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"status": "fail", "error_type": type(error).__name__,
            "message": "Publication/registration not accepted. Existing sources were not dropped or replaced."}), file=sys.stderr)
        return 1
    finally:
        if layer:
            layer.client.close()


if __name__ == "__main__":
    sys.exit(main())
