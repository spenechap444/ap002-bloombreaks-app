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

#6. Switch to non-root
USER appuser

#7. Expose & healthcheck
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
   CMD curl -f http://localhost:8000/ping || exit 1

# For Gunicorn:
# CMD ["gunicorn", "wsgi:application", "--workers", "3", "--bind", "0.0.0.0:8000"]

#8. Execute with runtime args

# default env-vars (can be overridden at runtime with -e)
ENV HOST=0.0.0.0 \
    PORT=8000

# single CMD that launches your app and lets Docker expand $HOST, etc.
ENTRYPOINT ["python", "main.py"]
CMD ["--host", "0.0.0.0", "--port", "8000"]