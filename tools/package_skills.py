"""Package every Skill in skills/ into a reproducible ZIP under dist/."""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".key", ".pem"}
EXCLUDED_NAMES = {".env", ".DS_Store"}


def declared_skill_name(skill_dir: Path) -> str:
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", text, re.MULTILINE)
    if not match:
        raise ValueError(f"{skill_dir.name}: SKILL.md 缺少有效的 name")
    if match.group(1) != skill_dir.name:
        raise ValueError(f"{skill_dir.name}: name 与目录名不一致")
    return skill_dir.name


def source_files(skill_dir: Path) -> list[Path]:
    files = []
    for path in skill_dir.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(skill_dir)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if path.suffix.lower() in EXCLUDED_SUFFIXES or path.name in EXCLUDED_NAMES:
            continue
        if path.name.startswith(".env."):
            continue
        files.append(path)
    return sorted(files)


def archive_bytes(skill_dir: Path) -> bytes:
    name = declared_skill_name(skill_dir)
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path in source_files(skill_dir):
            info = ZipInfo(
                f"{name}/{path.relative_to(skill_dir).as_posix()}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


def package_skills(skills_dir: Path, dist_dir: Path, *, check: bool) -> int:
    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if not skill_dirs:
        raise ValueError(f"没有找到 Skill：{skills_dir}")
    failed = False
    for skill_dir in skill_dirs:
        expected = archive_bytes(skill_dir)
        target = dist_dir / f"{skill_dir.name}.zip"
        if check:
            if not target.is_file() or target.read_bytes() != expected:
                print(f"需要更新：{skill_dir.name}")
                failed = True
            else:
                print(f"已同步：{skill_dir.name}")
            continue
        dist_dir.mkdir(parents=True, exist_ok=True)
        target.write_bytes(expected)
        print(f"已打包：{skill_dir.name} -> {target}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=PROJECT_ROOT / "skills")
    parser.add_argument("--dist-dir", type=Path, default=PROJECT_ROOT / "dist")
    parser.add_argument("--check", action="store_true", help="只检查 ZIP 是否与源码同步")
    args = parser.parse_args()
    try:
        return package_skills(args.skills_dir, args.dist_dir, check=args.check)
    except (OSError, ValueError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
