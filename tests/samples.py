# Copyright 2026 Christophe Le Douarec
"""Python snippets with known cognitive complexity."""

SIMPLE = "def simple(x):\n    return x\n"

BRANCHY = (
    "def branchy(x):\n"
    "    if x:\n"
    "        for i in range(3):\n"
    "            if i:\n"
    "                pass\n"
    "    return x\n"
)

NESTED = (
    "def nested(a, b):\n"
    "    if a:\n"
    "        if b:\n"
    "            return 1\n"
    "    return a\n"
)

INVALID = "def broken(:\n    pass\n"
