#!/usr/bin/env python3
"""
Fixora Synthetic Dataset Generator
Deterministic generator for AICTE Extension of Approval (EoA) prototype.
Generates:
- 6 Institutions with RefRecords
- 40 Applications (including 5 named demo archetypes)
- 6 to 9 documents per application (PDF/PNG with QR, EXIF, and SYNTHETIC footer)
- data/synthetic/ground_truth.json defect injection catalog
"""

import os
import sys
import json
import zlib
import struct
import random
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Check for ReportLab, Pillow, and qrcode
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    from PIL.PngImagePlugin import PngInfo
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


RANDOM_SEED = 42

# 6 Demo Institutions
INSTITUTIONS = [
    {
        "id": "1-33276541",
        "name": "Government Engineering College, Pune",
        "address": "Wellesley Road, Shivajinagar",
        "state": "Maharashtra",
        "district": "Pune",
        "pin_code": "411005",
        "contact_email": "principal@gecpune.edu.in",
        "contact_phone": "+91 20 25507000",
        "category": "ENGINEERING_AND_TECHNOLOGY",
        "faculty_count": 56,
        "land_acres": 15.2,
        "built_up_sqm": 24500.0,
        "programmes": [
            {"name": "Computer Engineering", "intake": 120, "level": "UG"},
            {"name": "Mechanical Engineering", "intake": 120, "level": "UG"},
            {"name": "Civil Engineering", "intake": 60, "level": "UG"},
        ],
    },
    {
        "id": "1-44589210",
        "name": "Maharashtra Institute of Technology, Mumbai",
        "address": "Bandra Kurla Complex, Bandra East",
        "state": "Maharashtra",
        "district": "Mumbai",
        "pin_code": "400051",
        "contact_email": "director@mitmumbai.edu.in",
        "contact_phone": "+91 22 26508000",
        "category": "MANAGEMENT",
        "faculty_count": 28,
        "land_acres": 4.5,
        "built_up_sqm": 12800.0,
        "programmes": [
            {"name": "Master of Business Administration", "intake": 180, "level": "PG"},
            {"name": "Finance and Banking Management", "intake": 60, "level": "PG"},
        ],
    },
    {
        "id": "1-55691023",
        "name": "Karnataka Institute of Technology & Management, Bengaluru",
        "address": "Outer Ring Road, Marathahalli",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "pin_code": "560037",
        "contact_email": "principal@kitmblr.edu.in",
        "contact_phone": "+91 80 28456000",
        "category": "ENGINEERING_AND_TECHNOLOGY",
        "faculty_count": 48,
        "land_acres": 10.5,
        "built_up_sqm": 19200.0,
        "programmes": [
            {"name": "Computer Engineering", "intake": 120, "level": "UG"},
            {"name": "Electronics & Communication", "intake": 120, "level": "UG"},
            {"name": "Information Technology", "intake": 60, "level": "UG"},
        ],
    },
    {
        "id": "1-66782345",
        "name": "National College of Pharmacy, Hyderabad",
        "address": "Genome Valley, Shamirpet",
        "state": "Telangana",
        "district": "Medchal-Malkajgiri",
        "pin_code": "500078",
        "contact_email": "director@ncphyderabad.edu.in",
        "contact_phone": "+91 40 23412000",
        "category": "PHARMACY",
        "faculty_count": 32,
        "land_acres": 6.0,
        "built_up_sqm": 9500.0,
        "programmes": [
            {"name": "Bachelor of Pharmacy", "intake": 100, "level": "UG"},
            {"name": "Master of Pharmacy (Pharmaceutics)", "intake": 18, "level": "PG"},
        ],
    },
    {
        "id": "1-77893456",
        "name": "Delhi Academy of Architecture and Planning, New Delhi",
        "address": "Institutional Area, Lodhi Estate",
        "state": "Delhi",
        "district": "New Delhi",
        "pin_code": "110003",
        "contact_email": "dean@daapdelhi.edu.in",
        "contact_phone": "+91 11 24619000",
        "category": "ARCHITECTURE_AND_PLANNING",
        "faculty_count": 22,
        "land_acres": 3.8,
        "built_up_sqm": 8200.0,
        "programmes": [
            {"name": "Bachelor of Architecture", "intake": 80, "level": "UG"},
            {"name": "Master of Urban Planning", "intake": 20, "level": "PG"},
        ],
    },
    {
        "id": "1-88904567",
        "name": "Tamil Nadu Institute of Hotel Management, Chennai",
        "address": "East Coast Road, Thiruvanmiyur",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "pin_code": "600041",
        "contact_email": "principal@tnihmchennai.edu.in",
        "contact_phone": "+91 44 24415000",
        "category": "HOTEL_MANAGEMENT_AND_CATERING",
        "faculty_count": 24,
        "land_acres": 4.2,
        "built_up_sqm": 7800.0,
        "programmes": [
            {"name": "Hotel Management & Catering Technology", "intake": 120, "level": "UG"},
        ],
    },
]


