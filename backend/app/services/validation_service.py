import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
    HAS_YAML = True
except ImportError:
    yaml = None
    HAS_YAML = False
try:
    from sqlalchemy import delete, func, select, update
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload
    from app.models.entities import (
        Alert,
        Application,
        ChecklistResult,
        Document,
        Evidence,
        ExtractedField,
        Finding,
        RefRecord,
        RulePack,
        RulePackVersion,
    )
    HAS_SQLALCHEMY = True
except ImportError:
    delete = func = select = update = selectinload = None
    AsyncSession = Any
    Alert = Application = ChecklistResult = Document = Evidence = ExtractedField = Finding = RefRecord = RulePack = RulePackVersion = Any
    HAS_SQLALCHEMY = False

from app.core.logging import logger
from app.models.enums import (
    ApplicationStateEnum,
    ChecklistResultEnum,
    EvidenceKindEnum,
    FindingSeverityEnum,
    FindingStatusEnum,
    FindingTypeEnum,
)
from app.rules.evaluator import evaluate
from app.services.anomaly_service import AnomalyService, PRELIMINARY_INDICATOR_LABEL
from app.services.audit import AuditService

# Optional rapidfuzz import with pure-Python fallback
try:
    from rapidfuzz import fuzz
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False


def fuzzy_match_ratio(s1: str, s2: str) -> float:
    """Computes similarity ratio (0.0 to 100.0) between two strings."""
    if not s1 or not s2:
        return 0.0
    s1_clean = s1.strip().lower()
    s2_clean = s2.strip().lower()
    if s1_clean == s2_clean:
        return 100.0
    if HAS_RAPIDFUZZ:
        return fuzz.token_sort_ratio(s1_clean, s2_clean)

    # Pure Python Levenshtein fallback
    tokens1 = set(s1_clean.split())
    tokens2 = set(s2_clean.split())
    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)
    return (len(intersection) / len(union)) * 100.0 if union else 0.0


