"""aicontext CLI — install and sync commands."""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.WARNING, format="%(message)s")
logger = logging.getLogger(__name__)


# ── Paths ──────────────────────────────────────────────────────────────────

AICONTEXT_DIR = os.path.expanduser("~/.aicontext")
DATA_DIR = os.path.join(AICONTEXT_DIR, "data")
SKILL_DIR = os.path.join(AICONTEXT_DIR, "skill")
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
LOGS_DIR = os.path.join(AICONTEXT_DIR, "logs")
CONFIG_PATH = os.path.join(AICONTEXT_DIR, "config.json")
CLAUDE_AGENTS_DIR = os.path.expanduser("~/.claude/agents")
CODEX_AGENTS_DIR = os.path.expanduser("~/.codex/agents")
# Cross-harness skills dir — natively discovered by Pi and OpenClaw
SHARED_SKILLS_DIR = os.path.expanduser("~/.agents/skills")

LAUNCHD_LABEL = "sophonme.aicontext"
LAUNCHD_PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist")
SYNC_INTERVAL_SECONDS = 3600  # 1 hour

def _default_chrome_path() -> str | None:
    candidates = [
        os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/History"),
        os.path.expanduser("~/.config/google-chrome/Default/History"),
        os.path.expanduser("~/.config/chromium/Default/History"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _default_edge_path() -> str | None:
    candidates = [
        os.path.expanduser("~/Library/Application Support/Microsoft Edge/Default/History"),
        os.path.expanduser("~/.config/microsoft-edge/Default/History"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def _default_dia_path() -> str | None:
    candidates = [
        os.path.expanduser("~/Library/Application Support/Dia/User Data/Default/History"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


_KNOWN_SOURCES = [
    {
        "key": "claude_code",
        "label": "Claude Code sessions",
        "default_path": os.path.expanduser("~/.claude/projects"),
    },
    {
        "key": "codex",
        "label": "Codex sessions",
        "default_path": os.path.expanduser("~/.codex/sessions"),
    },
    {
        "key": "browser_chrome",
        "label": "Chrome browser history",
        "default_path": _default_chrome_path(),
    },
    {
        "key": "browser_edge",
        "label": "Edge browser history",
        "default_path": _default_edge_path(),
    },
    {
        "key": "browser_dia",
        "label": "Dia browser history",
        "default_path": _default_dia_path(),
    },
    {
        "key": "browser_safari",
        "label": "Safari browser history",
        "default_path": os.path.expanduser("~/Library/Safari/History.db"),
    },
]


# ── Timezone detection ─────────────────────────────────────────────────────

def _get_local_timezone() -> str:
    tz_link = "/etc/localtime"
    if os.path.islink(tz_link):
        target = os.path.realpath(tz_link)
        if "zoneinfo/" in target:
            return target.split("zoneinfo/", 1)[1]
    tz_env = os.environ.get("TZ")
    if tz_env:
        return tz_env
    return "UTC"


# ── Logging ────────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    """Dual logging: console at WARNING, sync.log at DEBUG."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_path = os.path.join(LOGS_DIR, "sync.log")

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    # Console: only warnings and above (print handles user-facing output)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)

    # File: full debug with timestamps for post-mortem debugging
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)


# ── Config ─────────────────────────────────────────────────────────────────

def _save_config(approved: list[tuple]) -> None:
    config = _load_config() or {}

    # Preserve agent-added sources (keys not in _KNOWN_SOURCES)
    known_keys = {s["key"] for s in _KNOWN_SOURCES}
    approved_keys = {source.source_key for source, _ in approved}
    preserved = [
        entry for entry in config.get("sources", [])
        if entry["key"] not in known_keys and entry["key"] not in approved_keys
    ]

    config["sources"] = [
        {"key": source.source_key, "path": path, "mode": source.mode}
        for source, path in approved
    ] + preserved

    os.makedirs(AICONTEXT_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def _load_config() -> dict | None:
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Launchd (macOS) ────────────────────────────────────────────────────────

def _install_launchd() -> bool:
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LAUNCHD_PLIST), exist_ok=True)

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>aicontext.cli</string>
        <string>sync</string>
        <string>--daemon</string>
    </array>
    <key>StartInterval</key>
    <integer>{SYNC_INTERVAL_SECONDS}</integer>
    <key>RunAtLoad</key>
    <false/>
    <key>StandardOutPath</key>
    <string>{os.path.join(LOGS_DIR, "sync.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.join(LOGS_DIR, "sync.log")}</string>
</dict>
</plist>"""

    # Unload existing service if present
    if os.path.exists(LAUNCHD_PLIST):
        subprocess.run(["launchctl", "unload", LAUNCHD_PLIST],
                       capture_output=True)

    with open(LAUNCHD_PLIST, "w") as f:
        f.write(plist)

    result = subprocess.run(["launchctl", "load", LAUNCHD_PLIST],
                            capture_output=True)
    return result.returncode == 0


# ── Helpers ────────────────────────────────────────────────────────────────

def _ask(prompt: str, default_yes: bool = True) -> bool:
    suffix = " [Y/n] " if default_yes else " [y/N] "
    try:
        answer = input(prompt + suffix).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if answer == "":
        return default_yes
    return answer in ("y", "yes")


def _print_ok(msg: str) -> None:
    print(f"  {msg}")


def _clean_error(msg: str) -> str:
    import re
    msg = re.sub(r"^\[Errno \d+\]\s*", "", msg)  # strip [Errno N]
    msg = re.sub(r":\s*'[^']*'$", "", msg)        # strip trailing: '/path/...'
    return msg.strip()


def _print_ingestion_table(results: list) -> None:
    if not results:
        return
    rows = []
    for r in results:
        name = r.source.name
        if r.errors:
            rows.append((name, None, None, None, _clean_error(r.errors[0])))
        else:
            rows.append((name, r.records_parsed, r.records_inserted, r.records_updated, None))

    total_parsed = sum(r.records_parsed for r in results if not r.errors)
    total_new = sum(r.records_inserted for r in results)
    total_updated = sum(r.records_updated for r in results)

    col_name    = max(max(len(r[0]) for r in rows), len("Source"))
    col_parsed  = max(max(len(f"{r[1]:,}") if r[1] is not None else 1 for r in rows), len("Parsed"))
    col_new     = max(max(len(f"{r[2]:,}") if r[2] is not None else 1 for r in rows), len("New"))
    col_updated = max(max(len(f"{r[3]:,}") if r[3] is not None else 1 for r in rows), len("Updated"))

    row_width = col_name + 2 + col_parsed + 2 + col_new + 2 + col_updated
    divider = f"  {'─' * row_width}"
    header  = f"  {'Source':<{col_name}}  {'Parsed':>{col_parsed}}  {'New':>{col_new}}  {'Updated':>{col_updated}}"

    print(header)
    print(divider)
    for name, parsed, new, updated, error in rows:
        if error:
            blank_new     = " " * col_new
            blank_updated = " " * col_updated
            print(f"  {name:<{col_name}}  {'—':>{col_parsed}}  {blank_new}  {blank_updated}  ✗  {error}")
        else:
            print(f"  {name:<{col_name}}  {parsed:>{col_parsed},}  {new:>{col_new},}  {updated:>{col_updated},}")
    print(divider)
    print(f"  {'Total':<{col_name}}  {total_parsed:>{col_parsed},}  {total_new:>{col_new},}  {total_updated:>{col_updated},}")


def _run_ingest(sources_config: list[dict]) -> list:
    """Ingest sources, rebuild skill, reinstall agents. Used by both install and sync."""
    from aicontext.timestamps import set_timezone
    from aicontext.sources import get_all_sources
    from aicontext.ingester import Ingester
    from aicontext.skill_builder import SkillBuilder
    from aicontext.agent import install_agent, install_codex_agent, install_shared_skill

    set_timezone(_get_local_timezone())

    all_sources = get_all_sources()
    to_run = []
    for entry in sources_config:
        key = entry["key"]
        path = os.path.expanduser(entry["path"])
        source = all_sources.get(key)
        if not source:
            logger.warning("Source '%s': not registered — skipping", key)
            continue
        if not os.path.exists(path):
            logger.warning("Source '%s': path not found — %s (skipping)",
                           source.name, path)
            continue
        to_run.append((source, path))

    results = []
    if to_run:
        ingester = Ingester(DATA_DIR)
        results = ingester.build(to_run)

    # Rebuild skill and agents
    db_path = os.path.join(DATA_DIR, "activity.db")
    if os.path.exists(db_path):
        SkillBuilder(skill_root=SKILL_DIR, db_path=db_path).build(results)
        install_agent(skill_root=SKILL_DIR, db_path=db_path, agents_dir=CLAUDE_AGENTS_DIR)
        install_codex_agent(skill_root=SKILL_DIR, db_path=db_path, agents_dir=CODEX_AGENTS_DIR)
        install_shared_skill(skill_root=SKILL_DIR, data_dir=DATA_DIR, skills_dir=SHARED_SKILLS_DIR)

    return results


# ── Commands ───────────────────────────────────────────────────────────────

def cmd_install() -> None:
    print("aicontext install")
    print("─" * 40)
    print()

    # 1. Scan sources
    from aicontext.sources import get_all_sources
    all_sources = get_all_sources()

    approved: list[tuple] = []

    print("Scanning for local data sources...")
    print()
    for spec in _KNOWN_SOURCES:
        key = spec["key"]
        label = spec["label"]
        path = spec["default_path"]

        if path is None or not os.path.exists(path):
            continue

        source = all_sources.get(key)
        if source is None:
            continue

        print(f"  [found] {label}")
        print(f"          {path}")
        if _ask("         Include?"):
            approved.append((source, path))
            print(f"          -> included")
        else:
            print(f"          -> skipped")
        print()

    if not approved:
        print("No sources selected. Nothing to install.")
        return

    print()
    print(f"Installing to {AICONTEXT_DIR}")

    # 2. Create directories and copy query.py
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    query_src = os.path.join(os.path.dirname(__file__), "resources", "query.py")
    shutil.copy2(query_src, os.path.join(SCRIPTS_DIR, "query.py"))

    # 3. Save config for daemon
    _save_config(approved)

    # 4. Run initial ingestion
    _setup_logging()
    logger.info("── aicontext install ──")

    print()
    print("Ingesting data...")

    sources_config = [{"key": s.source_key, "path": p} for s, p in approved]
    results = _run_ingest(sources_config)

    # 5. Install ingest skill (optional — skill may not be bundled)
    try:
        from aicontext.ingest_skill import install as install_ingest_skill
        install_ingest_skill(skills_dir=SHARED_SKILLS_DIR)
    except ImportError:
        pass

    # 5b. Install canvas skill (optional — skill may not be bundled)
    try:
        from aicontext.canvas_skill import install as install_canvas_skill
        install_canvas_skill(skills_dir=SHARED_SKILLS_DIR)
    except ImportError:
        pass

    print()
    _print_ingestion_table(results)
    print()
    _print_ok(f"Generated SKILL.md  -> {os.path.join(SKILL_DIR, 'SKILL.md')}")
    _print_ok(f"Claude Code agent   -> {os.path.join(CLAUDE_AGENTS_DIR, 'sophonme-context-engine.md')}")
    _print_ok(f"Codex agent         -> {os.path.join(CODEX_AGENTS_DIR, 'sophonme-context-engine.toml')}")
    _print_ok(f"Pi / OpenClaw skill -> {os.path.join(SHARED_SKILLS_DIR, 'aicontext-personal')}")
    ingest_skill_path = os.path.expanduser("~/.aicontext/ingest_skill")
    if os.path.isdir(ingest_skill_path):
        _print_ok(f"Ingest skill        -> {ingest_skill_path}")
        _print_ok(f"  Claude Code       -> ~/.claude/skills/aicontext-ingest/ (invoke: /aicontext-ingest)")
        _print_ok(f"  Codex             -> ~/.codex/skills/aicontext-ingest/ (invoke: /aicontext-ingest)")
    canvas_skill_path = os.path.expanduser("~/.aicontext/canvas_skill")
    if os.path.isdir(canvas_skill_path):
        _print_ok(f"Canvas skill        -> {canvas_skill_path}")
        _print_ok(f"  Claude Code       -> ~/.claude/skills/aicontext-canvas/ (invoke: /aicontext-canvas)")
        _print_ok(f"  Codex             -> ~/.codex/skills/aicontext-canvas/ (invoke: /aicontext-canvas)")

    # 6. Install background sync service
    if sys.platform == "darwin":
        if _install_launchd():
            _print_ok(f"Background sync     -> hourly via launchd ({LAUNCHD_LABEL})")
        else:
            _print_ok("Background sync     -> launchd install failed (run manually: aicontext sync)")

    print()
    print("Done. The sophonme-context-engine agent is now active in Claude Code, Codex, Pi, and OpenClaw.")
    print()
    print("Try the following prompts in your agent!")
    print('  "Do thorough research on my history, and infer my MBTI"')
    print('  "Recommend a book, video, or podcast for me"')
    print('  "What do I want to buy the most?"')
    print('  "Show how deeply you know about me"')
    print('  "Check my history and suggest what I should do this weekend"')
    print('  "What is the biggest miss of my daily life that I may not even be aware of?"')
    print()


def cmd_sync(daemon: bool = False) -> None:
    """Re-ingest configured sources.

    When called by the user: runs all sources (including static).
    When called by the daemon (--daemon): skips static sources.
    """
    config = _load_config()
    if not config:
        print("No config found. Run 'aicontext install' first.", file=sys.stderr)
        sys.exit(1)

    _setup_logging()
    logger.info("── aicontext sync%s ──", " (daemon)" if daemon else "")
    sources_config = config.get("sources", [])
    if daemon:
        sources_config = [s for s in sources_config
                          if s.get("mode", "dynamic") != "static"]
    results = _run_ingest(sources_config)
    _print_ingestion_table(results)


def cmd_uninstall() -> None:
    """Remove all aicontext data, agents, and background service."""
    print("aicontext uninstall")
    print("─" * 40)
    print()

    if not _ask("This will remove all aicontext data, agents, and background sync. Continue?", default_yes=False):
        print("Cancelled.")
        return

    removed = []

    # 1. Unload and remove launchd service
    if sys.platform == "darwin" and os.path.exists(LAUNCHD_PLIST):
        subprocess.run(["launchctl", "unload", LAUNCHD_PLIST], capture_output=True)
        os.remove(LAUNCHD_PLIST)
        removed.append(f"Background sync    -> {LAUNCHD_PLIST}")

    # 2. Remove agent files
    claude_agent = os.path.join(CLAUDE_AGENTS_DIR, "sophonme-context-engine.md")
    if os.path.exists(claude_agent):
        os.remove(claude_agent)
        removed.append(f"Claude Code agent   -> {claude_agent}")

    codex_agent = os.path.join(CODEX_AGENTS_DIR, "sophonme-context-engine.toml")
    if os.path.exists(codex_agent):
        os.remove(codex_agent)
        removed.append(f"Codex agent         -> {codex_agent}")

    shared_skill = os.path.join(SHARED_SKILLS_DIR, "aicontext-personal")
    if os.path.isdir(shared_skill):
        shutil.rmtree(shared_skill)
        removed.append(f"Pi / OpenClaw skill -> {shared_skill}")

    # Remove ingest skill from all locations
    for ingest_path in [
        os.path.join(SHARED_SKILLS_DIR, "aicontext-ingest"),
        os.path.expanduser("~/.claude/skills/aicontext-ingest"),
        os.path.expanduser("~/.codex/skills/aicontext-ingest"),
    ]:
        if os.path.islink(ingest_path):
            os.remove(ingest_path)
            removed.append(f"Ingest skill        -> {ingest_path}")
        elif os.path.isdir(ingest_path):
            shutil.rmtree(ingest_path)
            removed.append(f"Ingest skill        -> {ingest_path}")

    # Remove canvas skill from all locations
    for canvas_path in [
        os.path.join(SHARED_SKILLS_DIR, "aicontext-canvas"),
        os.path.expanduser("~/.claude/skills/aicontext-canvas"),
        os.path.expanduser("~/.codex/skills/aicontext-canvas"),
    ]:
        if os.path.islink(canvas_path):
            os.remove(canvas_path)
            removed.append(f"Canvas skill        -> {canvas_path}")
        elif os.path.isdir(canvas_path):
            shutil.rmtree(canvas_path)
            removed.append(f"Canvas skill        -> {canvas_path}")

    # 3. Remove ~/.aicontext directory (data, config, scripts, logs, SKILL.md, reference)
    if os.path.isdir(AICONTEXT_DIR):
        shutil.rmtree(AICONTEXT_DIR)
        removed.append(f"Data directory      -> {AICONTEXT_DIR}")

    if removed:
        print("Removed:")
        for item in removed:
            _print_ok(item)
    else:
        print("Nothing to remove — aicontext is not installed.")

    print()
    print("Done.")


# ── Entry point ────────────────────────────────────────────────────────────

def cmd_viewer(argv: list[str]) -> None:
    """Launch the local HTML viewer for activity.db."""
    import argparse as _argparse
    from aicontext.viewer import run as _run_viewer

    parser = _argparse.ArgumentParser(prog="aicontext viewer",
                                      description="Local HTML viewer for activity.db")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    _run_viewer(port=args.port)


def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "install":
        cmd_install()
    elif args[0] == "sync":
        cmd_sync(daemon="--daemon" in args)
    elif args[0] == "uninstall":
        cmd_uninstall()
    elif args[0] == "viewer":
        cmd_viewer(args[1:])
    elif args[0] in ("-h", "--help", "help"):
        print("Usage: aicontext <command>")
        print()
        print("Commands:")
        print("  install     Scan local data, ingest, and install agents")
        print("  sync        Re-ingest all configured sources")
        print("  sync --daemon  Re-ingest dynamic sources only (used by hourly background sync)")
        print("  viewer      Launch local HTML viewer for activity.db")
        print("  uninstall   Remove all data, agents, and background sync")
    elif args[0] in ("-v", "--version", "version"):
        from aicontext import __version__
        print(f"aicontext {__version__}")
    else:
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        print("Run 'aicontext --help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
