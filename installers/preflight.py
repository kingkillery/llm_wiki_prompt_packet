"""
preflight.py -- pre-install tool checker for llm_wiki_prompt_packet / g-kade.

Usage:
    python3 installers/preflight.py --mode {packet|g-kade} [--skip] [--no-color]

Exit 0 if all required tools are present (or --skip / LLM_WIKI_SKIP_PREFLIGHT=1).
Exit 1 if any required tool is missing.
"""

import argparse
import os
import platform
import shutil
import sys

# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

GREEN  = "\033[32m"
YELLOW = "\033[33m"
RED    = "\033[31m"
RESET  = "\033[0m"

def colorize(text, code, use_color):
    if use_color:
        return code + text + RESET
    return text

# ---------------------------------------------------------------------------
# Install hint registry (keyed by tool-group name, then platform)
# ---------------------------------------------------------------------------

HINTS = {
    "python": {
        "Windows": "  -> install: https://www.python.org/downloads/ (or: winget install Python.Python.3)",
        "Darwin":  "  -> install: brew install python3",
        "Linux":   "  -> install: apt install python3   (or your distro's package manager)",
    },
    "git": {
        "Windows": "  -> install: winget install Git.Git",
        "Darwin":  "  -> install: brew install git",
        "Linux":   "  -> install: apt install git",
    },
    "node": {
        "Windows": "  -> install: winget install OpenJS.NodeJS  (or use https://nodejs.org)",
        "Darwin":  "  -> install: brew install node",
        "Linux":   "  -> install: apt install nodejs npm  (or use https://nodejs.org)",
    },
    "curl": {
        "Windows": "  -> install: winget install cURL.cURL  (Windows 10+ usually has curl bundled)",
        "Darwin":  "  -> install: brew install curl  /  apt install curl",
        "Linux":   "  -> install: brew install curl  /  apt install curl",
    },
    "bun": {
        "_all": "  -> install: https://bun.sh/install",
    },
    "brv": {
        "_all": "  -> install: npm install -g byterover-cli",
    },
}

def get_hint(group, sys_name):
    h = HINTS.get(group, {})
    return h.get("_all") or h.get(sys_name) or h.get("Linux", "")

# ---------------------------------------------------------------------------
# Tool definitions
# Tool entry keys:
#   group    -- label shown in output
#   bins     -- list of binary names; any-one satisfies (OR logic)
#   required -- bool; missing required tool -> exit 1
#   modes    -- None means all modes; list of mode strings to limit scope
#   hint_key -- key into HINTS dict
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "group":    "python3 | python | py",
        "bins":     ["python3", "python", "py"],
        "required": True,
        "modes":    None,
        "hint_key": "python",
    },
    {
        "group":    "git",
        "bins":     ["git"],
        "required": True,
        "modes":    None,
        "hint_key": "git",
    },
    {
        "group":    "curl",
        "bins":     ["curl"],
        "required": True,
        "modes":    ["packet"],
        "hint_key": "curl",
    },
    {
        "group":    "node | npm",
        "bins":     ["node", "npm"],
        "required": True,
        "modes":    None,
        "hint_key": "node",
    },
    {
        "group":    "bun",
        "bins":     ["bun"],
        "required": False,
        "modes":    None,
        "hint_key": "bun",
    },
    {
        "group":    "brv",
        "bins":     ["brv"],
        "required": False,
        "modes":    None,
        "hint_key": "brv",
    },
    {
        "group":    "docker",
        "bins":     ["docker"],
        "required": False,
        "modes":    None,
        "hint_key": None,
    },
]

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser():
    p = argparse.ArgumentParser(
        description="Pre-install tool checker.",
        add_help=True,
    )
    p.add_argument("--mode", required=True, choices=["packet", "g-kade"],
                   help="Install mode (packet or g-kade)")
    p.add_argument("--skip", action="store_true",
                   help="Skip all checks and exit 0")
    p.add_argument("--no-color", dest="no_color", action="store_true",
                   help="Disable ANSI color output")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Honor env-var skip
    if args.skip or os.environ.get("LLM_WIKI_SKIP_PREFLIGHT", "") == "1":
        print("[preflight] skipped (user override)")
        sys.exit(0)

    use_color = (not args.no_color) and sys.stdout.isatty()
    sys_name = platform.system()  # "Windows" / "Darwin" / "Linux"

    print("[preflight] mode = {}  platform = {}".format(args.mode, sys_name))

    missing_required = 0

    for tool in TOOLS:
        # Skip tools scoped to other modes
        if tool["modes"] is not None and args.mode not in tool["modes"]:
            continue

        group   = tool["group"]
        bins    = tool["bins"]
        req     = tool["required"]

        # Find first resolved binary
        resolved = None
        for b in bins:
            found = shutil.which(b)
            if found:
                resolved = (b, found)
                break

        if resolved:
            label = "[ok]"
            colored_label = colorize(label, GREEN, use_color)
            b_name, b_path = resolved
            # Only show resolved path when it adds info (not just bare name on PATH)
            if b_path and b_path != b_name:
                print("{}   {:<12} (resolved: {})".format(colored_label, b_name, b_path))
            else:
                print("{}   {:<12}".format(colored_label, b_name))
        elif req:
            label = "[miss]"
            colored_label = colorize(label, RED, use_color)
            print("{} {:<12}".format(colored_label, group))
            hint = get_hint(tool["hint_key"], sys_name) if tool["hint_key"] else None
            if hint:
                print(hint)
            missing_required += 1
        else:
            label = "[warn]"
            colored_label = colorize(label, YELLOW, use_color)
            # Compose a description suffix for known optional tools
            desc_map = {
                "bun":    "optional, faster pk-qmd install",
                "brv":    "optional, durable memory",
                "docker": "optional, docker-compose path only",
            }
            primary_bin = bins[0]
            desc = desc_map.get(primary_bin, "optional")
            print("{} {} ({})".format(colored_label, primary_bin, desc))
            hint = get_hint(tool["hint_key"], sys_name) if tool["hint_key"] else None
            if hint:
                print(hint)

    # Env-var warnings
    warn_label = colorize("[warn]", YELLOW, use_color)
    if not os.environ.get("BYTEROVER_API_KEY"):
        print("{} BYTEROVER_API_KEY not set (optional, brv query/curate will be unauthenticated)".format(warn_label))
    if not os.environ.get("GEMINI_API_KEY"):
        print("{} GEMINI_API_KEY not set (optional, pk-qmd membed multimodal disabled)".format(warn_label))

    print()

    if missing_required:
        n = missing_required
        plural = "tool" if n == 1 else "tools"
        print("preflight: {} required {} missing".format(n, plural))
        print("hint: re-run after install, or pass --skip-preflight to bypass (you will hit cryptic errors mid-install).")
        sys.exit(1)
    else:
        print("preflight: ok")
        sys.exit(0)


if __name__ == "__main__":
    main()
