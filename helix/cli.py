from __future__ import annotations

import argparse

from examples.run_mock_workspace import main as run_mock_workspace


def main() -> None:
    parser = argparse.ArgumentParser(prog="helix")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run-mock-workspace", help="Run the mock workspace benchmark example.")
    args = parser.parse_args()
    if args.command == "run-mock-workspace":
        run_mock_workspace()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
