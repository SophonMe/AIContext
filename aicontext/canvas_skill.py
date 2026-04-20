"""Install the aicontext-canvas skill to coding agent platforms."""

import logging
import os
import shutil

logger = logging.getLogger(__name__)

CANVAS_SKILL_DIR = os.path.expanduser("~/.aicontext/canvas_skill")
CANVAS_OUTPUT_DIR = os.path.expanduser("~/.aicontext/canvas")


def _find_source() -> str | None:
    """Locate the aicontext-canvas skill directory relative to this package."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(pkg_dir, os.pardir, "aicontext-canvas"))
    if os.path.isdir(candidate) and os.path.isfile(os.path.join(candidate, "SKILL.md")):
        return candidate
    return None


def _symlink(link_path: str, target: str) -> None:
    """Create a symlink, removing any existing file/dir at link_path."""
    os.makedirs(os.path.dirname(link_path), exist_ok=True)
    if os.path.islink(link_path):
        os.remove(link_path)
    elif os.path.isdir(link_path):
        shutil.rmtree(link_path)
    elif os.path.exists(link_path):
        os.remove(link_path)
    os.symlink(target, link_path)


def install(skills_dir: str) -> str | None:
    """Install the aicontext-canvas skill.

    1. Copy skill files to ~/.aicontext/canvas_skill/
    2. Ensure ~/.aicontext/canvas/ output directory exists
    3. Symlink from ~/.agents/skills/ (Pi/OpenClaw)
    4. Symlink from ~/.claude/skills/ (Claude Code — invoked as /aicontext-canvas)
    5. Symlink from ~/.codex/skills/ (Codex — invoked as /aicontext-canvas)

    Returns the installed skill path, or None if the source wasn't found.
    """
    source_dir = _find_source()
    if source_dir is None:
        logger.warning("aicontext-canvas skill source not found — skipping install")
        return None

    if os.path.exists(CANVAS_SKILL_DIR):
        shutil.rmtree(CANVAS_SKILL_DIR)
    shutil.copytree(source_dir, CANVAS_SKILL_DIR)

    os.makedirs(CANVAS_OUTPUT_DIR, exist_ok=True)

    _symlink(os.path.join(skills_dir, "aicontext-canvas"), CANVAS_SKILL_DIR)

    claude_skills_dir = os.path.expanduser("~/.claude/skills")
    _symlink(os.path.join(claude_skills_dir, "aicontext-canvas"), CANVAS_SKILL_DIR)

    codex_skills_dir = os.path.expanduser("~/.codex/skills")
    _symlink(os.path.join(codex_skills_dir, "aicontext-canvas"), CANVAS_SKILL_DIR)

    logger.info("Installed canvas skill: %s", CANVAS_SKILL_DIR)
    return CANVAS_SKILL_DIR
