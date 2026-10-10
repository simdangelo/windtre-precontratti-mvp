# ============================================================================
# Dockerfile: Production Document Synthesis & API Worker
# Target: Google Cloud Run Deployment
# ============================================================================

# 1. Use a lightweight, official Python runtime as base
FROM python:3.11-slim-bookworm

# 2. Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# 3. Install headless LibreOffice, MS core fonts, and PDF/UA utilities
# LibreOffice and custom fonts are strictly required to ensure correct PDF styling,
# accurate margins, and Tagged PDF/UA accessibility compliance.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-calc \
    fonts-liberation \
    fonts-dejavu \
    fontconfig \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 4. Refresh the OS system font cache
RUN fc-cache -fv

# 5. Set up work directory
WORKDIR /app

# 6. Copy requirements list and install dependencies
# Note: we declare our python dependencies (docx, openpyxl, fastapi, uvicorn, sqlalchemy, pydantic)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copy application source files
# Expected directories: app/ (routers, models, generators) and templates/ (meta-templates)
COPY app/ ./app
COPY templates/ /gcs/templates/
COPY admin_dashboard.html .

# 8. Create non-root system user for secure Cloud Run sandbox execution
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app /tmp
USER appuser

# 9. Expose default Google Cloud Run server port
EXPOSE 8080

# 10. Start high-performance Uvicorn ASGI server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4"]