def create_minimal_pdf_fallback(title: str, lines: List[str], footer: str = "SYNTHETIC - AICTE PROTOTYPE ONLY") -> bytes:
    """Creates a valid, syntactically conforming PDF 1.4 binary without external dependencies."""
    content_stream = []
    content_stream.append("BT")
    content_stream.append("/F1 16 Tf")
    content_stream.append("50 780 Td")
    clean_title = title.replace("(", "\\(").replace(")", "\\)")
    content_stream.append(f"({clean_title}) Tj")

    content_stream.append("/F1 11 Tf")
    content_stream.append("0 -30 Td")

    for line in lines[:30]:
        clean_line = line.replace("(", "\\(").replace(")", "\\)")
        content_stream.append(f"({clean_line}) Tj")
        content_stream.append("0 -18 Td")

    content_stream.append("/F1 9 Tf")
    content_stream.append("50 40 Td")
    clean_footer = footer.replace("(", "\\(").replace(")", "\\)")
    content_stream.append(f"({clean_footer}) Tj")
    content_stream.append("ET")

    stream_data = "\n".join(content_stream).encode("latin1")
    stream_len = len(stream_data)

    objs = []
    objs.append(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    
    # 1: Catalog
    objs.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    # 2: Pages
    objs.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    # 3: Page
    objs.append(
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 595 842] /Contents 5 0 R >>\nendobj\n"
    )
    # 4: Font
    objs.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    # 5: Contents
    objs.append(
        f"5 0 obj\n<< /Length {stream_len} >>\nstream\n".encode("latin1")
        + stream_data
        + b"\nendstream\nendobj\n"
    )

    body = b"".join(objs)
    # Calculate xref
    xref_offset = len(body)
    offsets = [0]
    curr = len(objs[0])
    offsets.append(curr)  # obj 1
    curr += len(objs[1])
    offsets.append(curr)  # obj 2
    curr += len(objs[2])
    offsets.append(curr)  # obj 3
    curr += len(objs[3])
    offsets.append(curr)  # obj 4
    curr += len(objs[4])
    offsets.append(curr)  # obj 5

    xref = ["xref\n0 6\n0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref.append(f"{off:010d} 00000 n \n")
    xref_str = "".join(xref)

    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    )

    return body + xref_str.encode("latin1") + trailer.encode("latin1")


