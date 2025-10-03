# Stage 1: Build Python dependencies
FROM python:3.10-alpine AS build
WORKDIR /api/app

# Install build dependencies for psycopg2
RUN apk add --no-cache gcc musl-dev postgresql-dev

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --user --no-cache-dir -r requirements.txt \
    && find /root/.local -name '*.pyc' -delete \
    && find /root/.local -name '__pycache__' -delete

# Stage 2: Main application image
FROM python:3.10-alpine AS main
WORKDIR /api

# Install PostgreSQL client for pg_isready
RUN apk add --no-cache postgresql-client

# Copy installed Python packages from build stage
COPY --from=build /root/.local /root/.local

# Copy the entire app folder
COPY . ./app

# Add pip binaries to PATH
ENV PATH=/root/.local/bin:$PATH
ENV FLASK_APP=app/wsgi.py

# Expose port
EXPOSE 5000

# Start Gunicorn server
CMD ["gunicorn", "app.wsgi:app"]
