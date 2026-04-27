#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update and validate release version manifests."
    )
    parser.add_argument("version", help="Release version without a leading 'v'")
    parser.add_argument(
        "--repo",
        default=".",
        help="Repository root to update (default: current directory)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify manifest versions match the target version without writing files",
    )
    return parser.parse_args()


def discover_manifest_paths(repo_root: Path) -> list[Path]:
    paths = [repo_root / "plugin.json", repo_root / ".claude-plugin" / "marketplace.json"]
    paths.extend(repo_root.glob("plugins/**/.claude-plugin/plugin.json"))

    existing = [path for path in paths if path.exists()]
    if not existing:
        raise SystemExit("No managed version manifests were found.")
    return sorted(existing)


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def dump_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def update_manifest(path: Path, version: str, check_only: bool) -> tuple[bool, str]:
    data = load_json(path)
    relative_path = path.as_posix()

    if path.name == "plugin.json":
        current_version = data.get("version")
        if current_version is None:
            raise SystemExit(f"{relative_path} is missing a top-level version field.")

        changed = current_version != version
        if not check_only and changed:
            data["version"] = version
            dump_json(path, data)
        return changed, str(current_version)

    if path.name == "marketplace.json":
        plugins = data.get("plugins")
        if not isinstance(plugins, list) or not plugins:
            raise SystemExit(f"{relative_path} is missing a non-empty plugins array.")

        current_versions = []
        changed = False
        for plugin in plugins:
            current_version = plugin.get("version")
            if current_version is None:
                raise SystemExit(
                    f"{relative_path} has a plugin entry without a version field."
                )
            current_versions.append(str(current_version))
            if current_version != version:
                changed = True
                if not check_only:
                    plugin["version"] = version

        if not check_only and changed:
            dump_json(path, data)

        distinct_versions = sorted(set(current_versions))
        return changed, ", ".join(distinct_versions)

    raise SystemExit(f"Unsupported manifest type: {relative_path}")


def main() -> int:
    args = parse_args()
    version = args.version.removeprefix("v")
    if not SEMVER_RE.match(version):
        raise SystemExit(
            f"Invalid version '{args.version}'. Use semantic versioning like 1.2.3."
        )

    repo_root = Path(args.repo).resolve()
    manifests = discover_manifest_paths(repo_root)

    mismatches: list[str] = []
    changed_paths: list[str] = []

    for manifest in manifests:
        changed, current_version = update_manifest(
            manifest, version=version, check_only=args.check
        )
        relative_path = manifest.relative_to(repo_root).as_posix()
        if args.check:
            if current_version != version:
                mismatches.append(f"{relative_path}: {current_version} != {version}")
        elif changed:
            changed_paths.append(relative_path)

    if args.check:
        if mismatches:
            print("Version check failed:")
            for mismatch in mismatches:
                print(f"  - {mismatch}")
            return 1

        print(f"All managed version manifests already match {version}.")
        return 0

    if changed_paths:
        print(f"Updated release version to {version} in:")
        for path in changed_paths:
            print(f"  - {path}")
    else:
        print(f"All managed version manifests already matched {version}.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
