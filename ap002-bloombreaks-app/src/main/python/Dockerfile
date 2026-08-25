FROM python:3.9-slim

# 1. System deps for psycopg2
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/apt*

# 2. Create non-root user
RUN addgroup --system appgroup && adduser --system appuser --ingroup appgroup

# 3. Env vars as build args
ARG FLASK_ENV=production
ENV FLASK_ENV=${FLASK_ENV} \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/src/main/python

#4. Install Python deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

#5. Copy code
COPY . .

# Guard: COPY preserves host file modes and lands files owned by root.
# A 0600 file on the Mac would be unreadable by appuser at import time.
RUN chown -R appuser:appgroup /app && chmod -R u+rwX,go+rX /app

#6. Switch to non-root
USER appuser

#7. Expose & healthcheck
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
   CMD curl -f http://localhost:8000/ping || exit 1

#8. Run under gunicorn (production WSGI server; main.py's app.run stays dev-only)
CMD ["gunicorn", "wsgi:application", \
     "--workers", "3", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