def create_pdf_reportlab(title: str, lines: List[str], footer: str = "SYNTHETIC - AICTE PROTOTYPE ONLY", qr_image_path: str = None) -> bytes:
    """Creates a high quality styled PDF using ReportLab."""
    import io
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    # Header Border
    c.setStrokeColor(colors.HexColor("#1A365D"))
    c.setLineWidth(2)
    c.rect(30, 30, width - 60, height - 60)

    # Top banner
    c.setFillColor(colors.HexColor("#1A365D"))
    c.rect(32, height - 90, width - 64, 58, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2.0, height - 60, title.upper())

    # Content
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    y = height - 120
    for line in lines:
        if line.startswith("---"):
            c.setStrokeColor(colors.HexColor("#CBD5E1"))
            c.setLineWidth(1)
            c.line(45, y, width - 45, y)
            y -= 15
        elif line.startswith("[STRONG]"):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(45, y, line.replace("[STRONG]", "").strip())
            c.setFont("Helvetica", 10)
            y -= 18
        else:
            c.drawString(45, y, line)
            y -= 18

    # QR Code embedding if provided
    if qr_image_path and os.path.exists(qr_image_path):
        c.drawImage(qr_image_path, width - 140, 60, width=80, height=80)

    # Footer
    c.setFillColor(colors.HexColor("#DC2626"))
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(width / 2.0, 45, footer)

    c.save()
    buf.seek(0)
    return buf.read()


def generate_pdf(title: str, lines: List[str], footer: str = "SYNTHETIC - AICTE PROTOTYPE ONLY", qr_image_path: str = None) -> bytes:
    if HAS_REPORTLAB:
        return create_pdf_reportlab(title, lines, footer, qr_image_path)
    return create_minimal_pdf_fallback(title, lines, footer)


def create_minimal_png_fallback(width: int = 600, height: int = 400, text_lines: List[str] = None, comment: str = "SYNTHETIC - AICTE PROTOTYPE ONLY") -> bytes:
    """Generates a valid minimal PNG binary with raw zlib and simulated EXIF tEXt chunks."""
    raw_rows = []
    for y in range(height):
        row = bytearray([0])  # filter byte
        for x in range(width):
            # Soft grey grid
            if x % 50 == 0 or y % 50 == 0:
                row.extend([180, 180, 200])
            else:
                row.extend([240, 243, 246])
        raw_rows.append(bytes(row))
    raw_data = b"".join(raw_rows)
    compressed = zlib.compress(raw_data)

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    png_header = b"\x89PNG\r\n\x1a\n"
    ihdr = png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    text_chunk = png_chunk(b"tEXt", b"Comment\x00" + comment.encode("latin1"))
    exif_chunk = png_chunk(b"tEXt", b"EXIF\x00Make: SyntheticAI Model: Canon EOS 90D ISO: 100")
    idat = png_chunk(b"IDAT", compressed)
    iend = png_chunk(b"IEND", b"")

    return png_header + ihdr + text_chunk + exif_chunk + idat + iend


