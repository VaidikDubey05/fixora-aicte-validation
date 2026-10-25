"""
Sample AICTE Approval Process Handbook (APH) PDF Generator
Generates a multi-page statutory handbook PDF in data/aph/
structured with chapters, sections, and clear statutory norms.
Works with ReportLab if installed, or pure Python fallback.
"""

import os
from pathlib import Path
from typing import List, Tuple

aph_dir = Path(__file__).resolve().parent
output_pdf_path = aph_dir / "aicte_approval_process_handbook_2024_25.pdf"

HANDBOOK_PAGES = [
    (
        "ALL INDIA COUNCIL FOR TECHNICAL EDUCATION",
        [
            "[STRONG]APPROVAL PROCESS HANDBOOK (2024-25)",
            "Statutory Procedures, Regulations and Norms for Technical Institutions",
            "----------------------------------------------------------------------",
            "[STRONG]Chapter 1: Statutory Basis & Objectives",
            "[STRONG]Section 1.1: Scope and Jurisdiction of the Council",
            "The All India Council for Technical Education (AICTE) was established under the AICTE Act 1987",
            "to ensure planned and coordinated development of technical education across India. Technical",
            "institutions offering Degree and Diploma programmes in Engineering, Technology, Management,",
            "Pharmacy, Architecture, and Applied Arts fall under the statutory jurisdiction of the Council.",
            "",
            "[STRONG]Section 1.2: Annual Extension of Approval (EoA)",
            "Every approved technical institution must obtain an annual Extension of Approval (EoA) prior to",
            "commencing admissions for the academic year. The grant of EoA is strictly contingent upon full",
            "compliance with council norms regarding land, built-up area, faculty cadre ratio, and certificates.",
            "",
            "[STRONG]Section 1.3: Decision Support and Official Review Policy",
            "Automated document validation and digital verification systems operate strictly as decision support.",
            "Preliminary indicators highlight potential discrepancies with evidence. Statutory determinations,",
            "including approvals, deficiency notices, and inspections, are made solely by authorised council officers.",
        ]
    ),
    (
        "APPROVAL PROCESS HANDBOOK (2024-25) - CHAPTER 2",
        [
            "[STRONG]Chapter 2: Grant of Extension of Approval (EoA) & Mandatory Submissions",
            "[STRONG]Section 2.1: Sworn Affidavit Requirements",
            "Institutions must submit a sworn Affidavit duly executed on non-judicial stamp paper of prescribed",
            "denomination. The affidavit must affirm that all declared student intake, land titles, and building",
            "specifications comply truthfully with AICTE regulations without suppression of material facts.",
            "",
            "[STRONG]Section 2.2: Fire Safety Certificate & NOC",
            "A valid, unexpired Fire Safety Certificate issued by the competent State Disaster Management or",
            "Fire Prevention Services Department must be uploaded. A certificate that has expired or is nearing",
            "expiry within 30 days requires an immediate renewal inspection prior to the grant of approval.",
            "",
            "[STRONG]Section 2.3: Building Completion and Occupancy Certificate",
            "Institutions must possess a structural stability and Building Occupancy Certificate issued by the",
            "local Municipal Corporation, Town Planning Authority, or Competent PWD Engineer certifying safety.",
            "",
            "[STRONG]Section 2.4: National Board of Accreditation (NBA) Certificate",
            "Where accredited programmes are declared, institutions must furnish digital accreditation certificates",
            "bearing verifiable QR codes. The QR payload must resolve to official accreditation registries.",
            "",
            "[STRONG]Section 2.5: Land Title Deed & Ownership Documentation",
            "The land on which the institution operates must be registered in the name of the sponsoring Trust,",
            "Society, or Company via a registered Title Deed or permanent registered Government lease.",
            "",
            "[STRONG]Section 2.6: University Affiliation Letter",
            "An annual affiliation confirmation letter from the designated State Technical University must be",
            "uploaded, confirming approved programmes and student intake for the concerned academic session.",
        ]
    ),
    (
        "APPROVAL PROCESS HANDBOOK (2024-25) - CHAPTER 3",
        [
            "[STRONG]Chapter 3: Norms for Land and Spatial Infrastructure",
            "[STRONG]Section 3.1: Minimum Land Requirements for Technical Institutions",
            "For Engineering and Technology institutions, the minimum contiguous land requirement is 2.5 acres",
            "in designated Urban areas (Mega/Metro cities) and 4.0 acres in Rural areas. The land must be free from",
            "any encumbrances and owned or leased on long-term basis for a minimum duration of thirty years.",
            "",
            "[STRONG]Section 3.2: Carpet Area and Built-up Space Norms",
            "The prescribed total built-up carpet area for technical institutions depends on applied student intake.",
            "For applied intake exceeding 120 students, the minimum required built-up area is 4,000 square metres.",
            "Institutions with intake of 120 or fewer students must possess at least 2,500 square metres of area.",
            "",
            "[STRONG]Section 3.3: Laboratory and Workshop Requirements",
            "Institutions must provide minimum one specialised laboratory or practical workshop per thirty technical",
            "intake. Every technical institution must possess a baseline minimum of four fully equipped laboratories.",
            "Blueprints exhibiting a shortfall of more than 50% laboratories trigger an on-site scrutiny inspection.",
            "",
            "[STRONG]Section 3.4: Computer Centre and Digital Library Norms",
            "A dedicated Computer Centre with a terminal-to-student ratio of 1:4 for technical courses is mandatory.",
            "High-speed broadband internet connectivity and subscription to national e-journal consortia are required.",
            "",
            "[STRONG]Section 3.5: Barrier-free Environment and Accessibility",
            "Institutions must provide barrier-free infrastructure including ramps, lifts, and dedicated accessible",
            "washrooms for differently-abled persons in accordance with the Persons with Disabilities Act.",
        ]
    ),
    (
        "APPROVAL PROCESS HANDBOOK (2024-25) - CHAPTER 4 & 5",
        [
            "[STRONG]Chapter 4: Faculty Cadre Ratio, Qualifications and Intake",
            "[STRONG]Section 4.1: Faculty Cadre Ratio",
            "The prescribed faculty-to-student cadre ratio for Undergraduate Degree courses in Engineering and",
            "Technology is 1:20. The cadre structure should ideally follow Professor to Associate Professor to",
            "Assistant Professor ratio of 1:2:6. Institutions failing to maintain minimum 80% faculty face intake reduction.",
            "",
            "[STRONG]Section 4.2: Approved Programmes and Intake Ceilings",
            "Student intake declared on EoA applications must match approved council records. Any unapproved intake",
            "increase exceeding 10% without prior sanction constitutes a statutory deficiency requiring rectification.",
            "",
            "[STRONG]Section 4.3: Principal and Director Qualifications",
            "Every technical institution must have a regular, full-time Principal or Director possessing Ph.D. degree",
            "in an appropriate engineering discipline with minimum fifteen years of teaching or research experience.",
            "----------------------------------------------------------------------",
            "[STRONG]Chapter 5: Technical Education Regulatory (TER) Fee Schedule",
            "[STRONG]Section 5.1: Processing Fee Structure",
            "Institutions applying for Extension of Approval must pay a non-refundable Technical Education Regulatory",
            "(TER) fee. The standard fee for existing institutions is Rs. 1,00,000 to Rs. 3,00,000 depending on intake.",
            "",
            "[STRONG]Section 5.2: TER Fee Payment Verification",
            "TER fee payments must be remitted strictly via the online council payment gateway. Offline or cash payments",
            "are not accepted. A valid transaction reference number with status PAID is mandatory before application review.",
        ]
    ),
    (
        "APPROVAL PROCESS HANDBOOK (2024-25) - CHAPTER 6 & 7",
        [
            "[STRONG]Chapter 6: Verification, Scrutiny and On-site Inspection",
            "[STRONG]Section 6.1: Scrutiny Committee Procedures",
            "The Scrutiny Committee verifies the authenticity of submitted documents, cross-checking declared data",
            "against council databases, university affiliation portals, and state fire safety department registries.",
            "",
            "[STRONG]Section 6.2: External Authority Verification Procedures",
            "Digital checks against external registries verify affiliation and fire certificates. If an external API",
            "times out or is temporarily unavailable, the outage is treated neutrally and routed to manual review.",
            "",
            "[STRONG]Section 6.3: Expert Visit Committee (EVC) Physical Inspection",
            "An on-site inspection by an Expert Visit Committee is recommended when spatial shortfalls, laboratory",
            "deficiencies, or serious document discrepancies cannot be reconciled during digital scrutiny.",
            "----------------------------------------------------------------------",
            "[STRONG]Chapter 7: Rectification, Deficiencies and Appeal Procedures",
            "[STRONG]Section 7.1: Rectification Window and Opportunity to Cure",
            "Where minor deficiencies or expired certificates are identified, institutions are granted a statutory",
            "rectification window of seven to fifteen days to upload replacement documents without penalty.",
            "",
            "[STRONG]Section 7.2: Standing Hearing Committee (SHC) Appeals",
            "Institutions aggrieved by adverse Scrutiny findings or recommendation of intake reduction may appeal",
            "before the Standing Hearing Committee (SHC) with certified documentary evidence.",
            "",
            "[STRONG]Section 7.3: Withdrawal of Approval or Intake Reduction",
            "Persistent failure to rectify mandatory deficiencies regarding land, fire safety, or faculty cadre",
            "ratio may result in placed in No Admission status or reduction of approved intake by 50%.",
        ]
    )
]


