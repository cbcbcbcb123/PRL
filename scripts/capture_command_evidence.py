from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one real command's merged output and exit code."
    )
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--exitcode", type=Path, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("a command is required after --")
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.exitcode.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    args.log.write_bytes(completed.stdout)
    args.exitcode.write_text(f"{completed.returncode}\n", encoding="ascii")
    print(f"exit_code={completed.returncode} log={args.log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
