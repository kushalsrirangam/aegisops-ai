"""Conservative matching for the deterministic demo's small log vocabulary.

The input list is assumed to be in event order. Unknown formats remain unverified.
"""

import re

MISSING_COLUMN = re.compile(
    r'\bcolumn\s+(?:"(?P<quoted>[^"]+)"|(?P<plain>[\w.]+))\s+does\s+not\s+exist\b',
    re.IGNORECASE,
)
DEPLOY_EVENT = re.compile(
    r"\bdeploy(?:ment)?\s+(?:v?\d[\w.-]*\s+)?(?:completed|succeeded)\b"
    r"|\bafter\s+deploy(?:ment)?\s+v\d[\w.-]*"
    r"|\brelease\s+v?\d[\w.-]*\s+rolled\s+out\s+successfully\b",
    re.IGNORECASE,
)
NEGATED_DEPLOY = re.compile(r"\b(?:no|not|never|without)\b.{0,32}\bdeploy(?:ment)?\b", re.IGNORECASE)
STALE_EVENT = re.compile(
    r"\b(?:last\s+week|last\s+month|yesterday|\d+\s+days?\s+ago)\b", re.IGNORECASE
)
MIGRATION_STATUS = re.compile(
    r"\bmigration\b.*\b(?P<status>pending|completed|applied|succeeded|failed)\b",
    re.IGNORECASE,
)
NEGATED_MIGRATION = re.compile(
    r"\b(?:no|not|never|without)\b.{0,32}\bmigration\b", re.IGNORECASE
)
SERVICE_TAG = re.compile(r"\b[a-z][a-z0-9-]*-(?:api|service)\b", re.IGNORECASE)


def _belongs_to_service(line: str, service: str) -> bool:
    tags = {tag.lower() for tag in SERVICE_TAG.findall(line)}
    return not tags or tags == {service.lower()}


def migration_signals(logs: list[str], service: str) -> dict[str, bool]:
    """Correlate a schema error, preceding release, and latest related migration state."""
    missing = []
    deployments = []
    statuses = []
    for index, line in enumerate(logs):
        if not _belongs_to_service(line, service):
            continue
        match = MISSING_COLUMN.search(line)
        if match:
            missing.append((index, (match.group("quoted") or match.group("plain")).lower()))
        if DEPLOY_EVENT.search(line) and not NEGATED_DEPLOY.search(line) and not STALE_EVENT.search(line):
            deployments.append(index)
        status = MIGRATION_STATUS.search(line)
        if status and not NEGATED_MIGRATION.search(line):
            statuses.append((line.lower(), status.group("status").lower()))

    has_deployment = any(deploy < error for deploy in deployments for error, _ in missing)
    has_pending_migration = False
    corroborated = False
    for error_index, column in missing:
        related = [status for line, status in statuses if column in line]
        pending = bool(related) and related[-1] == "pending"
        has_pending_migration |= pending
        corroborated |= pending and any(deploy < error_index for deploy in deployments)
    return {
        "missing_column": bool(missing),
        "deployment": has_deployment,
        "migration_pending": has_pending_migration,
        "corroborated_migration": corroborated,
    }
