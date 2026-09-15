# Copyright 2026 Christophe Le Douarec
"""Entry point for ``python -m complexity_python_monitoring``."""

import sys

from complexity_python_monitoring.cli import main

if __name__ == "__main__":
    sys.exit(main())
