# Build context is the project root (the folder holding src/ and tests/),
# NOT src/main/python. Elastic Beanstalk bundles from the project root and
# looks for the Dockerfile there, so every path below is root-relative.
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

# The app is flattened into /app: the src/main/python nesting is a source-tree
# convention and carries no meaning inside the image.
WORKDIR /app

#4. Install Python deps
#   Copied on its own first so a code change doesn't bust the pip layer cache.
COPY src/main/python/requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

#5. Copy code
#   Trailing slash on the source copies the directory's *contents* into /app,
#   so main.py, wsgi.py and application/ sit at the WORKDIR root.
COPY src/main/python/ .

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
