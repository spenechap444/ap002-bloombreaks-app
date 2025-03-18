FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app/

# Expose the port that Gunicorn will run on
EXPOSE 8000

# Command to run the applicatio using Gunicorn
CMD ["gunicorn", "wsgi:application", "--workers", "3", "--bind", "0.0.0.0:8000"]
