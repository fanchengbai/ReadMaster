import argparse
from pathlib import Path

from app.core.config import PROJECT_ROOT
from app.services.ecdict_builder import build_ecdict_database


def main() -> None:
    parser = argparse.ArgumentParser(description="将 ECDICT CSV 转换为 ReadMaster 离线词典")
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "data" / "dictionaries" / "ecdict.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "dictionaries" / "ecdict.db",
    )
    args = parser.parse_args()

    result = build_ecdict_database(args.source.resolve(), args.output.resolve())
    print(f"词条：{result.entries:,}")
    print(f"词形：{result.forms:,}")
    print(f"数据库：{args.output.resolve()}")
    print(f"大小：{result.database_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
