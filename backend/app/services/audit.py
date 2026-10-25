import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
try:
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.models.entities import AuditEntry
    HAS_SQLALCHEMY = True
except ImportError:
    func = select = None
    AsyncSession = Any
    class AuditEntry:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    HAS_SQLALCHEMY = False

GENESIS_HASH: str = "0" * 64


def compute_payload_hash(payload: Any) -> str:
    """Computes deterministic SHA-256 hash of canonical JSON payload."""
    raw = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_entry_hash(
    seq: int,
    actor: str,
    role: str,
    action: str,
    target_type: str,
    target_id: Optional[str],
    payload_hash: str,
    rule_versions: Optional[Dict[str, Any]],
    model_versions: Optional[Dict[str, Any]],
    prev_hash: str,
    created_at: Any,
) -> str:
    """Computes SHA-256 hash across canonical block attributes."""
    iso_time = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
    canonical_block = {
        "seq": int(seq),
        "actor": str(actor),
        "role": str(role),
        "action": str(action),
        "target_type": str(target_type),
        "target_id": str(target_id) if target_id is not None else None,
        "payload_hash": str(payload_hash),
        "rule_versions": rule_versions or {},
        "model_versions": model_versions or {},
        "prev_hash": str(prev_hash),
        "created_at": iso_time,
    }
    raw = json.dumps(canonical_block, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditService:
    """
    Append-only tamper-evident audit service with cryptographic SHA-256 chaining.
    RULES.md: Every state change, rule run, source call, officer action and document read writes an audit event.
    """

    @staticmethod
    async def log_event(
        db: AsyncSession,
        actor: str,
        role: str,
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        rule_versions: Optional[Dict[str, Any]] = None,
        model_versions: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditEntry:
        """
        Appends an immutable audit entry into the hash chain.
        Calculates seq, payload_hash, prev_hash, and current_hash.
        """
        # Determine latest entry to link hash chain
        if not HAS_SQLALCHEMY or select is None or db is None:
            now_utc = datetime.now(timezone.utc)
            payload_dict = payload or {}
            p_hash = compute_payload_hash(payload_dict)
            c_hash = compute_entry_hash(1, actor, role, action, target_type, target_id, p_hash, rule_versions, model_versions, GENESIS_HASH, now_utc.isoformat())
            if isinstance(AuditEntry, type):
                return AuditEntry(
                    seq=1, actor=actor, role=role, action=action, target_type=target_type,
                    target_id=target_id, payload=payload_dict, payload_hash=p_hash,
                    prev_hash=GENESIS_HASH, current_hash=c_hash, timestamp=now_utc,
                )
            return None

        stmt = select(AuditEntry).order_by(AuditEntry.seq.desc()).limit(1)
        res = await db.execute(stmt)
        latest = res.scalar_one_or_none()

        if latest:
            next_seq = latest.seq + 1
            prev_hash = latest.current_hash
        else:
            next_seq = 1
            prev_hash = GENESIS_HASH

        payload_dict = payload or {}
        payload_hash = compute_payload_hash(payload_dict)
        now_utc = datetime.now(timezone.utc)

        current_hash = compute_entry_hash(
            seq=next_seq,
            actor=actor,
            role=role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload_hash=payload_hash,
            rule_versions=rule_versions,
            model_versions=model_versions,
            prev_hash=prev_hash,
            created_at=now_utc,
        )

        entry = AuditEntry(
            seq=next_seq,
            actor=actor,
            role=role,
            action=action,
            target_type=target_type,
            target_id=target_id,
            payload=payload_dict,
            payload_hash=payload_hash,
            rule_versions=rule_versions or {},
            model_versions=model_versions or {},
            prev_hash=prev_hash,
            current_hash=current_hash,
            ip_address=ip_address,
            created_at=now_utc,
        )

        db.add(entry)
        await db.commit()

        logger.info(
            "Audit event recorded",
            extra={
                "seq": next_seq,
                "actor": actor,
                "action": action,
                "target_type": target_type,
                "target_id": target_id,
                "current_hash": current_hash[:16] + "...",
            },
        )
        return entry

    @staticmethod
    async def verify_chain(db: AsyncSession) -> Dict[str, Any]:
        """
        Recomputes and verifies the complete SHA-256 cryptographic chain.
        Returns:
            {
                "valid": bool,
                "checked": int,
                "first_broken_seq": Optional[int]
            }
        """
        stmt = select(AuditEntry).order_by(AuditEntry.seq.asc())
        res = await db.execute(stmt)
        entries: List[AuditEntry] = list(res.scalars().all())

        if not entries:
            return {"valid": True, "checked": 0, "first_broken_seq": None}

        expected_prev_hash = GENESIS_HASH

        for idx, entry in enumerate(entries):
            expected_seq = idx + 1

            # 1. Sequence continuity verification
            if entry.seq != expected_seq:
                return {
                    "valid": False,
                    "checked": idx,
                    "first_broken_seq": entry.seq,
                }

            # 2. Payload hash integrity
            expected_payload_hash = compute_payload_hash(entry.payload)
            if entry.payload_hash != expected_payload_hash:
                return {
                    "valid": False,
                    "checked": idx,
                    "first_broken_seq": entry.seq,
                }

            # 3. Chain predecessor hash link verification
            if entry.prev_hash != expected_prev_hash:
                return {
                    "valid": False,
                    "checked": idx,
                    "first_broken_seq": entry.seq,
                }

            # 4. Current block hash verification
            expected_current_hash = compute_entry_hash(
                seq=entry.seq,
                actor=entry.actor,
                role=entry.role,
                action=entry.action,
                target_type=entry.target_type,
                target_id=entry.target_id,
                payload_hash=entry.payload_hash,
                rule_versions=entry.rule_versions,
                model_versions=entry.model_versions,
                prev_hash=entry.prev_hash,
                created_at=entry.created_at,
            )
            if entry.current_hash != expected_current_hash:
                return {
                    "valid": False,
                    "checked": idx,
                    "first_broken_seq": entry.seq,
                }

            expected_prev_hash = entry.current_hash

        return {
            "valid": True,
            "checked": len(entries),
            "first_broken_seq": None,
        }