def create_handbook_pdf_pure_python(output_path: Path) -> None:
    """Creates a multi-page PDF using pure Python stream generation."""
    objs = []
    # obj 1: Catalog
    # obj 2: Pages
    # obj 3..7: Page objects
    # obj 8..12: Content stream objects
    # obj 13: Font object

    page_count = len(HANDBOOK_PAGES)
    page_obj_nums = [3 + i for i in range(page_count)]
    content_obj_nums = [3 + page_count + i for i in range(page_count)]
    font_obj_num = 3 + 2 * page_count

    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    kids_str = " ".join([f"{num} 0 R" for num in page_obj_nums])
    objs.append(f"2 0 obj\n<< /Type /Pages /Kids [{kids_str}] /Count {page_count} >>\nendobj\n".encode("latin1"))

    # Generate Page objects
    for i, p_num in enumerate(page_obj_nums):
        c_num = content_obj_nums[i]
        objs.append(
            f"{p_num} 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/MediaBox [0 0 595 842] /Contents {c_num} 0 R >>\nendobj\n".encode("latin1")
        )

    # Generate Content streams
    for i, (title, lines) in enumerate(HANDBOOK_PAGES):
        c_num = content_obj_nums[i]
        stream_commands = [
            "BT",
            "/F1 12 Tf",
            "50 800 Td",
            f"({title}) Tj",
            "/F1 9 Tf",
            "0 -22 Td",
        ]
        for line in lines:
            safe_line = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            stream_commands.append(f"({safe_line}) Tj")
            stream_commands.append("0 -16 Td")
        
        # Add footer
        stream_commands.append("/F1 8 Tf")
        stream_commands.append("0 -20 Td")
        stream_commands.append(f"(AICTE APPROVAL PROCESS HANDBOOK - PAGE {i+1} OF {page_count}) Tj")
        stream_commands.append("ET")

        stream_data = "\n".join(stream_commands).encode("latin1")
        stream_len = len(stream_data)
        objs.append(
            f"{c_num} 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
            + stream_data
            + b"\nendstream\nendobj\n"
        )

    # Font object
    objs.append(f"{font_obj_num} 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n".encode("latin1"))

    # Compute xref offsets
    body = b"".join(objs)
    offsets = [0]
    curr = 0
    for obj in objs:
        curr += len(obj)
        offsets.append(curr)

    total_objs = len(objs) + 1
    xref = [f"xref\n0 {total_objs}\n0000000000 65535 f \n"]
    running = 0
    for obj in objs:
        xref.append(f"{running:010d} 00000 n \n")
        running += len(obj)

    xref_offset = len(body)
    trailer = f"trailer\n<< /Size {total_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(body + "".join(xref).encode("latin1") + trailer.encode("latin1"))
    print(f"Sample APH PDF generated successfully: {output_path} ({len(HANDBOOK_PAGES)} pages)")


if __name__ == "__main__":
    create_handbook_pdf_pure_python(output_pdf_path)
