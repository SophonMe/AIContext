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
SCRIPTS_DIR = os.path.join(AICONTEXT_DIR, "scripts")
LOGS_DIR = os.path.join(AICONTEXT_DIR, "logs")
CONFIG_PATH = os.path.join(AICONTEXT_DIR, "config.json")
CLAUDE_AGENTS_DIR = os.path.expanduser("~/.claude/agents")
CODEX_AGENTS_DIR = os.path.expanduser("~/.codex/agents")
PI_SKILLS_DIR = os.path.expanduser("~/.pi/agent/skills")

LAUNCHD_LABEL = "me.sophon.aicontext"
LAUNCHD_PLIST = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCHD_LABEL}.plist")
SYNC_INTERVAL_SECONDS = 3600  # 1 hour
EXCHANGE_DIR = os.path.join(AICONTEXT_DIR, "exchange")


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


# ── Config ─────────────────────────────────────────────────────────────────

def _save_config(approved: list[tuple]) -> None:
    config = _load_config() or {}
    config["sources"] = [
        {"key": source.source_key, "path": path}
        for source, path in approved
    ]
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


def _run_exchange_sync() -> None:
    """Export local data to exchange dir and import from peers, if pairing is configured."""
    config = _load_config()
    if not config or "device_id" not in config:
        return

    from aicontext.sync import export_skill, import_skills

    device_id = config["device_id"]

    try:
        logger.info("=== P2P Sync ===")
        export_skill(AICONTEXT_DIR, EXCHANGE_DIR, device_id)

        merge_results = import_skills(AICONTEXT_DIR, EXCHANGE_DIR, device_id)
        for r in merge_results:
            if r.activity_inserted or r.activity_updated:
                logger.info("  Merged: %d inserted, %d updated, %d skipped",
                            r.activity_inserted, r.activity_updated, r.activity_skipped)
    except Exception as exc:
        logger.warning("P2P sync failed (will retry next cycle): %s", exc)


def _run_ingest(sources_config: list[dict]) -> list:
    """Ingest, sync peers, rebuild skill, reinstall agent. Used by both install and sync."""
    from aicontext.timestamps import set_timezone
    from aicontext.sources import get_all_sources
    from aicontext.ingester import Ingester
    from aicontext.skill_builder import SkillBuilder
    from aicontext.agent import install_agent, install_codex_agent, install_pi_skill

    set_timezone(_get_local_timezone())

    # Step 1: Ingest local sources
    all_sources = get_all_sources()
    to_run = []
    for entry in sources_config:
        source = all_sources.get(entry["key"])
        path = entry["path"]
        if source and os.path.exists(path):
            to_run.append((source, path))

    results = []
    if to_run:
        ingester = Ingester(DATA_DIR)
        results = ingester.build(to_run)

    # Step 2: P2P exchange sync (export local, import from peers)
    _run_exchange_sync()

    # Step 3: Rebuild skill and agents (includes peer data in stats)
    db_path = os.path.join(DATA_DIR, "activity.db")
    if os.path.exists(db_path):
        SkillBuilder(skill_root=AICONTEXT_DIR, db_path=db_path).build(results)
        install_agent(skill_root=AICONTEXT_DIR, db_path=db_path, agents_dir=CLAUDE_AGENTS_DIR)
        install_codex_agent(skill_root=AICONTEXT_DIR, db_path=db_path, agents_dir=CODEX_AGENTS_DIR)
        install_pi_skill(skill_root=AICONTEXT_DIR, skills_dir=PI_SKILLS_DIR)

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
            print(f"  [ ] {label} — not found")
            continue

        source = all_sources.get(key)
        if source is None:
            print(f"  [ ] {label} — source not available")
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
    print()
    print("Ingesting data...")
    logging.getLogger("aicontext").setLevel(logging.INFO)

    sources_config = [{"key": s.source_key, "path": p} for s, p in approved]
    results = _run_ingest(sources_config)

    total_inserted = sum(r.records_inserted for r in results)
    total_updated = sum(r.records_updated for r in results)
    print()
    print(f"  Ingested: {total_inserted} new records, {total_updated} updated")

    db_path = os.path.join(DATA_DIR, "activity.db")
    _print_ok(f"Generated SKILL.md  -> {os.path.join(AICONTEXT_DIR, 'SKILL.md')}")
    _print_ok(f"Claude Code agent   -> {os.path.join(CLAUDE_AGENTS_DIR, 'sophon-me-context-engine.md')}")
    _print_ok(f"Codex agent         -> {os.path.join(CODEX_AGENTS_DIR, 'sophon-me-context-engine.toml')}")
    _print_ok(f"Pi skill            -> {os.path.join(PI_SKILLS_DIR, 'personal-data')}")

    # 5. Install background sync service
    if sys.platform == "darwin":
        if _install_launchd():
            _print_ok(f"Background sync    -> hourly via launchd ({LAUNCHD_LABEL})")
        else:
            _print_ok("Background sync    -> launchd install failed (run manually: aicontext sync)")

    print()
    print("Done.")
    print()
    print("The sophon-me-context-engine agent is now active in Claude Code, Codex, and Pi.")
    print("Your data syncs automatically every hour.")


