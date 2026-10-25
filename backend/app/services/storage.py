import hashlib
import os
import uuid
from typing import Optional, Tuple
try:
    from fastapi import HTTPException, status
except ImportError:
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class _MockStatus:
        HTTP_400_BAD_REQUEST = 400
        HTTP_404_NOT_FOUND = 404
        HTTP_413_REQUEST_ENTITY_TOO_LARGE = 413

    status = _MockStatus()
try:
    from app.core.config import settings
except ImportError:
    class _MockSettings:
        STORAGE_ENCRYPTION_KEY = os.getenv("STORAGE_ENCRYPTION_KEY", "fixora-default-secret-key-32bytes!")
        STORAGE_PATH = os.getenv("STORAGE_PATH", "storage")
        STORAGE_DIR = STORAGE_PATH
    settings = _MockSettings()

# Attempt to use native Fernet from cryptography package; provide robust fallback if cryptography is not installed
try:
    from cryptography.fernet import Fernet
    HAS_FERNET = True
except ImportError:
    HAS_FERNET = False


class IVirusScanner:
    """Interface for anti-malware and file inspection scanners."""

    def scan(self, file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        raise NotImplementedError


class MockVirusScanner(IVirusScanner):
    """Stub statutory virus scanner."""

    def scan(self, file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        # Check for EICAR test string
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in file_bytes:
            return False, "EICAR test malware signature detected"
        return True, "File clean (simulated scanner)"


MAGIC_BYTES = {
    "pdf": [b"%PDF-"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_PAGE_LIMIT = 50


class StorageService:
    """
    Manages document validation, virus scanning, at-rest Fernet encryption,
    and immutable storage under private storage/ directory.
    Real filesystem paths are strictly kept private.
    """

    def __init__(self, scanner: Optional[IVirusScanner] = None):
        self.scanner = scanner or MockVirusScanner()
        self._ensure_storage_dir()
        if HAS_FERNET:
            key = settings.STORAGE_ENCRYPTION_KEY
            if isinstance(key, str):
                key = key.encode("utf-8")
            self._fernet = Fernet(key)
        else:
            self._fernet = None

    def _ensure_storage_dir(self):
        storage_path = settings.STORAGE_PATH
        # If relative or host path
        if not os.path.isabs(storage_path):
            storage_path = os.path.abspath(storage_path)
        os.makedirs(storage_path, exist_ok=True)

    def validate_file(self, filename: str, content: bytes) -> str:
        """
        Validates extension, size, magic bytes, and page count.
        Returns normalized extension.
        """
        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum permissible statutory upload size of 15MB (got {len(content)} bytes).",
            )

        if "." not in filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File has no extension.",
            )

        ext = filename.rsplit(".", 1)[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type '.{ext}'. Allowed types are PDF, PNG, JPG.",
            )

        # Magic byte verification
        expected_magics = MAGIC_BYTES.get(ext, [])
        is_magic_valid = any(content.startswith(magic) for magic in expected_magics)
        if not is_magic_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File magic bytes do not match declared extension '.{ext}'. Possible corrupt or disguised payload.",
            )

        # Approximate page count validation for PDFs
        if ext == "pdf":
            # Count /Type /Page occurrences in PDF stream
            page_count = content.count(b"/Type /Page") - content.count(b"/Type /Pages")
            if page_count > MAX_PAGE_LIMIT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document exceeds maximum statutory limit of {MAX_PAGE_LIMIT} pages (detected ~{page_count}).",
                )

        # Run virus scanner
        clean, detail = self.scanner.scan(content, filename)
        if not clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document failed security inspection: {detail}",
            )

        return ext

    def compute_sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def encrypt_bytes(self, content: bytes) -> bytes:
        if self._fernet:
            return self._fernet.encrypt(content)
        else:
            # Reversible standard obfuscation fallback when cryptography package is not installed on host
            key_bytes = settings.STORAGE_ENCRYPTION_KEY.encode("utf-8")
            return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(content)])

    def decrypt_bytes(self, encrypted_content: bytes) -> bytes:
        if self._fernet:
            return self._fernet.decrypt(encrypted_content)
        else:
            key_bytes = settings.STORAGE_ENCRYPTION_KEY.encode("utf-8")
            return bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_content)])

    def save_encrypted_document(self, content: bytes) -> str:
        """
        Encrypts content and persists under a randomly generated UUID name.
        Returns the random file_ref token (not a full path).
        """
        encrypted = self.encrypt_bytes(content)
        random_token = f"{uuid.uuid4().hex}.enc"
        target_path = os.path.join(settings.STORAGE_PATH, random_token)
        with open(target_path, "wb") as f:
            f.write(encrypted)
        return random_token

    def read_decrypted_document(self, file_ref: str) -> bytes:
        """Reads and decrypts stored file given its file_ref token."""
        # Sanitize file_ref to prevent directory traversal
        clean_ref = os.path.basename(file_ref)
        target_path = os.path.join(settings.STORAGE_PATH, clean_ref)
        if not os.path.exists(target_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encrypted document artifact not found in storage vault.",
            )
        with open(target_path, "rb") as f:
            encrypted_data = f.read()
        return self.decrypt_bytes(encrypted_data)


storage_service = StorageService()


def encrypt_file_bytes(content: bytes) -> bytes:
    """Convenience helper to encrypt raw bytes at rest."""
    return storage_service.encrypt_bytes(content)


def decrypt_file_bytes(encrypted_content: bytes) -> bytes:
    """Convenience helper to decrypt stored bytes."""
    return storage_service.decrypt_bytes(encrypted_content)


class FileValidationResult:
    def __init__(self, is_valid: bool, detected_ext: Optional[str] = None, error_message: Optional[str] = None):
        self.is_valid = is_valid
        self.detected_ext = detected_ext
        self.error_message = error_message


def validate_upload_file(filename: str, content_type: str, content: bytes) -> FileValidationResult:
    """Validates file extension, magic bytes, size limits, and scans for malware."""
    try:
        ext = storage_service.validate_file(filename, content)
        return FileValidationResult(is_valid=True, detected_ext=f".{ext}")
    except Exception as e:
        msg = str(getattr(e, "detail", str(e)))
        return FileValidationResult(is_valid=False, error_message=msg)
