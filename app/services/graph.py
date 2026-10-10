"""
pdf_compilation.graph
─────────────────────
Microsoft Graph API wrapper for converting DOCX → PDF via OneDrive.

Flow per file:
    1. Acquire a Bearer token using client credentials (cached until expiry).
    2. Upload the DOCX into a dedicated run folder on OneDrive.
    3. Download the same item rendered as PDF (?format=pdf).
    4. Delete the DOCX from OneDrive.
    5. Return the PDF bytes.

Retry behaviour:
    All Graph API calls (upload, convert, delete) are retried with
    exponential backoff on 429 (rate limit) and 5xx (server error) responses.
    The Retry-After header is respected when present.

Usage:
    from pdf_compilation.graph import Graph

    graph = Graph(
        tenant_id="...",
        client_id="...",
        client_secret="...",
        drive_id="...",
    )
    pdf_bytes = graph.convert_to_pdf(filename="order_001.docx", file_bytes=docx_bytes)

Environment variables (alternative to passing args directly):
    MS_GRAPH_TENANT_ID
    MS_GRAPH_CLIENT_ID
    MS_GRAPH_CLIENT_SECRET
    MS_GRAPH_DRIVE_ID
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

import requests

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_LOGIN_BASE = "https://login.microsoftonline.com"

# Statuses that are safe to retry
_RETRYABLE_STATUSES = {400, 429, 500, 502, 503, 504}

F = TypeVar("F", bound=Callable)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GraphAuthError(Exception):
    """Raised when token acquisition fails."""


class GraphUploadError(Exception):
    """Raised when the DOCX upload to OneDrive fails."""


class GraphConvertError(Exception):
    """Raised when the PDF download / conversion fails."""


class GraphDeleteError(Exception):
    """Raised when the DOCX deletion from OneDrive fails."""


class GraphRateLimitError(Exception):
    """Raised when all retries are exhausted due to rate limiting."""


# ---------------------------------------------------------------------------
# Retry helper
# ---------------------------------------------------------------------------


def _with_retry(
    fn: Callable[[], requests.Response],
    label: str,
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 32.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> requests.Response:
    """
    Call *fn* and retry on retryable HTTP status codes.

    Back-off strategy:
        - If the response contains a Retry-After header, sleep that many seconds.
        - Otherwise, use exponential back-off: base_delay * 2^attempt, capped at max_delay.

    Parameters
    ----------
    fn:
        Zero-argument callable that returns a requests.Response.
    label:
        Human-readable description used in log messages.
    max_retries:
        Maximum number of retries (total attempts = max_retries + 1).
    base_delay:
        Initial back-off delay in seconds.
    max_delay:
        Maximum back-off delay in seconds.
    sleep_fn:
        Function to call for sleeping (defaults to time.sleep).
    """
    attempt = 0
    while True:
        resp = fn()

        if resp.status_code not in _RETRYABLE_STATUSES:
            return resp  # success or a non-retryable error — return as-is

        if attempt >= max_retries:
            raise GraphRateLimitError(
                f"{label} failed after {max_retries + 1} attempts "
                f"[{resp.status_code}]: {resp.text}",
            )

        # Respect Retry-After if present, otherwise exponential back-off
        retry_after = resp.headers.get("Retry-After")
        if retry_after is not None:
            try:
                # Handle localized floats like "9,9"
                delay = float(retry_after.replace(",", "."))
            except ValueError:
                delay = min(base_delay * 2**attempt, max_delay)
        else:
            delay = min(base_delay * 2**attempt, max_delay)

        logger.warning(
            "%s got %s (attempt %d/%d) — retrying in %.1fs",
            label,
            resp.status_code,
            attempt + 1,
            max_retries + 1,
            delay,
        )
        sleep_fn(delay)
        attempt += 1


# ---------------------------------------------------------------------------
# Graph client
# ---------------------------------------------------------------------------


class Graph:
    """
    Thin wrapper around Microsoft Graph for DOCX → PDF conversion.

    Parameters
    ----------
    tenant_id, client_id, client_secret:
        Azure AD app registration credentials (client credentials flow).
    drive_id:
        The OneDrive drive ID to use as scratch space.
        Find it via: GET https://graph.microsoft.com/v1.0/me/drive
    upload_folder:
        Root folder inside the drive where run sub-folders are created.
        Defaults to "dataflow_docx_pipeline_tmp".
    run_id:
        Identifier for this pipeline run — used as sub-folder name so
        concurrent Dataflow workers don't collide. Defaults to a timestamp.
    timeout:
        HTTP request timeout in seconds.
    max_retries:
        Maximum retries per API call on 429 / 5xx responses.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        drive_id: str,
        upload_folder: str = "dataflow_docx_pipeline_tmp",
        run_id: str = "",
        timeout: int = 60,
        max_retries: int = 5,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.drive_id = drive_id
        self.upload_folder = upload_folder
        self.run_id = run_id or str(int(time.time()))
        self.timeout = timeout
        self.max_retries = max_retries
        self.sleep_fn = sleep_fn

        # Token cache
        self._token: str | None = None
        self._token_expiry: float = 0.0

        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert_to_pdf(self, filename: str, file_bytes: bytes) -> bytes:
        """
        Upload *filename* (.docx) to OneDrive, convert to PDF, delete the
        DOCX, and return the PDF bytes.

        Parameters
        ----------
        filename:
            The filename to use on OneDrive, e.g. ``"order_001.docx"``.
        file_bytes:
            Raw bytes of the DOCX file.

        Returns
        -------
        bytes
            Raw bytes of the converted PDF.
        """
        token = self._get_token()

        # Step 1 — upload DOCX
        item_id = self._upload_docx(token, filename, file_bytes)
        logger.info("Uploaded  %s → OneDrive item %s", filename, item_id)

        # Step 2 — download as PDF
        pdf_bytes = self._download_as_pdf(token, item_id)
        logger.info("Converted %s → PDF (%d bytes)", filename, len(pdf_bytes))

        # Step 3 — delete DOCX from OneDrive (best-effort, never blocks the PDF)
        try:
            self._delete_item(token, item_id)
            logger.info("Deleted   %s from OneDrive", filename)
        except Exception as exc:  # pylint: disable=broad-except
            # Deletion failure is not fatal — log and move on
            logger.warning("Could not delete %s (item %s): %s", filename, item_id, exc)

        return pdf_bytes

    # ------------------------------------------------------------------
    # Token (client credentials, cached until expiry)
    # ------------------------------------------------------------------

    def verify_credentials(self) -> None:
        """Verifies credentials by attempting to acquire a token immediately."""
        self._get_token()

    def _get_token(self) -> str:
        """Return a valid Bearer token, refreshing if within 30s of expiry."""
        if self._token and time.time() < self._token_expiry - 30:
            return self._token

        url = f"{_LOGIN_BASE}/{self.tenant_id}/oauth2/v2.0/token"
        # Token endpoint does not return 429s in practice, but wrap anyway
        resp = _with_retry(
            lambda: self._session.post(
                url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                },
                timeout=self.timeout,
            ),
            label="token",
            max_retries=self.max_retries,
            sleep_fn=self.sleep_fn,
        )

        if not resp.ok:
            raise GraphAuthError(
                f"Token request failed [{resp.status_code}]: {resp.text}",
            )

        data = resp.json()
        self._token = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 3600))
        logger.debug(
            "Acquired new Graph token (expires in %ss)",
            data.get("expires_in"),
        )
        return self._token

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def _upload_docx(self, token: str, filename: str, file_bytes: bytes) -> str:
        """
        Upload *file_bytes* to:
            {upload_folder}/{run_id}/{filename}

        Returns the OneDrive item ID.
        """
        onedrive_path = f"{self.upload_folder}/{self.run_id}/{filename}"
        url = f"{_GRAPH_BASE}/drives/{self.drive_id}/root:/{onedrive_path}:/content"

        resp = _with_retry(
            lambda: self._session.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": (
                        "application/vnd.openxmlformats-officedocument"
                        ".wordprocessingml.document"
                    ),
                },
                data=file_bytes,
                timeout=self.timeout,
            ),
            label=f"upload:{filename}",
            max_retries=self.max_retries,
            sleep_fn=self.sleep_fn,
        )

        if not resp.ok:
            raise GraphUploadError(
                f"Upload failed for '{filename}' [{resp.status_code}]: {resp.text}",
            )

        item_id = resp.json().get("id")
        if not item_id:
            raise GraphUploadError(
                f"Upload response missing 'id' for '{filename}': {resp.text}",
            )

        return item_id

    # ------------------------------------------------------------------
    # Convert → PDF
    # ------------------------------------------------------------------

    def _download_as_pdf(self, token: str, item_id: str) -> bytes:
        """
        Download the OneDrive item rendered as PDF.
        Graph converts on-the-fly when ?format=pdf is appended and
        returns a 302 redirect to a pre-signed Azure Blob URL.
        The redirect must be followed WITHOUT the Authorization header.
        """
        url = f"{_GRAPH_BASE}/drives/{self.drive_id}/items/{item_id}/content?format=pdf"

        resp = _with_retry(
            lambda: self._session.get(
                url,
                headers={"Authorization": f"Bearer {token}"},
                allow_redirects=False,  # handle redirect manually (see below)
                timeout=self.timeout,
            ),
            label=f"convert:{item_id}",
            max_retries=self.max_retries,
            sleep_fn=self.sleep_fn,
        )

        # Follow the 302 redirect manually — Azure Blob rejects requests
        # that carry an Authorization header on the pre-signed URL.
        if resp.status_code in (301, 302, 303, 307, 308):
            download_url = resp.headers.get("Location")
            if not download_url:
                raise GraphConvertError(
                    f"PDF redirect missing Location header for item {item_id}",
                )
            # The blob download itself can also be rate-limited
            resp = _with_retry(
                lambda: self._session.get(download_url, timeout=self.timeout),
                label=f"blob_download:{item_id}",
                max_retries=self.max_retries,
                sleep_fn=self.sleep_fn,
            )

        if not resp.ok:
            raise GraphConvertError(
                f"PDF download failed for item {item_id} [{resp.status_code}]: {resp.text}",
            )

        return resp.content

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def _delete_item(self, token: str, item_id: str) -> None:
        """Delete a OneDrive item by ID. Raises GraphDeleteError on failure."""
        url = f"{_GRAPH_BASE}/drives/{self.drive_id}/items/{item_id}"

        resp = _with_retry(
            lambda: self._session.delete(
                url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self.timeout,
            ),
            label=f"delete:{item_id}",
            max_retries=self.max_retries,
            sleep_fn=self.sleep_fn,
        )

        # 204 No Content = success; 404 = already gone, treat as success
        if resp.status_code not in (204, 404):
            raise GraphDeleteError(
                f"Delete failed for item {item_id} [{resp.status_code}]: {resp.text}",
            )