def cmd_sync() -> None:
    """Re-ingest all configured sources (called by launchd hourly)."""
    config = _load_config()
    if not config:
        print("No config found. Run 'aicontext install' first.", file=sys.stderr)
        sys.exit(1)

    logging.getLogger("aicontext").setLevel(logging.INFO)
    _run_ingest(config.get("sources", []))


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
    claude_agent = os.path.join(CLAUDE_AGENTS_DIR, "sophon-me-context-engine.md")
    if os.path.exists(claude_agent):
        os.remove(claude_agent)
        removed.append(f"Claude Code agent   -> {claude_agent}")

    codex_agent = os.path.join(CODEX_AGENTS_DIR, "sophon-me-context-engine.toml")
    if os.path.exists(codex_agent):
        os.remove(codex_agent)
        removed.append(f"Codex agent         -> {codex_agent}")

    pi_skill = os.path.join(PI_SKILLS_DIR, "personal-data")
    if os.path.isdir(pi_skill):
        shutil.rmtree(pi_skill)
        removed.append(f"Pi skill            -> {pi_skill}")

    # 3. Remove Syncthing exchange folder registration (best-effort)
    try:
        from aicontext.syncthing import read_api_key, remove_folder
        api_key = read_api_key()
        if api_key:
            remove_folder(api_key)
            removed.append("Syncthing folder   -> aicontext-exchange")
    except Exception:
        pass

    # 4. Remove ~/.aicontext directory (data, config, scripts, logs, SKILL.md, reference)
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


# ── Pair ──────────────────────────────────────────────────────────────

_PAIR_HELP = """\
Usage: aicontext pair [device-id | --status | --web | --lan | --help]

Configure P2P sync with other devices via Syncthing.

  aicontext pair                Show this device's ID
  aicontext pair <device-id>    Add a peer device and start syncing
  aicontext pair --status       Show paired devices and sync status
  aicontext pair --web          Enable sync over the internet (via Syncthing relays)
  aicontext pair --lan          Restrict sync to local network only (default)
  aicontext pair --help         Show this help

Setup (one-time):
  1. Install Syncthing:   brew install syncthing && brew services start syncthing
  2. On this device:      aicontext pair
  3. On other device:     aicontext pair <this-device-id>
  4. Back on this device: aicontext pair <other-device-id>

Adding more devices:
  Pair each new device with any already-paired device.
  All devices discover each other automatically (introducer mode).

Sync mode:
  By default, sync is restricted to the local network (LAN).
  Use --web to enable sync over the internet via Syncthing's encrypted
  relay servers. Use --lan to switch back to LAN-only.
"""


