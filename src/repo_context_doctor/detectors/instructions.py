"""Inventory documented coding-agent instruction surfaces and scopes."""

from __future__ import annotations

import re
from pathlib import PurePosixPath

from repo_context_doctor.models import (
    Category,
    Confidence,
    Finding,
    InstructionSurface,
    Status,
)
from repo_context_doctor.privacy import sanitize_excerpt
from repo_context_doctor.snapshot import RepositorySnapshot


def _scope_from_parent(path: str) -> str:
    parent = PurePosixPath(path).parent.as_posix()
    return "repository" if parent == "." else f"{parent}/**"


def _frontmatter_value(text: str | None, key: str) -> str | None:
    if not text or not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    block = text[3:end]
    scalar = re.search(rf"(?mi)^\s*{re.escape(key)}\s*:\s*['\"]?([^\n'\"]+)", block)
    if scalar:
        value, _ = sanitize_excerpt(scalar.group(1), limit=160)
        return value
    return None


def _surface(snapshot: RepositorySnapshot, path: str) -> InstructionSurface | None:
    lower = path.lower()
    name = PurePosixPath(path).name.lower()
    kind = ""
    recognized: tuple[str, ...] = ()
    scope = _scope_from_parent(path)
    note = "Inventory only; semantic consistency is not inferred."

    if name == "agents.override.md":
        kind = "agents_override"
        recognized = ("OpenAI Codex",)
        note = "Codex checks this before AGENTS.md in the same directory."
    elif name == "agents.md":
        kind = "agents"
        recognized = ("OpenAI Codex", "GitHub Copilot", "Cursor")
        note = "Nested scope follows vendor-specific rules; closer files generally take precedence."
    elif name == "claude.local.md":
        kind = "claude_local"
        recognized = ("Claude Code",)
        note = "Personal project instruction surface; content is inventoried but not compared."
    elif name == "claude.md":
        kind = "claude"
        recognized = ("Claude Code",)
        if PurePosixPath(path).parent.as_posix() in {".", ".claude"}:
            recognized += ("GitHub Copilot",)
        note = "Claude concatenates ancestor files and loads nested files on demand."
    elif name == "gemini.md":
        kind = "gemini"
        recognized = ("Gemini CLI",)
        if PurePosixPath(path).parent.as_posix() == ".":
            recognized += ("GitHub Copilot",)
        note = "Gemini uses hierarchical context; custom filenames are outside v0.1.0."
    elif lower == ".github/copilot-instructions.md":
        kind = "copilot_repository"
        recognized = ("GitHub Copilot",)
        scope = "repository"
        note = "Repository-wide GitHub Copilot custom instructions."
    elif lower.startswith(".github/instructions/") and lower.endswith(".instructions.md"):
        kind = "copilot_path"
        recognized = ("GitHub Copilot",)
        text = snapshot.read_text(path, max_bytes=16 * 1024)
        scope = _frontmatter_value(text, "applyTo") or "path scope not declared"
        note = "Path-specific Copilot instructions; applyTo is reported without glob expansion."
    elif "/.cursor/rules/" in f"/{lower}" and lower.endswith(".mdc"):
        kind = "cursor_rule"
        recognized = ("Cursor",)
        text = snapshot.read_text(path, max_bytes=16 * 1024)
        scope = _frontmatter_value(text, "globs") or _scope_from_parent(path)
        note = "Cursor .mdc rule; activation semantics are not evaluated."
    elif name == ".cursorrules":
        kind = "cursor_legacy"
        recognized = ("Cursor",)
        note = "Legacy Cursor rule surface; current Cursor docs prefer .cursor/rules or AGENTS.md."
    elif "/.claude/rules/" in f"/{lower}" and lower.endswith(".md"):
        kind = "claude_rule"
        recognized = ("Claude Code",)
        text = snapshot.read_text(path, max_bytes=16 * 1024)
        scope = _frontmatter_value(text, "paths") or _scope_from_parent(path)
        note = "Claude rule surface; paths frontmatter is reported without glob expansion."
    else:
        return None

    return InstructionSurface(path, kind, scope, recognized, note)


def detect_instructions(
    snapshot: RepositorySnapshot,
) -> tuple[list[InstructionSurface], list[Finding], dict[str, bool]]:
    surfaces = [surface for path in sorted(snapshot.files) if (surface := _surface(snapshot, path))]

    override_dirs = {
        PurePosixPath(surface.path).parent.as_posix()
        for surface in surfaces
        if surface.kind == "agents_override"
    }
    if override_dirs:
        updated: list[InstructionSurface] = []
        for surface in surfaces:
            parent = PurePosixPath(surface.path).parent.as_posix()
            if surface.kind == "agents" and parent in override_dirs:
                surface = InstructionSurface(
                    surface.path,
                    surface.kind,
                    surface.scope,
                    surface.recognized_by,
                    "Shadowed for Codex in this directory by AGENTS.override.md; other tools may still read it.",
                )
            updated.append(surface)
        surfaces = updated

    findings: list[Finding] = []
    if surfaces:
        findings.append(
            Finding(
                "instructions.inventory",
                Category.AGENT_CONTEXT,
                Status.PASS,
                f"Detected {len(surfaces)} coding-agent instruction surface(s)",
                "The report includes repository-relative paths, inferred scopes, and vendor recognition.",
                ", ".join(surface.path for surface in surfaces[:8]),
                "Review multiple surfaces periodically for human-maintained consistency.",
                Confidence.HIGH,
                tuple(surface.path for surface in surfaces),
            )
        )
    else:
        findings.append(
            Finding(
                "instructions.inventory",
                Category.AGENT_CONTEXT,
                Status.WARN,
                "No documented coding-agent instruction surface was detected",
                "A repository can still be usable, but agents may need to rediscover commands and boundaries.",
                "No supported instruction filename was present within the bounded scan.",
                "Add one concise, vendor-appropriate instruction surface if repeated agent confusion occurs.",
                Confidence.HIGH,
            )
        )

    kinds = {surface.kind for surface in surfaces}
    if len(kinds) > 1:
        findings.append(
            Finding(
                "instructions.multiple-surfaces",
                Category.AGENT_CONTEXT,
                Status.INFO,
                "Multiple instruction surface types were detected",
                "This is not automatically a conflict; v0.1.0 does not compare prose semantics.",
                ", ".join(sorted(kinds)),
                "Review them for drift when commands or package-manager choices change.",
                Confidence.HIGH,
                tuple(surface.path for surface in surfaces),
            )
        )

    nested = any("/" in surface.path for surface in surfaces if surface.kind in {"agents", "gemini"})
    root = any(surface.scope == "repository" for surface in surfaces)
    return surfaces, findings, {"instruction_any": bool(surfaces), "instruction_root": root, "scoped": nested}

