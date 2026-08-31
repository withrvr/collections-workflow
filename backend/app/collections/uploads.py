"""Where uploaded workbooks are kept on disk so a run's original file can
be downloaded again later (GET /collections/runs/{id}/download).

/tmp rather than a proper object store -- this is a local assessment
demo, not a production deployment (see docs/ARCHITECTURE.md's
production-hardening notes for what changes at scale: S3/blob storage,
a retention policy, none of it needed here). Every stored file is
prefixed with a random token so two uploads of files sharing a name
never collide.
"""

from __future__ import annotations

import secrets
from pathlib import Path

UPLOAD_DIR = Path("/tmp/collections-uploads")


def save_upload(filename: str, content: bytes) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename or "upload.xlsx").name  # strip any path components
    dest = UPLOAD_DIR / f"{secrets.token_hex(8)}_{safe_name}"
    dest.write_bytes(content)
    return dest
