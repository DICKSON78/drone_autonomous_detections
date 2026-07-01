#!/usr/bin/env python3
"""
Manual CLI test script for the NLU parser.

Usage:
    python tests/test_parser_cli.py "fly to forest at 25 meters"
    python tests/test_parser_cli.py --interactive
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from nlu_parser import parse_command


def show(parsed: dict) -> None:
    print()
    print(f"  success    : {parsed['success']}")
    print(f"  intent     : {parsed['intent']}")
    print(f"  altitude   : {parsed['altitude']}")
    print(f"  location   : {parsed['location']}")
    print(f"  target_gps : {parsed['target_gps']}")
    print(f"  confidence : {parsed['confidence']}")
    if parsed.get("reason"):
        print(f"  reason     : {parsed['reason']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the NLU command parser")
    parser.add_argument("text", nargs="*", help="Command text to parse")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    if args.interactive:
        print("NLU Parser CLI — type commands or 'quit' to exit.")
        print("Examples: take off, land, fly to forest at 25m, rtl, hover, arm")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line or line.lower() in ("quit", "exit", "q"):
                break
            result = parse_command(line)
            show(result)
        return

    if args.text:
        text = " ".join(args.text)
        result = parse_command(text)
        show(result)
        return

    # Demo mode — run a battery of examples
    examples = [
        "take off",
        "take off to 20 meters",
        "launch",
        "land",
        "land at 5m",
        "fly to forest",
        "go to building at 15 meters",
        "fly to -6.163, 35.752 at 30m",
        "return home",
        "rtl",
        "hover",
        "stop",
        "arm",
        "disarm",
        "go to base",
        "climb to 50",
        "dance for me",
        "",
    ]
    print("NLU Parser — demo run")
    print("=" * 50)
    for ex in examples:
        if ex:
            print(f"\nInput: {ex!r}")
        else:
            print(f"\nInput: (empty)")
        result = parse_command(ex)
        show(result)


if __name__ == "__main__":
    main()