def create_png_pillow(width: int = 800, height: int = 600, kind: str = "floor_plan", text_lines: List[str] = None, footer: str = "SYNTHETIC - AICTE PROTOTYPE ONLY", blur: bool = False) -> bytes:
    """Generates PNG with floor plan drawings or mock photo using Pillow."""
    import io
    img = Image.new("RGB", (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    if kind == "floor_plan":
        # Draw rooms and labs
        rooms = [
            ("Computer Lab 1 (120 sqm)", (50, 50, 350, 200), (224, 231, 255)),
            ("Computer Lab 2 (120 sqm)", (370, 50, 670, 200), (224, 231, 255)),
            ("Electronics Lab (100 sqm)", (50, 220, 350, 370), (254, 243, 199)),
            ("Mechanical Workshop (200 sqm)", (370, 220, 750, 370), (254, 226, 226)),
            ("Classroom A (80 sqm)", (50, 390, 250, 510), (209, 250, 229)),
            ("Classroom B (80 sqm)", (270, 390, 470, 510), (209, 250, 229)),
            ("Library & Reading Room (300 sqm)", (490, 390, 750, 510), (243, 232, 255)),
        ]
        for name, bbox, col in rooms:
            draw.rectangle(bbox, fill=col, outline=(71, 85, 105), width=2)
            draw.text((bbox[0] + 10, bbox[1] + 10), name, fill=(15, 23, 42))
    else:
        # Mock campus/lab photo
        draw.rectangle((40, 40, width - 40, height - 80), fill=(219, 234, 254), outline=(30, 64, 175), width=3)
        draw.text((width // 4, height // 3), f"[INSTITUTION INFRASTRUCTURE FACILITY]\n{text_lines[0] if text_lines else ''}", fill=(30, 58, 138))

    # Add Footer
    draw.rectangle((0, height - 35, width, height), fill=(254, 242, 242))
    draw.text((width // 3, height - 25), footer, fill=(185, 28, 28))

    if blur:
        img = img.filter(ImageFilter.GaussianBlur(radius=4))

    # Add EXIF / PNG Info
    pnginfo = PngInfo()
    pnginfo.add_text("Notice", footer)
    pnginfo.add_text("Device", "Nikon D850 Synthetic")
    pnginfo.add_text("Timestamp", datetime.now(timezone.utc).isoformat())

    buf = io.BytesIO()
    img.save(buf, format="PNG", pnginfo=pnginfo)
    buf.seek(0)
    return buf.read()


def generate_png(width: int = 800, height: int = 600, kind: str = "floor_plan", text_lines: List[str] = None, footer: str = "SYNTHETIC - AICTE PROTOTYPE ONLY", blur: bool = False) -> bytes:
    if HAS_PILLOW:
        return create_png_pillow(width, height, kind, text_lines, footer, blur)
    return create_minimal_png_fallback(width, height, text_lines, footer)


def generate_qr_code(payload: str, output_path: str) -> None:
    if HAS_QRCODE:
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(output_path)


def generate_synthetic_dataset(output_dir: Path, seed: int = RANDOM_SEED) -> Dict[str, Any]:
    """
    Main generator producing 6 institutions, 40 applications, document files,
    and ground_truth.json defect injection catalog.
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = output_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    ground_truth = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "total_institutions": len(INSTITUTIONS),
        "total_applications": 40,
        "archetypes": [
            "APP-EOA-DEMO-001-CLEAN",
            "APP-EOA-DEMO-002-MISSING-EXPIRED",
            "APP-EOA-DEMO-003-MISMATCH",
            "APP-EOA-DEMO-004-ALTERED-DUPLICATE",
            "APP-EOA-DEMO-005-INFRA-SHORTFALL",
        ],
        "applications": {},
    }

    applications_data = []

    # Prepare the 5 named demo archetypes
    archetype_configs = [
        {
            "id": "APP-EOA-DEMO-001-CLEAN",
            "institution_idx": 0,
            "category": "ENGINEERING_AND_TECHNOLOGY",
            "defects": [],
            "notes": "Reference clean application with complete, valid documents conforming to all norms.",
        },
        {
            "id": "APP-EOA-DEMO-002-MISSING-EXPIRED",
            "institution_idx": 1,
            "category": "MANAGEMENT",
            "defects": [
                {
                    "type": "missing",
                    "document_class": "building_occupancy_certificate",
                    "severity": "review_required",
                    "description": "Statutory Building / Occupancy Certificate is missing.",
                },
                {
                    "type": "expired",
                    "document_class": "fire_safety_certificate",
                    "severity": "review_required",
                    "description": "Fire Safety Certificate expired on 2023-11-30.",
                },
            ],
            "notes": "Missing occupancy certificate and expired fire safety certificate.",
        },
        {
            "id": "APP-EOA-DEMO-003-MISMATCH",
            "institution_idx": 2,
            "category": "ENGINEERING_AND_TECHNOLOGY",
            "defects": [
                {
                    "type": "record_mismatch",
                    "document_class": "form_data",
                    "severity": "review_required",
                    "description": "Applied intake (360) exceeds statutory previous approved intake (120) by >10% without prior council sanction.",
                },
                {
                    "type": "inconsistent",
                    "document_class": "land_title_deed",
                    "severity": "needs_attention",
                    "description": "Swapped institution name: Land Deed title references 'St. Peters Technical College'.",
                },
            ],
            "notes": "Intake mismatch vs AICTE records and institution name inconsistency.",
        },
        {
            "id": "APP-EOA-DEMO-004-ALTERED-DUPLICATE",
            "institution_idx": 3,
            "category": "PHARMACY",
            "defects": [
                {
                    "type": "possible_anomaly",
                    "document_class": "accreditation_certificate",
                    "severity": "review_required",
                    "label": "Preliminary indicator - human verification required",
                    "description": "Altered expiry date on certificate: text displays 2027 while digital QR code verifies expiry as 2022.",
                },
                {
                    "type": "duplicate",
                    "document_class": "infrastructure_photo_1",
                    "severity": "needs_attention",
                    "label": "Preliminary indicator - human verification required",
                    "description": "Infrastructure photograph perceptual hash matches previously submitted photograph from GEC Pune.",
                },
            ],
            "notes": "Pixel/QR date discrepancy and cross-institution reused infrastructure photograph.",
        },
        {
            "id": "APP-EOA-DEMO-005-INFRA-SHORTFALL",
            "institution_idx": 4,
            "category": "ARCHITECTURE_AND_PLANNING",
            "defects": [
                {
                    "type": "infrastructure",
                    "document_class": "floor_plan",
                    "severity": "review_required",
                    "infrastructure_output": "recommend_inspection",
                    "description": "Studio/Laboratory shortfall: Floor plan shows only 2 studios vs AICTE norm of 6 studios for 80 intake.",
                },
                {
                    "type": "infrastructure",
                    "document_class": "form_data",
                    "severity": "needs_attention",
                    "infrastructure_output": "needs_additional_evidence",
                    "description": "Built-up area (4,200 sqm) does not meet the prescribed norm of 6,000 sqm for applied programmes.",
                },
            ],
            "notes": "Floor plan studio deficiency and carpet area shortfall.",
        },
    ]

    # Build 35 additional applications
    for i in range(1, 36):
        app_id = f"APP-EOA-2024-{i:05d}"
        inst_idx = i % len(INSTITUTIONS)
        inst = INSTITUTIONS[inst_idx]

        # Inject defects in some standard applications (~35% defect rate)
        defects = []
        if i % 7 == 0:
            defects.append({
                "type": "blurred_or_cropped_scan",
                "document_class": "ter_payment_receipt",
                "severity": "needs_attention",
                "description": "Uploaded TER Payment receipt is blurred and partially cropped.",
            })
        elif i % 5 == 0:
            defects.append({
                "type": "expired",
                "document_class": "affidavit",
                "severity": "needs_attention",
                "description": "Notarized affidavit stamp date is older than 180 days.",
            })
        elif i % 11 == 0:
            defects.append({
                "type": "qr_payload_mismatch",
                "document_class": "accreditation_certificate",
                "severity": "review_required",
                "description": "QR Code payload verification returned URL not matching official NBA portal.",
            })

        archetype_configs.append({
            "id": app_id,
            "institution_idx": inst_idx,
            "category": inst["category"],
            "defects": defects,
            "notes": "Standard batch application" if not defects else "Application with minor defect injection",
        })

    # Keep a reference copy of photo 1 for the duplicate defect in DEMO-004
    canonical_photo_bytes = None

    for config in archetype_configs:
        app_id = config["id"]
        inst = INSTITUTIONS[config["institution_idx"]]
        defects = config["defects"]

        ground_truth["applications"][app_id] = {
            "institution_id": inst["id"],
            "institution_name": inst["name"],
            "category": config["category"],
            "academic_year": "2024-2025",
            "defects": defects,
            "notes": config["notes"],
        }

        # App folder in documents
        app_docs_dir = docs_dir / app_id
        app_docs_dir.mkdir(parents=True, exist_ok=True)

        defect_classes = {d.get("document_class") for d in defects}
        doc_metadata_list = []

        # 1. Affidavit
        is_affidavit_expired = any(d.get("type") == "expired" and d.get("document_class") == "affidavit" for d in defects)
        affidavit_date = (datetime.now(timezone.utc) - timedelta(days=250 if is_affidavit_expired else 15)).strftime("%d-%B-%Y")
        affidavit_text = [
            f"[STRONG]BEFORE THE EXECUTIVE COMMITTEE, AICTE NEW DELHI",
            f"AFFIDAVIT FOR EXTENSION OF APPROVAL (EOA) 2024-2025",
            "---",
            f"Institution: {inst['name']}",
            f"AICTE Permanent ID: {inst['id']}",
            f"Address: {inst['address']}, {inst['district']}, {inst['state']} - {inst['pin_code']}",
            f"Execution Date: {affidavit_date}",
            "We solemnly affirm and state that the institute complies with all AICTE Approval Process Handbook norms.",
            "All submitted documents and certificates are genuine and true copies of original records.",
        ]
        aff_bytes = generate_pdf("SWORN AFFIDAVIT - AICTE COMPLIANCE", affidavit_text)
        aff_file = app_docs_dir / "affidavit.pdf"
        aff_file.write_bytes(aff_bytes)
        doc_metadata_list.append({
            "class_name": "affidavit",
            "file_name": "affidavit.pdf",
            "path": str(aff_file),
            "sha256": hashlib.sha256(aff_bytes).hexdigest(),
            "page_count": 1,
        })

        # 2. Fire Safety Certificate
        is_fire_expired = any(d.get("type") == "expired" and d.get("document_class") == "fire_safety_certificate" for d in defects)
        fire_valid_until = (datetime.now(timezone.utc) - timedelta(days=120 if is_fire_expired else -300)).strftime("%d-%B-%Y")
        fire_text = [
            f"[STRONG]GOVERNMENT FIRE SERVICES DEPARTMENT - NO OBJECTION CERTIFICATE",
            "---",
            f"Issued to: {inst['name']}",
            f"Address: {inst['address']}",
            f"Inspection Clearance No: FIRE/NOC/{inst['id']}/2023",
            f"Valid Until: {fire_valid_until}",
            f"Status: {'EXPIRED' if is_fire_expired else 'VALID AND IN FORCE'}",
            "Certified that adequate fire fighting arrangements have been made as per National Building Code norms.",
        ]
        fire_bytes = generate_pdf("FIRE SAFETY COMPLIANCE CERTIFICATE", fire_text)
        fire_file = app_docs_dir / "fire_safety_certificate.pdf"
        fire_file.write_bytes(fire_bytes)
        doc_metadata_list.append({
            "class_name": "fire_safety_certificate",
            "file_name": "fire_safety_certificate.pdf",
            "path": str(fire_file),
            "sha256": hashlib.sha256(fire_bytes).hexdigest(),
            "page_count": 1,
        })

        # 3. Building Occupancy Certificate (Omit if missing defect)
        if "building_occupancy_certificate" not in defect_classes:
            occ_text = [
                f"[STRONG]MUNICIPAL CORPORATION / COMPETENT AUTHORITY",
                "BUILDING COMPLETION AND OCCUPANCY CERTIFICATE",
                "---",
                f"Applicant: {inst['name']}",
                f"Total Built-up Area Approved: {inst['built_up_sqm']} sq. meters",
                f"Number of Blocks: 4 Blocks (Institutional + Laboratories)",
                f"Certificate No: OCC/MC/{inst['id']}/REV-A",
                "Certified fit for academic occupancy in accordance with sanctioned master plan.",
            ]
            occ_bytes = generate_pdf("BUILDING OCCUPANCY CERTIFICATE", occ_text)
            occ_file = app_docs_dir / "building_occupancy_certificate.pdf"
            occ_file.write_bytes(occ_bytes)
            doc_metadata_list.append({
                "class_name": "building_occupancy_certificate",
                "file_name": "building_occupancy_certificate.pdf",
                "path": str(occ_file),
                "sha256": hashlib.sha256(occ_bytes).hexdigest(),
                "page_count": 1,
            })

        # 4. Accreditation Certificate (with QR code)
        is_altered = any(d.get("type") == "possible_anomaly" and d.get("document_class") == "accreditation_certificate" for d in defects)
        is_qr_mismatch = any(d.get("type") == "qr_payload_mismatch" for d in defects)
        
        qr_file_path = str(app_docs_dir / "qr_acc.png")
        if is_altered:
            qr_payload = f"https://verify.nba-india.org/cert?id={inst['id']}&valid_until=2022-06-30"
            displayed_valid_until = "30-June-2027 (ALTERED)"
        elif is_qr_mismatch:
            qr_payload = f"https://unauthorized-mirror.info/verify?id={inst['id']}"
            displayed_valid_until = "30-June-2026"
        else:
            qr_payload = f"https://verify.nba-india.org/cert?id={inst['id']}&valid_until=2026-06-30"
            displayed_valid_until = "30-June-2026"

        generate_qr_code(qr_payload, qr_file_path)

        acc_text = [
            f"[STRONG]NATIONAL BOARD OF ACCREDITATION (NBA)",
            "CERTIFICATE OF ACCREDITATION",
            "---",
            f"Institution: {inst['name']}",
            f"Accredited Programmes: {inst['programmes'][0]['name']}",
            f"Valid Until: {displayed_valid_until}",
            f"Digital Verification Token: {hashlib.sha256(qr_payload.encode()).hexdigest()[:16]}",
            "Scan QR code for real-time statutory registry verification.",
        ]
        acc_bytes = generate_pdf("NBA ACCREDITATION CERTIFICATE", acc_text, qr_image_path=qr_file_path if os.path.exists(qr_file_path) else None)
        acc_file = app_docs_dir / "accreditation_certificate.pdf"
        acc_file.write_bytes(acc_bytes)
        doc_metadata_list.append({
            "class_name": "accreditation_certificate",
            "file_name": "accreditation_certificate.pdf",
            "path": str(acc_file),
            "sha256": hashlib.sha256(acc_bytes).hexdigest(),
            "page_count": 1,
        })

        # 5. TER Payment Receipt
        is_ter_blurred = any(d.get("type") == "blurred_or_cropped_scan" for d in defects)
        ter_text = [
            f"[STRONG]AICTE CENTRAL FEE PORTAL (TER)",
            "TER PROCESSING CHARGES E-RECEIPT",
            "---",
            f"Institution Name: {inst['name']}",
            f"Transaction ID: TER-2024-TXN-{inst['id'][-5:]}",
            f"Amount Paid: INR 2,00,000/- (Two Lakhs Only)",
            f"Payment Mode: NEFT/RTGS State Bank of India",
            f"Status: SUCCESS",
            f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]
        ter_bytes = generate_pdf("TER PAYMENT RECEIPT", ter_text)
        ter_file = app_docs_dir / "ter_payment_receipt.pdf"
        ter_file.write_bytes(ter_bytes)
        doc_metadata_list.append({
            "class_name": "ter_payment_receipt",
            "file_name": "ter_payment_receipt.pdf",
            "path": str(ter_file),
            "sha256": hashlib.sha256(ter_bytes).hexdigest(),
            "page_count": 1,
        })

        # 6. Land Title Deed
        is_name_swapped = any("swapped" in d.get("description", "").lower() for d in defects)
        land_inst_name = "St. Peters Technical College" if is_name_swapped else inst["name"]
        land_text = [
            f"[STRONG]REVENUE AND REGISTRATION DEPARTMENT",
            "REGISTERED LAND TITLE DEED / LEASE DEED",
            "---",
            f"Lessee / Owner: {land_inst_name}",
            f"Survey / Khasra No: 142/1B, 142/2A",
            f"Total Contiguous Land: {inst['land_acres']} Acres",
            f"Location: {inst['district']}, {inst['state']}",
            f"Title Classification: Clear and Unencumbered Educational Land",
            "Registered in perpetuity for establishment of technical educational institution.",
        ]
        land_bytes = generate_pdf("LAND TITLE AND REGISTRATION DEED", land_text)
        land_file = app_docs_dir / "land_title_deed.pdf"
        land_file.write_bytes(land_bytes)
        doc_metadata_list.append({
            "class_name": "land_title_deed",
            "file_name": "land_title_deed.pdf",
            "path": str(land_file),
            "sha256": hashlib.sha256(land_bytes).hexdigest(),
            "page_count": 1,
        })

        # 7. Floor Plan (PNG)
        floor_bytes = generate_png(width=800, height=600, kind="floor_plan", text_lines=[inst["name"]])
        floor_file = app_docs_dir / "floor_plan.png"
        floor_file.write_bytes(floor_bytes)
        doc_metadata_list.append({
            "class_name": "floor_plan",
            "file_name": "floor_plan.png",
            "path": str(floor_file),
            "sha256": hashlib.sha256(floor_bytes).hexdigest(),
            "page_count": 1,
        })

        # 8. Infrastructure Photo 1 (PNG)
        is_duplicate = any(d.get("type") == "duplicate" for d in defects)
        if is_duplicate and canonical_photo_bytes is not None:
            photo1_bytes = canonical_photo_bytes
        else:
            photo1_bytes = generate_png(width=800, height=600, kind="photo", text_lines=[f"Facility: Computer Lab - {inst['name']}"])
            if canonical_photo_bytes is None:
                canonical_photo_bytes = photo1_bytes
        
        photo1_file = app_docs_dir / "infrastructure_photo_1.png"
        photo1_file.write_bytes(photo1_bytes)
        doc_metadata_list.append({
            "class_name": "infrastructure_photo_1",
            "file_name": "infrastructure_photo_1.png",
            "path": str(photo1_file),
            "sha256": hashlib.sha256(photo1_bytes).hexdigest(),
            "page_count": 1,
        })

        # 9. Infrastructure Photo 2 (PNG)
        photo2_bytes = generate_png(width=800, height=600, kind="photo", text_lines=[f"Facility: Library Central - {inst['name']}"])
        photo2_file = app_docs_dir / "infrastructure_photo_2.png"
        photo2_file.write_bytes(photo2_bytes)
        doc_metadata_list.append({
            "class_name": "infrastructure_photo_2",
            "file_name": "infrastructure_photo_2.png",
            "path": str(photo2_file),
            "sha256": hashlib.sha256(photo2_bytes).hexdigest(),
            "page_count": 1,
        })

        # Intake calculation for application form_data
        has_intake_mismatch = any(d.get("type") == "record_mismatch" for d in defects)
        applied_programmes = []
        for p in inst["programmes"]:
            prog_intake = p["intake"]
            if has_intake_mismatch and "computer" in p["name"].lower():
                prog_intake = 360  # Defect: inflated intake without prior approval
            applied_programmes.append({"name": p["name"], "intake": prog_intake, "level": p["level"]})

        has_area_shortfall = any("built-up area" in d.get("description", "").lower() for d in defects)
        applied_built_up = 4200.0 if has_area_shortfall else inst["built_up_sqm"]

        applications_data.append({
            "id": app_id,
            "institution_id": inst["id"],
            "category": config["category"],
            "academic_year": "2024-2025",
            "checklist_pack_version": "EOA-CHECKLIST-v1",
            "form_data": {
                "institution_name": inst["name"],
                "contact_phone": inst["contact_phone"],
                "contact_email": inst["contact_email"],
                "land_area_acres": inst["land_acres"],
                "built_up_area_sqm": applied_built_up,
                "faculty_count": inst["faculty_count"],
                "lab_count": 4 if any("shortfall" in d.get("description", "").lower() for d in defects) else 14,
                "ter_transaction_id": f"TER-2024-TXN-{inst['id'][-5:]}",
                "programmes": applied_programmes,
            },
            "documents": doc_metadata_list,
        })

    # Save ground_truth.json
    gt_file = output_dir / "ground_truth.json"
    with open(gt_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    return {
        "institutions": INSTITUTIONS,
        "applications": applications_data,
        "ground_truth_path": str(gt_file),
    }


if __name__ == "__main__":
    out = Path("data/synthetic")
    res = generate_synthetic_dataset(out)
    print(f"Generated synthetic dataset: {len(res['institutions'])} institutions, {len(res['applications'])} applications.")
    print(f"Ground truth saved to: {res['ground_truth_path']}")
