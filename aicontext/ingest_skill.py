"""Install the aicontext-ingest skill to coding agent platforms."""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger(__name__)

INGEST_SKILL_DIR = os.path.expanduser("~/.aicontext/ingest_skill")


def _find_source() -> str | None:
    """Locate the aicontext-ingest skill directory relative to this package."""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.normpath(os.path.join(pkg_dir, os.pardir, "aicontext-ingest"))
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
    """Install the aicontext-ingest skill.

    1. Copy skill files to ~/.aicontext/ingest_skill/
    2. Symlink from ~/.agents/skills/ (Pi/OpenClaw)
    3. Symlink from ~/.claude/skills/ (Claude Code — invoked as /aicontext-ingest)
    4. Symlink from ~/.codex/skills/ (Codex — invoked as /aicontext-ingest)

    Returns the installed skill path, or None if the source wasn't found.
    """
    source_dir = _find_source()
    if source_dir is None:
        logger.warning("aicontext-ingest skill source not found — skipping install")
        return None

    # 1. Copy skill files to ~/.aicontext/ingest_skill/
    if os.path.exists(INGEST_SKILL_DIR):
        shutil.rmtree(INGEST_SKILL_DIR)
    shutil.copytree(source_dir, INGEST_SKILL_DIR)

    # 2. Symlink from ~/.agents/skills/ (Pi/OpenClaw)
    _symlink(os.path.join(skills_dir, "aicontext-ingest"), INGEST_SKILL_DIR)

    # 3. Symlink from ~/.claude/skills/ (Claude Code)
    claude_skills_dir = os.path.expanduser("~/.claude/skills")
    _symlink(os.path.join(claude_skills_dir, "aicontext-ingest"), INGEST_SKILL_DIR)

    # 4. Symlink from ~/.codex/skills/ (Codex)
    codex_skills_dir = os.path.expanduser("~/.codex/skills")
    _symlink(os.path.join(codex_skills_dir, "aicontext-ingest"), INGEST_SKILL_DIR)

    logger.info("Installed ingest skill: %s", INGEST_SKILL_DIR)
    return INGEST_SKILL_DIR
