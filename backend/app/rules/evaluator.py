import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.enums import ChecklistResultEnum, FindingSeverityEnum, InfrastructureOutputEnum


def _parse_date(date_val: Any) -> Optional[datetime]:
    if not date_val:
        return None
    if isinstance(date_val, datetime):
        return date_val.replace(tzinfo=timezone.utc) if date_val.tzinfo is None else date_val
    date_str = str(date_val).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%B-%Y", "%d-%b-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _get_nested(data: Dict[str, Any], path: str) -> Any:
    """Helper to retrieve nested fields by dot path, e.g. 'form_data.principal_name'."""
    if not data or not path:
        return None
    curr = data
    for part in path.split("."):
        if isinstance(curr, dict):
            curr = curr.get(part)
        else:
            return None
    return curr


def evaluate_item(item: Dict[str, Any], context: Dict[str, Any], pack_version: str) -> Dict[str, Any]:
    """
    Evaluates a single rule item against case_context.
    RULES.md Checklist vocabulary: PRESENT, MISSING, EXPIRED, INCONSISTENT, VERIFIED, NEEDS_EVIDENCE.
    """
    item_id = item.get("id", "RULE-ITEM")
    clause_ref = item.get("clause_ref", "APH-CLAUSE")
    severity = item.get("severity", FindingSeverityEnum.REVIEW_REQUIRED.value)
    item_type = item["type"]
    msg_template = item.get("message_template", "")

    form_data = context.get("form_data", {})
    documents = context.get("documents", [])
    extracted_fields = context.get("extracted_fields", {})
    ref_record = context.get("ref_record") or context.get("ref_records") or {}
    now_utc = context.get("as_of_date") or datetime.now(timezone.utc)
    if isinstance(now_utc, str):
        now_utc = _parse_date(now_utc) or datetime.now(timezone.utc)

    inputs: Dict[str, Any] = {}
    result = ChecklistResultEnum.VERIFIED
    details = ""
    infra_output = None

    # 1. document_required
    if item_type == "document_required":
        target_class = item.get("document_class") or item.get("target_document_class")
        inputs["document_class"] = target_class
        found = [d for d in documents if d.get("class") == target_class or d.get("class_name") == target_class]
        inputs["found_count"] = len(found)
        if found:
            result = ChecklistResultEnum.PRESENT
            details = f"Document '{target_class}' uploaded and verified present."
        else:
            result = ChecklistResultEnum.MISSING
            details = f"Mandatory statutory document '{target_class}' is missing."

    # 2. document_validity
    elif item_type == "document_validity":
        target_class = item.get("document_class") or item.get("target_document_class")
        inputs["document_class"] = target_class
        found = [d for d in documents if d.get("class") == target_class or d.get("class_name") == target_class]
        if not found:
            result = ChecklistResultEnum.MISSING
            details = f"Document '{target_class}' missing; cannot verify validity."
        else:
            doc = found[0]
            field_name = item.get("field_name")
            validity_check = item.get("validity_check")

            expiry_str = doc.get("expiry_date") or extracted_fields.get(f"{target_class}.expiry_date")
            if not expiry_str and field_name and validity_check == "must_not_be_expired":
                expiry_str = extracted_fields.get(f"{target_class}.{field_name}") or extracted_fields.get(target_class, {}).get(field_name)

            issue_str = doc.get("issue_date") or extracted_fields.get(f"{target_class}.issue_date")
            if not issue_str and field_name and (validity_check == "max_age_days" or "age" in str(item)):
                issue_str = extracted_fields.get(f"{target_class}.{field_name}") or extracted_fields.get(target_class, {}).get(field_name)

            inputs["expiry_date"] = expiry_str
            inputs["issue_date"] = issue_str

            is_expired = False
            must_not_be_expired = item.get("must_not_be_expired", validity_check == "must_not_be_expired" if validity_check else True)
            if must_not_be_expired and expiry_str:
                dt_exp = _parse_date(expiry_str)
                if dt_exp and dt_exp < now_utc:
                    is_expired = True

            max_age_days = item.get("max_age_days")
            if max_age_days is not None and issue_str:
                dt_issue = _parse_date(issue_str)
                if dt_issue and (now_utc - dt_issue).days > max_age_days:
                    is_expired = True

            if is_expired:
                result = ChecklistResultEnum.EXPIRED
                details = f"Document '{target_class}' has expired or exceeded maximum statutory validity age."
            else:
                result = ChecklistResultEnum.VERIFIED
                details = f"Document '{target_class}' is valid and unexpired."

    # 3. field_required
    elif item_type == "field_required":
        field_path = item.get("field") or item.get("field_name")
        val = _get_nested(context, field_path)
        if val is None:
            val = _get_nested(form_data, field_path)
        inputs["field"] = field_path
        inputs["value"] = val
        if val is not None and str(val).strip() != "":
            result = ChecklistResultEnum.VERIFIED
            details = f"Required statutory field '{field_path}' is declared."
        else:
            result = ChecklistResultEnum.MISSING
            details = f"Required statutory field '{field_path}' is missing or blank."

    # 4. field_format
    elif item_type == "field_format":
        field_path = item.get("field") or item.get("field_name")
        pattern = item.get("regex") or item.get("regex_pattern")
        val = _get_nested(context, field_path)
        if val is None:
            val = _get_nested(form_data, field_path)
        inputs["field"] = field_path
        inputs["value"] = val
        inputs["regex"] = pattern
        if val is None or str(val).strip() == "":
            result = ChecklistResultEnum.MISSING
            details = f"Field '{field_path}' not provided for format verification."
        elif re.match(pattern, str(val)):
            result = ChecklistResultEnum.VERIFIED
            details = f"Field '{field_path}' complies with statutory format."
        else:
            result = ChecklistResultEnum.INCONSISTENT
            details = f"Field '{field_path}' value does not match statutory pattern '{pattern}'."

    # 5. cross_field_consistency
    elif item_type == "cross_field_consistency":
        field_a = item["field_a"]
        field_b = item["field_b"]
        val_a = _get_nested(context, field_a)
        if val_a is None:
            val_a = _get_nested(form_data, field_a)
        val_b = _get_nested(context, field_b)
        if val_b is None:
            val_b = _get_nested(form_data, field_b)
        inputs["field_a"] = field_a
        inputs["value_a"] = val_a
        inputs["field_b"] = field_b
        inputs["value_b"] = val_b
        op = item.get("operator", "==")

        if val_a is None or val_b is None:
            result = ChecklistResultEnum.NEEDS_EVIDENCE
            details = f"Cannot compare '{field_a}' and '{field_b}': one or both fields are missing."
        else:
            match = False
            if op == "==":
                match = (str(val_a).strip().lower() == str(val_b).strip().lower())
            elif op == ">=":
                match = float(val_a) >= float(val_b)
            elif op == "<=":
                match = float(val_a) <= float(val_b)

            if match:
                result = ChecklistResultEnum.VERIFIED
                details = f"Cross-field consistency verified between '{field_a}' and '{field_b}'."
            else:
                result = ChecklistResultEnum.INCONSISTENT
                details = f"Cross-field discrepancy detected: '{field_a}' ({val_a}) does not match '{field_b}' ({val_b})."

    # 6. form_to_document_match
    elif item_type == "form_to_document_match":
        form_field = item["form_field"]
        doc_field = item["document_field"]
        target_doc_class = item.get("target_document_class")
        form_val = _get_nested(form_data, form_field)
        doc_val = _get_nested(extracted_fields, doc_field)
        if doc_val is None and target_doc_class:
            doc_val = extracted_fields.get(target_doc_class, {}).get(doc_field)
        inputs["form_field"] = form_field
        inputs["form_value"] = form_val
        inputs["document_field"] = doc_field
        inputs["document_value"] = doc_val

        if form_val is None or doc_val is None:
            result = ChecklistResultEnum.NEEDS_EVIDENCE
            details = f"Awaiting extracted document field '{doc_field}' to match against declared '{form_field}'."
        else:
            clean_form = re.sub(r"\s+", " ", str(form_val).strip().lower())
            clean_doc = re.sub(r"\s+", " ", str(doc_val).strip().lower())
            if clean_form in clean_doc or clean_doc in clean_form:
                result = ChecklistResultEnum.VERIFIED
                details = f"Form declaration '{form_field}' matches verified document text '{doc_field}'."
            else:
                result = ChecklistResultEnum.INCONSISTENT
                details = f"Mismatch between application declaration '{form_val}' and document extract '{doc_val}'."

    # 7. form_to_record_match
    elif item_type == "form_to_record_match":
        form_field = item["form_field"]
        record_field = item["record_field"]
        tolerance_pct = float(item.get("tolerance_percent", 0.0))
        form_val = _get_nested(form_data, form_field)
        rec_val = _get_nested(ref_record, record_field)
        inputs["form_field"] = form_field
        inputs["form_value"] = form_val
        inputs["record_field"] = record_field
        inputs["record_value"] = rec_val
        inputs["tolerance_percent"] = tolerance_pct

        if form_val is None or rec_val is None:
            result = ChecklistResultEnum.NEEDS_EVIDENCE
            details = f"Statutory reference record '{record_field}' unavailable for verification."
        else:
            try:
                num_form = float(form_val)
                num_rec = float(rec_val)
                delta = abs(num_form - num_rec)
                max_allowed = (tolerance_pct / 100.0) * num_rec if num_rec > 0 else 0
                if delta <= max_allowed:
                    result = ChecklistResultEnum.VERIFIED
                    details = f"Declaration matches AICTE reference record '{record_field}' within {tolerance_pct}% tolerance."
                else:
                    result = ChecklistResultEnum.INCONSISTENT
                    details = f"Discrepancy: declared {num_form} vs statutory record {num_rec} (exceeds {tolerance_pct}% tolerance)."
            except (ValueError, TypeError):
                if str(form_val).strip().lower() == str(rec_val).strip().lower():
                    result = ChecklistResultEnum.VERIFIED
                    details = f"Declaration matches AICTE reference record '{record_field}'."
                else:
                    result = ChecklistResultEnum.INCONSISTENT
                    details = f"Discrepancy: declared '{form_val}' does not match statutory record '{rec_val}'."

    # 8. record_status
    elif item_type == "record_status":
        field = item["record_field"]
        expected_status = item["expected_status"]
        actual_status = _get_nested(ref_record, field)
        inputs["record_field"] = field
        inputs["expected_status"] = expected_status
        inputs["actual_status"] = actual_status

        if actual_status is None:
            result = ChecklistResultEnum.NEEDS_EVIDENCE
            details = f"Statutory record field '{field}' not found in registry."
        elif str(actual_status).upper() == str(expected_status).upper():
            result = ChecklistResultEnum.VERIFIED
            details = f"Statutory status verified: '{field}' is '{actual_status}'."
        else:
            result = ChecklistResultEnum.INCONSISTENT
            details = f"Statutory requirement unmet: '{field}' is '{actual_status}', expected '{expected_status}'."

    # 9. numeric_threshold
    elif item_type == "numeric_threshold":
        field = item.get("field") or item.get("field_name")
        min_val = item.get("min_value")
        max_val = item.get("max_value")
        op = item.get("operator")
        thresh = item.get("threshold_value")
        if thresh is not None:
            if op in (">=", ">"):
                min_val = thresh
            elif op in ("<=", "<"):
                max_val = thresh

        actual_val = _get_nested(context, field)
        if actual_val is None:
            actual_val = _get_nested(form_data, field)
        inputs["field"] = field
        inputs["actual_value"] = actual_val
        inputs["min_value"] = min_val
        inputs["max_value"] = max_val

        if actual_val is None:
            result = ChecklistResultEnum.NEEDS_EVIDENCE
            details = f"Field '{field}' unavailable for threshold evaluation."
        else:
            try:
                num = float(actual_val)
                passed = True
                if min_val is not None and num < float(min_val):
                    passed = False
                if max_val is not None and num > float(max_val):
                    passed = False

                if passed:
                    result = ChecklistResultEnum.VERIFIED
                    details = f"Numeric parameter '{field}' ({num}) meets statutory threshold criteria."
                else:
                    result = ChecklistResultEnum.INCONSISTENT
                    details = f"Numeric parameter '{field}' ({num}) violates statutory threshold (min: {min_val}, max: {max_val})."
            except (ValueError, TypeError):
                result = ChecklistResultEnum.INCONSISTENT
                details = f"Could not parse numeric parameter '{field}' value '{actual_val}'."

    # 10. conditional
    elif item_type == "conditional":
        condition = item.get("if") or item.get("if_condition", {})
        then_rule = item.get("then") or item.get("then_rule", {})
        cond_field = condition.get("field")
        expected_val = condition.get("equals")
        actual_cond_val = _get_nested(context, cond_field)
        if actual_cond_val is None:
            actual_cond_val = _get_nested(form_data, cond_field)
        inputs["condition_field"] = cond_field
        inputs["condition_expected"] = expected_val
        inputs["condition_actual"] = actual_cond_val

        condition_met = False
        if "field_present" in condition:
            condition_met = (_get_nested(context, condition["field_present"]) is not None or
                             _get_nested(form_data, condition["field_present"]) is not None)
        elif expected_val is not None and actual_cond_val is not None:
            condition_met = (str(actual_cond_val).strip().lower() == str(expected_val).strip().lower())

        if condition_met:
            sub_res = evaluate_item(then_rule, context, pack_version)
            sub_res["inputs"].update(inputs)
            return sub_res
        else:
            result = ChecklistResultEnum.VERIFIED
            details = f"Conditional trigger condition not met ({cond_field}={actual_cond_val}); requirement waived."

    # 11. infrastructure_norm
    elif item_type == "infrastructure_norm":
        # Supports both lab count norms and area norms
        actual_field = item.get("actual_field")
        norm_field = item.get("norm_field")
        if actual_field and norm_field:
            actual_val = float(_get_nested(form_data, actual_field) or 0)
            norm_val = float(_get_nested(form_data, norm_field) or 1)
            ratio = actual_val / norm_val if norm_val > 0 else 0
            inputs["actual"] = actual_val
            inputs["norm"] = norm_val
            inputs["ratio"] = ratio
            if ratio >= 1.0:
                infra_output = InfrastructureOutputEnum.CONSISTENT
                result = ChecklistResultEnum.VERIFIED
                details = f"Infrastructure norm satisfied: {actual_val} >= {norm_val}."
            elif ratio >= 0.8:
                infra_output = InfrastructureOutputEnum.NEEDS_ADDITIONAL_EVIDENCE
                result = ChecklistResultEnum.NEEDS_EVIDENCE
                details = f"Infrastructure within 80-100% of norm ({actual_val}/{norm_val}); needs additional evidence."
            else:
                infra_output = InfrastructureOutputEnum.RECOMMEND_INSPECTION
                result = ChecklistResultEnum.INCONSISTENT
                details = f"Infrastructure shortfall ({actual_val} < 80% of {norm_val}); recommend physical inspection."
            inputs["infrastructure_output"] = infra_output.value
        else:
            req_labs = float(item.get("declared_min_labs", 1))
            declared_labs = float(_get_nested(form_data, "laboratories_count") or 0)
            floor_plan_labs = _get_nested(extracted_fields, "floor_plan.laboratories_count")
            inputs["required_labs"] = req_labs
            inputs["declared_labs"] = declared_labs
            inputs["floor_plan_labs"] = floor_plan_labs

            if floor_plan_labs is None:
                infra_output = InfrastructureOutputEnum.NEEDS_ADDITIONAL_EVIDENCE
                result = ChecklistResultEnum.NEEDS_EVIDENCE
                details = "Spatial architectural layout analysis incomplete; needs additional photographic or surveyor evidence."
            elif float(floor_plan_labs) < req_labs or float(floor_plan_labs) < declared_labs:
                infra_output = InfrastructureOutputEnum.RECOMMEND_INSPECTION
                result = ChecklistResultEnum.INCONSISTENT
                details = f"Spatial shortfall detected: verified {floor_plan_labs} labs vs declared {declared_labs}. Human inspection recommended."
            else:
                infra_output = InfrastructureOutputEnum.CONSISTENT
                result = ChecklistResultEnum.VERIFIED
                details = f"Infrastructure verified: {floor_plan_labs} physical laboratory spaces consistent with APH norms."
            inputs["infrastructure_output"] = infra_output.value

    # Build plain language message
    message = details
    if msg_template:
        try:
            rendered = msg_template.format(**inputs)
            message = f"{rendered} ({details})"
        except Exception:
            pass

    ret_val = {
        "rule_id": item_id,
        "rule_version": pack_version,
        "clause_ref": clause_ref,
        "severity": severity,
        "result": result.value if hasattr(result, "value") else str(result),
        "inputs": inputs,
        "message": message,
    }
    if infra_output is not None:
        ret_val["infrastructure_output"] = infra_output.value if hasattr(infra_output, "value") else str(infra_output)
    return ret_val


def evaluate(pack: Dict[str, Any], case_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pure, deterministic statutory rule evaluator.
    Returns checklist results with rule_id, rule_version, result, inputs, and plain-language message.
    """
    pack_version = pack.get("version", "v1")
    items = pack.get("items", [])
    results = []

    for item in items:
        res = evaluate_item(item, case_context, pack_version)
        results.append(res)

    return results