def cmd_pair() -> None:
    """Configure P2P sync with another device via Syncthing."""
    from aicontext.syncthing import (
        check_installed, check_running, read_api_key,
        get_device_id, add_device, ensure_folder, share_folder_with, get_status,
        set_sync_mode, get_sync_mode,
    )

    args = sys.argv[2:]

    if args and args[0] in ("-h", "--help"):
        print(_PAIR_HELP)
        return

    # Check prerequisites
    if not check_installed():
        print("Error: Syncthing is not installed.", file=sys.stderr)
        print()
        print("Install it:")
        print("  brew install syncthing && brew services start syncthing")
        sys.exit(1)

    if not check_running():
        print("Error: Syncthing is not running.", file=sys.stderr)
        print()
        print("Start it:")
        print("  brew services start syncthing")
        sys.exit(1)

    api_key = read_api_key()
    if not api_key:
        print("Error: Could not read Syncthing API key.", file=sys.stderr)
        print("Make sure Syncthing has been started at least once.")
        sys.exit(1)

    my_id = get_device_id(api_key)

    # Save device_id to config
    config = _load_config() or {}
    config["device_id"] = my_id
    os.makedirs(AICONTEXT_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    os.makedirs(EXCHANGE_DIR, exist_ok=True)
    ensure_folder(api_key, EXCHANGE_DIR)

    # Set LAN-only on first pair setup
    if "sync_mode" not in config:
        set_sync_mode(api_key, web=False)
        config["sync_mode"] = "lan"
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    # --web / --lan: switch sync mode
    if args and args[0] == "--web":
        set_sync_mode(api_key, web=True)
        config["sync_mode"] = "web"
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print("Sync mode: web (internet via Syncthing relays)")
        print("Note: All paired devices must also run `aicontext pair --web` for internet sync to work.")
        return

    if args and args[0] == "--lan":
        set_sync_mode(api_key, web=False)
        config["sync_mode"] = "lan"
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print("Sync mode: lan (local network only)")
        return

    # --status: show paired devices
    if args and args[0] == "--status":
        status = get_status(api_key)
        mode = get_sync_mode(api_key)
        print(f"Device ID: {status['my_id']}")
        print(f"Exchange folder: {EXCHANGE_DIR}")
        print(f"Sync mode: {mode}")
        print()
        if not status["devices"]:
            print("No paired devices. Run: aicontext pair <device-id>")
        else:
            print("Paired devices:")
            for d in status["devices"]:
                state = "connected" if d["connected"] else "disconnected"
                name = f" ({d['name']})" if d["name"] else ""
                addr = f"  {d['address']}" if d["address"] and d["connected"] else ""
                print(f"  {d['id'][:20]}...{name}  {state}{addr}")
        return

    has_sources = config.get("sources")

    # No args: print device ID
    if not args:
        print(f"Your device ID:")
        print(f"  {my_id}")
        print()
        print("Run on your other device:")
        print(f"  aicontext pair {my_id}")
        if not has_sources:
            print()
            print("Note: Run `aicontext install` to set up data sources for syncing.")
        return

    # Add peer
    peer_id = args[0].strip()
    if peer_id == my_id:
        print("Error: Cannot pair with yourself.", file=sys.stderr)
        sys.exit(1)

    add_device(api_key, peer_id, introducer=True)
    share_folder_with(api_key, EXCHANGE_DIR, peer_id)

    print(f"Paired with:")
    print(f"  {peer_id}")
    print()
    print(f"Your device ID:")
    print(f"  {my_id}")
    print()
    print("Run on the other device if you haven't already:")
    print(f"  aicontext pair {my_id}")
    if not has_sources:
        print()
        print("Note: Run `aicontext install` to set up data sources for syncing.")


# ── Entry point ────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    if not args or args[0] == "install":
        cmd_install()
    elif args[0] == "sync":
        cmd_sync()
    elif args[0] == "pair":
        cmd_pair()
    elif args[0] == "uninstall":
        cmd_uninstall()
    elif args[0] in ("-h", "--help", "help"):
        print("Usage: aicontext <command>")
        print()
        print("Commands:")
        print("  install     Scan local data, ingest, and install agents")
        print("  sync        Re-ingest all configured sources (runs automatically every hour)")
        print("  pair        Configure P2P sync with another device via Syncthing")
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
