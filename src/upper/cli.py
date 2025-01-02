import argparse

import upper


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upgrades all your packages!",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="print the version number and exit",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="log debug information during program execution",
    )
    args = parser.parse_args()

    if args.version:
        print(upper.__version__)
        return 0

    if args.debug:
        upper.debug_logging_enabled = True

    ok = upper.upgrade()
    return 0 if ok else 1
