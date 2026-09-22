#!/usr/bin/env python3
"""
CausalGate CLI — run the lending domain's causal benchmark and print the
per-level report and deploy recommendations.

Usage:
    python cli.py
"""

import sys

from benchmark import run_report
from domains.lending import build_lending_suite


def main():
    suite = build_lending_suite()
    print(run_report(suite))


if __name__ == "__main__":
    sys.exit(main())
