# ============================================================
# Daffo-Botz Dockerfile
# Build context harus berisi:
#   - Dockerfile
#   - Daffo-Botz-Updated.zip
#
# Dockerfile ini akan:
# 1. Memakai Python 3.11
# 2. Menginstal unzip, FFmpeg, libmagic, dan dependency sistem
# 3. Meng-unzip project ke /app/Daffo-Botz
# 4. Membuat virtual environment .venv
# 5. Menginstal seluruh module dari requirements.txt
# 6. Mengaktifkan venv secara permanen melalui PATH
# 7. Menyiapkan .env dari .env.example
# 8. Menjalankan python main.py
# ============================================================

FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="Daffo-Botz"
LABEL org.opencontainers.image.description="WhatsApp Bot Daffo-Botz - Python 3.11"
LABEL org.opencontainers.image.version="1.0"

# Supaya output log langsung tampil dan Python tidak membuat .pyc yang tidak perlu.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# ------------------------------------------------------------
# Install dependency sistem yang dibutuhkan Daffo-Botz
# ------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        unzip \
        ffmpeg \
        libmagic1 \
        file \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------
# Copy ZIP project ke dalam container
# ------------------------------------------------------------
WORKDIR /app

COPY Daffo-Botz-Updated.zip /app/Daffo-Botz-Updated.zip

# ------------------------------------------------------------
# Unzip project, lalu hapus ZIP agar image lebih bersih
# ------------------------------------------------------------
RUN unzip -q /app/Daffo-Botz-Updated.zip -d /app \
    && rm -f /app/Daffo-Botz-Updated.zip \
    && test -f /app/Daffo-Botz/requirements.txt \
    && test -f /app/Daffo-Botz/main.py

# Sama dengan "cd /app/Daffo-Botz" untuk instruction berikutnya.
WORKDIR /app/Daffo-Botz

# ------------------------------------------------------------
# Buat Python virtual environment
# ------------------------------------------------------------
RUN python3 -m venv /app/Daffo-Botz/.venv

# "Aktifkan" virtual environment secara permanen.
# Setelah baris ini, python/pip menunjuk ke .venv.
ENV VIRTUAL_ENV=/app/Daffo-Botz/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# ------------------------------------------------------------
# Upgrade pip lalu install seluruh requirements Daffo-Botz
# ------------------------------------------------------------
RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install -r requirements.txt

# ------------------------------------------------------------
# Siapkan konfigurasi dasar.
# Environment variable yang diberikan saat docker run akan tetap
# meng-override nilai dari file .env karena python-dotenv default
# tidak menimpa environment variable yang sudah tersedia.
# ------------------------------------------------------------
RUN if [ ! -f .env ]; then cp .env.example .env; fi \
    && mkdir -p data downloads

# Konfigurasi default yang dapat di-override dengan `docker run -e ...`
ENV BOT_NAME="Daffo-Botz" \
    PREFIX="." \
    SESSION_DB="data/whatsapp-session.db" \
    APP_DB="data/daffo-botz.db" \
    MAX_DOWNLOAD_MB="90" \
    WELCOME_DEFAULT="true" \
    AUTO_RESPONDER="true" \
    STRIKE_LIMIT="3"

# Session WhatsApp/database dan hasil download sebaiknya persisten.
VOLUME ["/app/Daffo-Botz/data", "/app/Daffo-Botz/downloads"]

# Pemeriksaan sederhana saat proses build.
RUN python --version \
    && python -c "import neonize; print('Neonize: OK')" \
    && python -c "import magic; print('libmagic: OK')" \
    && python -m compileall -q daffobot main.py \
    && echo "Daffo-Botz build check: OK"

# ------------------------------------------------------------
# Menjalankan bot
# ------------------------------------------------------------
CMD ["python", "main.py"]
