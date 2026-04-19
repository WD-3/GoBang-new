"""
Entry point for running GoBang as a module.

Usage:
    python -m gobang           # Launch GUI
    python -m gobang web       # Start web server
    python -m gobang cli       # CLI mode
"""

import sys


def main():
    from gobang.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    sys.exit(main())
