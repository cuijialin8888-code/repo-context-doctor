"""Dependency reproducibility and package-manager consistency signals."""

from __future__ import annotations

from pathlib import PurePosixPath

from repo_context_doctor.detectors.ecosystems import EcosystemState
from repo_context_doctor.models import Category, Confidence, Finding, Status
from repo_context_doctor.snapshot import RepositorySnapshot

_NODE_LOCKS = {
    "bun.lock": "bun",
    "bun.lockb": "bun",
    "npm-shrinkwrap.json": "npm",
    "package-lock.json": "npm",
    "pnpm-lock.yaml": "pnpm",
    "yarn.lock": "yarn",
}
_OTHER_LOCKS = {"cargo.lock", "go.sum", "pipfile.lock", "poetry.lock", "uv.lock"}


def detect_dependencies(
    snapshot: RepositorySnapshot, state: EcosystemState
) -> tuple[list[Finding], dict[str, bool]]:
    findings: list[Finding] = []
    node_lock_paths = [path for path in snapshot.files if PurePosixPath(path).name.lower() in _NODE_LOCKS]
    node_managers = {_NODE_LOCKS[PurePosixPath(path).name.lower()] for path in node_lock_paths}

    declared_managers: set[str] = set()
    for data in state.package_json.values():
        value = data.get("packageManager")
        if isinstance(value, str) and value:
            declared_managers.add(value.split("@", 1)[0].lower())

    if len(node_managers) > 1:
        findings.append(
            Finding(
                "dependencies.node-lockfiles",
                Category.REPRODUCIBILITY,
                Status.WARN,
                "Multiple Node.js package-manager lockfiles were detected",
                "This can be intentional during migration, but the intended manager is ambiguous.",
                ", ".join(sorted(node_lock_paths)),
                "Confirm the intended package manager and remove stale lockfiles when safe.",
                Confidence.HIGH,
                tuple(sorted(node_lock_paths)),
            )
        )
    elif node_lock_paths:
        findings.append(
            Finding(
                "dependencies.node-lockfiles",
                Category.REPRODUCIBILITY,
                Status.PASS,
                "Node.js lockfile signal is consistent",
                "Exactly one Node package-manager family was detected.",
                ", ".join(sorted(node_lock_paths)),
                "Keep the declared packageManager field aligned with the lockfile when used.",
                Confidence.HIGH,
                tuple(sorted(node_lock_paths)),
            )
        )

    if declared_managers and node_managers and not declared_managers.issubset(node_managers):
        findings.append(
            Finding(
                "dependencies.package-manager-declaration",
                Category.REPRODUCIBILITY,
                Status.WARN,
                "Declared Node.js package manager does not match lockfile signals",
                "The packageManager field and discovered lockfiles name different manager families.",
                f"declared={sorted(declared_managers)}; lockfiles={sorted(node_managers)}",
                "Align package.json packageManager and the committed lockfile.",
                Confidence.HIGH,
                tuple(sorted(state.package_json)),
            )
        )

    other_lock_paths = [path for path in snapshot.files if PurePosixPath(path).name.lower() in _OTHER_LOCKS]
    lock_present = bool(node_lock_paths or other_lock_paths)
    if state.manifests and not lock_present:
        findings.append(
            Finding(
                "dependencies.lock-signal",
                Category.REPRODUCIBILITY,
                Status.INFO,
                "No recognized dependency lockfile was detected",
                "This is not an error; libraries and some ecosystems legitimately omit lockfiles.",
                "Manifest signals exist, but no supported lockfile name was found.",
                "Document the intended reproducibility workflow if it is not obvious.",
                Confidence.HIGH,
                tuple(state.manifests),
            )
        )
    elif lock_present and not node_lock_paths:
        findings.append(
            Finding(
                "dependencies.lock-signal",
                Category.REPRODUCIBILITY,
                Status.PASS,
                "Dependency lockfile signal detected",
                "The scanner records presence only and does not validate dependency freshness.",
                ", ".join(sorted(other_lock_paths)),
                "Keep lockfiles synchronized with their manifests.",
                Confidence.HIGH,
                tuple(sorted(other_lock_paths)),
            )
        )

    consistent = len(node_managers) <= 1 and not (
        declared_managers and node_managers and not declared_managers.issubset(node_managers)
    )
    return findings, {"lock_present": lock_present, "manager_consistent": consistent}