class ValidationService:
    """
    Statutory Application Validation Pipeline.
    Idempotent validation executing:
    - Rule pack evaluation (pure evaluator)
    - Fuzzy cross-document and form-to-document matching (with rapidfuzz)
    - Multi-signal anomaly and duplicate screening (AnomalyService)
    - 0 to 100 review priority scoring
    - Alert generation for missing/expiring documents
    - State transition and cryptographic audit event logging
    """

    @classmethod
    async def validate_application(cls, db: AsyncSession, application_id: str) -> Dict[str, Any]:
        """
        Executes full statutory validation for an application.
        Idempotent: supersedes existing findings without losing audit history.
        """
        # 1. Load Application with documents and extracted fields
        stmt = (
            select(Application)
            .where(Application.id == application_id)
            .options(
                selectinload(Application.documents).selectinload(Document.extracted_fields),
                selectinload(Application.findings).selectinload(Finding.evidence),
            )
        )
        res = await db.execute(stmt)
        app = res.scalar_one_or_none()
        if not app:
            raise ValueError(f"Application '{application_id}' not found.")

        # 2. Load RefRecord for institution
        ref_stmt = select(RefRecord).where(RefRecord.institution_id == app.institution_id)
        ref_res = await db.execute(ref_stmt)
        ref_rec = ref_res.scalar_one_or_none()
        ref_record_data = {}
        if ref_rec:
            ref_record_data = {
                "institution_id": ref_rec.institution_id,
                "previous_eoa": ref_rec.previous_eoa,
                "approved_programmes_and_intake": ref_rec.approved_programmes_and_intake,
                "faculty_count": ref_rec.faculty_count,
                "ter_payment_status": ref_rec.ter_payment_status,
                "deficiency_status": ref_rec.deficiency_status,
            }

        # 3. Load Pinned Rule Pack
        pack_version_str = app.checklist_pack_version or "v1"
        pack_dict = await cls._load_rule_pack(db, pack_version_str)

        # 4. Build Case Context
        case_context = cls._build_case_context(app, ref_record_data)

        # 5. Supersede previous open findings
        for old_finding in app.findings:
            if old_finding.status == FindingStatusEnum.OPEN:
                old_finding.status = FindingStatusEnum.DISMISSED
                old_finding.reason = f"[SUPERSEDED by validation run at {datetime.now(timezone.utc).isoformat()}] {old_finding.reason}"

        # 6. Run Pure Statutory Evaluator
        rule_eval_results = evaluate(pack_dict, case_context)

        # Clear previous checklist results
        await db.execute(delete(ChecklistResult).where(ChecklistResult.application_id == app.id))

        new_findings: List[Finding] = []
        alerts_created: List[Alert] = []

        # 7. Process Rule Evaluation Results into Checklist Results & Findings
        finding_counter = 1
        current_year = datetime.now(timezone.utc).year

        for r in rule_eval_results:
            rule_id = r["rule_id"]
            res_str = r["result"]
            inputs = r["inputs"]
            clause_ref = r.get("clause_ref", "APH-NORMS")
            severity_str = r.get("severity", "review_required")

            # Persist checklist result
            cl_res = ChecklistResult(
                application_id=app.id,
                rule_id=rule_id,
                rule_version=pack_dict.get("version", "v1"),
                result=ChecklistResultEnum(res_str),
                inputs_ref=inputs,
            )
            db.add(cl_res)

            # Generate finding if rule failed
            if res_str in (ChecklistResultEnum.MISSING.value, ChecklistResultEnum.EXPIRED.value, ChecklistResultEnum.INCONSISTENT.value):
                finding_id = f"F-{current_year}-{app.id[-5:]}{finding_counter:04d}"
                finding_counter += 1

                finding_type = FindingTypeEnum.MISSING if res_str == ChecklistResultEnum.MISSING.value else (
                    FindingTypeEnum.EXPIRED if res_str == ChecklistResultEnum.EXPIRED.value else FindingTypeEnum.INCONSISTENT
                )
                severity = FindingSeverityEnum(severity_str)

                # Locate matching document for evidence
                target_doc = None
                target_class = inputs.get("document_class")
                if target_class:
                    for d in app.documents:
                        if d.class_name == target_class:
                            target_doc = d
                            break

                finding = Finding(
                    finding_id=finding_id,
                    application_id=app.id,
                    type=finding_type,
                    severity=severity,
                    title=f"Statutory Deficiency: {rule_id.replace('-', ' ').title()}",
                    reason=r["message"],
                    rule_refs=[clause_ref, rule_id],
                    confidence=0.98,
                    status=FindingStatusEnum.OPEN,
                    model_versions={"rules_evaluator": "fixora-rules-v1"},
                )

                # Attach mandatory evidence
                ev = Evidence(
                    finding_id=finding_id,
                    kind=EvidenceKindEnum.RULE if not target_doc else EvidenceKindEnum.REGION,
                    document_id=target_doc.id if target_doc else None,
                    page=1,
                    bbox=[50.0, 50.0, 250.0, 100.0] if target_doc else None,
                    field=inputs.get("field") or inputs.get("form_field"),
                    value=str(inputs.get("value") or inputs.get("found_count")),
                    threshold=str(inputs.get("min_value") or inputs.get("regex") or inputs.get("expected_status")),
                    record_ref=inputs.get("record_field"),
                )
                finding.evidence.append(ev)
                new_findings.append(finding)
                db.add(finding)

                # Create Alert for missing or expired documents
                if res_str in (ChecklistResultEnum.MISSING.value, ChecklistResultEnum.EXPIRED.value):
                    alert = Alert(
                        application_id=app.id,
                        severity=severity_str,
                        title=f"Statutory Alert: {rule_id}",
                        message=r["message"],
                        acknowledged=False,
                    )
                    alerts_created.append(alert)
                    db.add(alert)

        # 8. Fuzzy Cross-Document & Form Matching (rapidfuzz)
        # Note: A fuzzy match is a flag, never an identity conclusion
        form_name = app.form_data.get("institution_name", "") if app.form_data else ""
        for doc in app.documents:
            extracted_name = ""
            for ef in doc.extracted_fields:
                if ef.name == "institution_name" and ef.normalized_value:
                    extracted_name = ef.normalized_value
                    break

            if form_name and extracted_name:
                ratio = fuzzy_match_ratio(form_name, extracted_name)
                # Field threshold for institution name: 85%
                if ratio < 85.0:
                    f_id = f"F-{current_year}-{app.id[-5:]}{finding_counter:04d}"
                    finding_counter += 1
                    fuzzy_finding = Finding(
                        finding_id=f_id,
                        application_id=app.id,
                        type=FindingTypeEnum.INCONSISTENT,
                        severity=FindingSeverityEnum.REVIEW_REQUIRED,
                        title=f"Institution Name Discrepancy on {doc.class_name.replace('_', ' ').title()}",
                        reason=(
                            f"Discrepancy detected: application declares '{form_name}' but document "
                            f"references '{extracted_name}' (similarity {round(ratio, 1)}% < 85% threshold). "
                            f"Preliminary indicator - human verification required."
                        ),
                        rule_refs=["APH-NAME-CONSISTENCY"],
                        confidence=0.92,
                        label=PRELIMINARY_INDICATOR_LABEL,
                        status=FindingStatusEnum.OPEN,
                        model_versions={"rapidfuzz": "3.8.0"},
                    )
                    ev = Evidence(
                        finding_id=f_id,
                        kind=EvidenceKindEnum.REGION,
                        document_id=doc.id,
                        page=1,
                        bbox=[45.0, 45.0, 300.0, 95.0],
                        field="institution_name",
                        value=extracted_name,
                        measure=f"similarity_ratio={round(ratio, 1)}",
                        threshold="min_similarity=85.0",
                    )
                    fuzzy_finding.evidence.append(ev)
                    new_findings.append(fuzzy_finding)
                    db.add(fuzzy_finding)

        # 9. Anomaly & Duplicate Screening
        for doc in app.documents:
            doc_fields = {ef.name: ef.normalized_value or ef.raw_value for ef in doc.extracted_fields}
            doc_anomalies = await AnomalyService.analyze_document(
                db=db,
                application=app,
                doc=doc,
                extracted_fields=doc_fields,
            )
            for anom in doc_anomalies:
                f_id = f"F-{current_year}-{app.id[-5:]}{finding_counter:04d}"
                finding_counter += 1

                anom_finding = Finding(
                    finding_id=f_id,
                    application_id=app.id,
                    type=anom["type"],
                    severity=anom["severity"],
                    title=anom["title"],
                    reason=anom["reason"],
                    rule_refs=["APH-DOC-INTEGRITY"],
                    confidence=anom.get("confidence", 0.90),
                    label=anom.get("label", PRELIMINARY_INDICATOR_LABEL),
                    status=FindingStatusEnum.OPEN,
                    model_versions={"anomaly_service": "fixora-ela-v1"},
                )

                for ev_dict in anom.get("evidence", []):
                    ev = Evidence(
                        finding_id=f_id,
                        kind=ev_dict["kind"],
                        document_id=ev_dict.get("document_id"),
                        page=ev_dict.get("page", 1),
                        bbox=ev_dict.get("bbox"),
                        measure=ev_dict.get("measure"),
                        threshold=ev_dict.get("threshold"),
                        value=ev_dict.get("value"),
                        record_ref=ev_dict.get("record_ref"),
                    )
                    anom_finding.evidence.append(ev)

                new_findings.append(anom_finding)
                db.add(anom_finding)

        # 10. Review Priority Score Calculation (0 to 100)
        # Never shown to institutions
        priority_score = cls._compute_review_priority(new_findings)
        app.priority_score = priority_score

        # 11. Automated State Transition
        has_critical_deficiency = any(f.severity == FindingSeverityEnum.REVIEW_REQUIRED for f in new_findings)
        has_attention_deficiency = any(f.severity == FindingSeverityEnum.NEEDS_ATTENTION for f in new_findings)

        if has_critical_deficiency or has_attention_deficiency:
            app.state = ApplicationStateEnum.DEFICIENCIES_FOUND
        else:
            app.state = ApplicationStateEnum.READY_FOR_SCRUTINY

        await db.commit()

        # 12. Audit Logging
        await AuditService.log_event(
            db=db,
            actor="system_validator",
            role="system",
            action="VALIDATE_APPLICATION",
            target_type="APPLICATION",
            target_id=app.id,
            payload={
                "application_id": app.id,
                "state": app.state.value,
                "priority_score": app.priority_score,
                "findings_count": len(new_findings),
                "alerts_count": len(alerts_created),
            },
            rule_versions={"checklist_pack": app.checklist_pack_version},
            model_versions={
                "evaluator": "fixora-rules-v1",
                "rapidfuzz": "3.8.0",
                "anomaly_service": "fixora-ela-v1",
            },
        )

        return {
            "application_id": app.id,
            "state": app.state.value,
            "priority_score": app.priority_score,
            "checklist_count": len(rule_eval_results),
            "findings_count": len(new_findings),
            "alerts_count": len(alerts_created),
        }

    @staticmethod
    def _compute_review_priority(findings: List[Any]) -> float:
        """
        Computes 0 to 100 review priority score:
        - review_required: 25 points each
        - needs_attention: 10 points each
        - info: 2 points each
        - anomaly / duplicate signals: +10-20 points corroboration bonus
        """
        score = 0.0
        anomaly_count = 0
        for f in findings:
            sev = f.severity if hasattr(f, "severity") else (f.get("severity") if isinstance(f, dict) else None)
            f_type = f.type if hasattr(f, "type") else (f.get("type") if isinstance(f, dict) else None)

            if sev in (FindingSeverityEnum.REVIEW_REQUIRED, FindingSeverityEnum.REVIEW_REQUIRED.value):
                score += 25.0
            elif sev in (FindingSeverityEnum.NEEDS_ATTENTION, FindingSeverityEnum.NEEDS_ATTENTION.value):
                score += 10.0
            else:
                score += 2.0

            if f_type in (FindingTypeEnum.POSSIBLE_ANOMALY, FindingTypeEnum.POSSIBLE_ANOMALY.value, FindingTypeEnum.DUPLICATE, FindingTypeEnum.DUPLICATE.value):
                anomaly_count += 1

        if anomaly_count > 0:
            score += min(20.0, anomaly_count * 10.0)

        return min(100.0, round(score, 1))

    @classmethod
    def calculate_priority_score(cls, findings: List[Any], case_context: Optional[Dict[str, Any]] = None) -> float:
        """Public method for computing 0 to 100 review priority score from findings."""
        return cls._compute_review_priority(findings)

    @staticmethod
    def _build_case_context(app: Application, ref_record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assembles case context for rule pack evaluator."""
        docs_list = []
        extracted_map = {}

        for doc in app.documents:
            docs_list.append({
                "id": doc.id,
                "class": doc.class_name,
                "class_name": doc.class_name,
                "scan_status": doc.scan_status.value if hasattr(doc.scan_status, "value") else str(doc.scan_status),
                "page_count": doc.page_count,
            })
            for ef in doc.extracted_fields:
                key = f"{doc.class_name}.{ef.name}"
                val = ef.normalized_value or ef.raw_value
                extracted_map[key] = val
                if doc.class_name not in extracted_map:
                    extracted_map[doc.class_name] = {}
                extracted_map[doc.class_name][ef.name] = val

        return {
            "application_id": app.id,
            "category": app.category,
            "academic_year": app.academic_year,
            "form_data": app.form_data or {},
            "ref_records": ref_record_data,
            "ref_record": ref_record_data,
            "documents": docs_list,
            "extracted_fields": extracted_map,
        }

    @staticmethod
    async def _load_rule_pack(db: AsyncSession, pack_version_str: str) -> Dict[str, Any]:
        """Loads rule pack YAML from database or seeded file."""
        stmt = (
            select(RulePackVersion)
            .where(RulePackVersion.version == pack_version_str)
            .where(RulePackVersion.is_active == True)
        )
        res = await db.execute(stmt)
        ver_obj = res.scalar_one_or_none()
        if ver_obj and ver_obj.rules_yaml:
            try:
                return yaml.safe_load(ver_obj.rules_yaml)
            except Exception:
                pass

        # Fallback to local YAML file
        yaml_path = Path("data/rulepacks/eoa_checklist_v1.yaml")
        if yaml_path.exists():
            return yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        return {"id": "EOA-CHECKLIST-v1", "version": "v1", "items": []}
