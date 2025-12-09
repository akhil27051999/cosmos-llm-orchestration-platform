# Student-REST-API Webserver Development

## Project Overview

A lightweight Flask REST API starter project for CRUD operations (student records example). This README shows how to initialize the project, install dependencies, configure version control, and push to GitHub.

## Prerequisites

- Python 3.8+ (adjust to your project's minimum)
- git
- Access to a PostgreSQL instance (if you plan to use PostgreSQL)

## Project Setup

### Create Project Structure

Run the following in your terminal:

```bash
# Create project directory and navigate to it
mkdir Flask-REST-API && cd Flask-REST-API

# Create virtual environment
python3 -m venv .venv
```

### Activate Virtual Environment

```bash
# On Linux / macOS
source .venv/bin/activate

# On Windows (PowerShell)
.venv\Scripts\Activate
```

Note: Your shell prompt should now show the `.venv` prefix.

## Install Packages

Install the packages required for development and testing:

```bash
pip install Flask Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-dotenv pytest pytest-flask pytest-dotenv gunicorn
```

### Verify Installation

```bash
# Check Python version
python3 --version

# List installed packages
pip list
```

### Generate requirements.txt

Freeze dependencies:

```bash
pip freeze > requirements.txt
```

### Expected requirements.txt

The following is the expected dependencies snapshot used for the project (for reference):

```
alembic==1.16.4
blinker==1.9.0
click==8.2.1
Flask==3.1.1
Flask-Migrate==4.1.0
Flask-SQLAlchemy==3.1.1
greenlet==3.2.4
gunicorn==23.0.0
iniconfig==2.1.0
itsdangerous==2.2.0
Jinja2==3.1.6
Mako==1.3.10
MarkupSafe==3.0.2
packaging==25.0
pluggy==1.6.0
psycopg2-binary==2.9.10
Pygments==2.19.2
pytest==8.4.1
pytest-dotenv==0.5.2
pytest-flask==1.3.0
python-dotenv==1.1.1
SQLAlchemy==2.0.43
typing_extensions==4.14.1
Werkzeug==3.1.3
```

(Your actual `requirements.txt` may differ depending on the latest package versions — run `pip freeze` to capture your environment.)

## Package Purpose Reference

| Package               | Purpose                       | Required For                       |
|-----------------------|-------------------------------|-------------------------------------|
| Flask                 | Web framework                 | Core application                    |
| Flask-SQLAlchemy      | ORM integration               | Database operations                 |
| Flask-Migrate         | Database migrations           | Schema versioning                   |
| psycopg2-binary       | PostgreSQL adapter            | PostgreSQL database                 |
| python-dotenv         | Environment variables         | Configuration management            |
| pytest                | Testing framework             | Application testing                 |
| pytest-flask          | Flask test helpers            | Flask-specific testing              |
| pytest-dotenv         | Test env variables support    | Testing with .env files             |
| gunicorn              | WSGI server                   | Production deployment               |

## Version Control Setup

Initialize a Git repository and create a `.gitignore`.

```bash
git init
```

### Create .gitignore

Create a `.gitignore` in the project root with contents like the following:

```gitignore
# Virtual environments
.venv/
venv/

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd

# Environment variables
.env
.env.local

# Database
*.db
*.sqlite3

# OS files
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/

# Logs
*.log

# Temporary files
tmp/
temp/
```

### Initial Commit

```bash
git add .
git commit -m "Initial commit: Flask REST API project setup"
```

## GitHub Repository Setup

Create a repository on GitHub (example name: `student-crud-api`). Do NOT initialize with a README on GitHub if you already have local files.

### Push to GitHub

Replace `your-username` with your GitHub username and run:

```bash
# Add remote origin
git remote add origin https://github.com/your-username/student-crud-api.git

# Rename default branch to main
git branch -M main

# Push to GitHub
git push -u origin main
```

## Project Maintenance

- To add a new package:

```bash
pip install <package-name>
pip freeze > requirements.txt
```

- To update dependencies, update installed packages and re-freeze.

## Contributing

1. Fork the repo.
2. Create a feature branch: `git checkout -b feat/your-feature`.
3. Make changes, add tests.
4. Commit and push: `git push origin feat/your-feature`.
5. Open a Pull Request.

# PostgreSQL Setup Guide for Flask Application (Ubuntu)

This document contains step-by-step instructions to install, configure, and verify PostgreSQL for use with a Flask application on Ubuntu. It includes commands, configuration examples, troubleshooting tips, a quick setup script, and security recommendations.

## Prerequisites

- Ubuntu system with sudo access
- Internet connection
- (Optional) PostgreSQL client tools installed on your local machine if connecting remotely

---

## 1. PostgreSQL Installation

### Install PostgreSQL

```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
```

### Verify Installation Status

```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# If not running, start the service
sudo systemctl start postgresql

# Enable PostgreSQL to start on boot
sudo systemctl enable postgresql
```

---

## 2. Database Configuration

### Access PostgreSQL Shell

```bash
sudo -u postgres psql
```

### Create Database User

Use the psql shell or run these SQL commands:

```sql
-- Create a new user with password
CREATE USER student_user WITH PASSWORD 'student123';

-- Alternative: Use existing postgres user with new password
ALTER USER postgres WITH PASSWORD 'postgres123';
```

> Security note: Replace the example passwords with strong secrets before using in any non-test environment.

### Create Application Database

```sql
-- Create database for the application
CREATE DATABASE studentdb;

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON DATABASE studentdb TO student_user;

-- Make the user the owner of the database (optional)
ALTER DATABASE studentdb OWNER TO student_user;
```

---

## 3. Verification Commands

```bash
# List all users
sudo -u postgres psql -c "\du"

# List all databases
sudo -u postgres psql -c "\l"

# Test connection with created user (prompts for password)
psql -U student_user -d studentdb -h localhost -W

# Or connect directly as postgres user
sudo -u postgres psql -d studentdb
```

Useful psql commands:

```sql
-- Connect to specific database
\c studentdb

-- List all tables
\dt

-- Describe table structure
\d students

-- View table data
SELECT * FROM students;

-- Exit PostgreSQL shell
\q
```

---

## 4. Flask Application Configuration

### Install PostgreSQL Driver

Ensure your virtual environment is active, then install:

```bash
# Make sure virtual environment is activated
source .venv/bin/activate

# Install PostgreSQL adapter
pip install psycopg2-binary
```

### Environment Variables (.env)

Create a `.env` file in your project root (replace credentials as appropriate):

```bash
# Flask environment variables
FLASK_ENV=development
FLASK_APP=app/wsgi.py
FLASK_DEBUG=1
PYTHONUNBUFFERED=1
DEBUG=True

# PostgreSQL configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=studentdb
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/studentdb
```

> Note: For production, avoid committing `.env` to source control. Use secrets management or environment variables provided by your hosting environment.

### Flask Configuration (config.py example)

```python
import os
from dotenv import load_dotenv
# This file is used to configure the application settings
# Load environment variables from a .env file
load_dotenv()

class Config:
    DEBUG = os.getenv('DEBUG', 'False') == 'True'

    # postgresql settings
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'dbname')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

    SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # always good to disable
   
```

---

## 5. Troubleshooting Common Issues

### Connection Issues

```bash
# Check if PostgreSQL is listening on correct port
sudo netstat -tulpn | grep 5432

# Check PostgreSQL logs
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### Permission Issues

If you face permission problems, run in psql as a superuser:

```sql
GRANT ALL ON SCHEMA public TO student_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO student_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO student_user;
```

### Reset PostgreSQL Password

```sql
-- If you forget the postgres user password:
ALTER USER postgres WITH PASSWORD 'new_password';
```

---

## 6. Quick Setup Script

Create a script named `setup_db.sh` to automate user and database creation.

Contents of `setup_db.sh`:

```bash
#!/bin/bash

# Database setup script
echo "Setting up PostgreSQL database for Flask application..."

# Create user and database
sudo -u postgres psql -c "CREATE USER student_user WITH PASSWORD 'student123';"
sudo -u postgres psql -c "CREATE DATABASE studentdb;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE studentdb TO student_user;"

echo "Database setup completed!"
echo "Connection string: postgresql://student_user:student123@localhost:5432/studentdb"
```

Make it executable and run:

```bash
chmod +x setup_db.sh
./setup_db.sh
```

> Reminder: Change default passwords before using in real environments.

---

## 7. Security Recommendations

For production, reduce privileges and follow the principle of least privilege:

```sql
-- Restrict elevated capabilities for the application user
ALTER USER student_user NOSUPERUSER NOCREATEDB NOCREATEROLE;

-- Create a read-only user for specific operations
CREATE USER read_only_user WITH PASSWORD 'readonly123';
GRANT CONNECT ON DATABASE studentdb TO read_only_user;
GRANT USAGE ON SCHEMA public TO read_only_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO read_only_user;
```

Additional recommendations:
- Use strong, unique passwords or managed secrets (e.g., Vault, AWS Secrets Manager).
- Use SSL/TLS for remote DB connections.
- Restrict network access to the PostgreSQL port.
- Regularly back up your database and test restores.

# Flask App with PostgreSQL Integration Guide

Project Structure (suggested)
```
Flask-REST-API/
├── .venv/                    # Virtual environment
├── app/                      # Application package
│   ├── __init__.py           # App factory
│   ├── config.py             # Configuration settings
│   └── models.py             # Database models
├── migrations/               # Database migrations (auto-generated)
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── README-FLASK-POSTGRESQL.md
```

### 1. Environment Configuration

Create a `.env` file in the project root to store environment-specific and sensitive values. Example:

```bash
# Flask environment variables
FLASK_ENV=development
FLASK_APP=app/wsgi.py
FLASK_DEBUG=1
PYTHONUNBUFFERED=1
DEBUG=True

# PostgreSQL configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres123
POSTGRES_DB=studentdb
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

DATABASE_URL=postgresql://postgres:postgres123@postgres:5432/studentdb
```

Configuration class (app/config.py)

```python
import os
from dotenv import load_dotenv
# This file is used to configure the application settings
# Load environment variables from a .env file
load_dotenv()

class Config:
    DEBUG = os.getenv('DEBUG', 'False') == 'True'

    # postgresql settings
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'dbname')
    POSTGRES_PORT = os.getenv('POSTGRES_PORT', '5432')

    SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # always good to disable

```

Notes:
- Use DATABASE_URL when deploying to services that provide a single connection string.
- Do not commit `.env` to source control. Use a secret manager for production.

### 2. Application Setup

App factory pattern provides flexibility for testing and multiple configurations.

app/__init__.py (application factory, extensions initialization)

```python
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .logger import setup_logger

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    app = Flask(__name__)

    # Configure the app
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('app.config.Config')


    # Initialize logger
    logger = setup_logger('student_logger', log_file='app.log')
    app.logger.info("Student Management API started successfully.")

    # Initialize database and migration
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models inside app context
    with app.app_context():
        from . import models

    # Import and register blueprints here (after db/models are ready)
    from .routes import student_bp
    app.register_blueprint(student_bp, url_prefix='/students')

    # Home route
    @app.route('/')
    def home():
        app.logger.info("Home page accessed")
        return "Welcome to the Student Management API!"

    # Health check route
    @app.route('/health')
    def health():
        app.logger.info("Health check accessed")
        return jsonify({"status": "ok"}), 200

    return app
```

### 3. Database Models

app/models.py — example Student model:

```python
from . import db   # Import db from the app package

class Student(db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    domain = db.Column(db.String(50), nullable=False)
    gpa = db.Column(db.Float, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

```

### 4. Database Migrations

Initial setup and common commands (requires Flask-Migrate installed and FLASK_APP set).

Set FLASK_APP and initialize migrations:

```bash
# Set the flask app entrypoint (Mac/Linux)
export FLASK_APP=app:create_app

# On Windows (PowerShell)
# $env:FLASK_APP = "app:create_app"

# Initialize migrations (run once)
flask db init

# Generate migration after creating models
flask db migrate -m "Initial migration - create students table"

# Apply migrations to the DB
flask db upgrade
```

Migration folder structure after `flask db init`:

```
migrations/
├── versions/           # Individual migration scripts
├── env.py              # Alembic environment configuration
└── script.py.mako      # Migration script template
```

Common migration commands:
- `flask db init` — initialize migrations directory (once)
- `flask db migrate -m "message"` — generate migration after model changes
- `flask db upgrade` — apply migrations
- `flask db downgrade` — rollback last migration
- `flask db current` — show current migration revision
- `flask db history` — show migration history

### 5. Database Operations

Using Flask shell for quick DB operations. Start shell (ensures app context is loaded):

```bash
flask shell
```

Example operations inside the shell:

```python
from app import db
from app.models import Student

# Create a new student
new_student = Student(
    name='Akhil Thydai',
    domain='Electronics and Communication Engineering',
    gpa=7.01,
    email='160101130028@cutm.ac.in'
)
db.session.add(new_student)
db.session.commit()

# Query all students
students = Student.query.all()

# Get by ID
student = Student.query.get(1)

# Filter by email
student_by_email = Student.query.filter_by(email='160101130028@cutm.ac.in').first()

# Update
student = Student.query.get(1)
student.gpa = 7.5
db.session.commit()

# Delete
db.session.delete(student)
db.session.commit()
```

PostgreSQL verification commands (shell):

```bash
# Connect to PostgreSQL
psql -h localhost -U postgres -d studentdb

# Inside psql:
\dt
\d students
SELECT * FROM students;
```

### 6. Schema Evolution Example

Adding a new nullable column (phone):

1) Update model (app/models.py):

```python
phone = db.Column(db.String(15), nullable=True)  # New optional field
```

2) Generate and apply migration:

```bash
flask db migrate -m "Add phone number field to Student"
flask db upgrade
```

Handling new non-nullable required fields for existing data:
- Option A: Add column as nullable, backfill data, then alter to non-nullable in a later migration.
- Option B: Add column with a server_default in migration so existing rows have a value; then remove the default if desired.

Example migration snippet to add non-nullable with default:

```python
def upgrade():
    op.add_column('students',
        sa.Column('phone', sa.String(length=15), nullable=False, server_default='000-000-0000')
    )
    # Optionally remove server_default afterward
    op.alter_column('students', 'phone', server_default=None)
```

### 7. Complete Workflow Example

- Edit app/models.py to change or add fields.
- Generate migration: `flask db migrate -m "Describe changes"`.
- Review `migrations/versions/<revision>.py`.
- Apply: `flask db upgrade`.
- Verify table/data in PostgreSQL: `psql -h localhost -U postgres -d studentdb -c "SELECT * FROM students;"`.

### 8. Troubleshooting common issues:
- Migration conflicts: If migrations diverge, consider merging revisions or — only in development — resetting migrations:
  ```bash
  rm -rf migrations/
  flask db init
  flask db migrate -m "Initial"
  flask db upgrade
  ```
  Do NOT do this on production databases without careful planning and backups.
- Database connection errors: verify PostgreSQL is running and .env credentials are correct.
- Import-time errors: ensure `create_app` registers or imports modules only after extensions are initialized.

### 9. Best Practices
- Always use migrations (Alembic via Flask-Migrate) for schema changes; do not manually alter production DB schema.
- Keep migration scripts in version control.
- Use meaningful migration messages.
- Test migrations on a development/staging DB before production.
- Use environment variables or a secret manager for DB credentials and secrets in production.
- Backup databases prior to major schema changes.
- Limit DB user privileges in production (principle of least privilege).
- Log SQL only when needed (SQLALCHEMY_ECHO).

# Flask REST API — Student CRUD Operations

## API Overview

### Base URL (development)
```
http://localhost:5000/api/students
```

### Project Structure (recommended)
```text
Flask-REST-API/
├── app/
│   ├── __init__.py          # App factory
│   ├── config.py            # Configuration
│   ├── models.py            # Database models
│   ├── loggers.py           # logger configuration
│   └── routes.py            # API routes
├── migrations/              # DB migrations
├── .env                     # Environment variables
└── requirements.txt
```

## Loggers Setup 
```python
import logging
import os

def setup_logger(name, log_file='app.log', level=logging.DEBUG):
    
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding multiple handlers if logger already exists
    if not logger.hasHandlers():
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter) 
        logger.addHandler(console_handler) 

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger
```

## Blueprint Setup

### Create routes package
```bash
mkdir -p app/routes
touch app/routes/__init__.py
touch app/routes/student_routes.py
```

Register blueprint in your app factory (see implementation snippet below). The blueprint is defined with:
- name: `student`
- url_prefix: `/api/students`

## API Endpoints

#### Create Student — POST /api/students
- Description: Add a new student.
- Request body (JSON):
```json
{
  "name": "John Doe",
  "domain": "Computer Science",
  "gpa": 3.8,
  "email": "john.doe@university.edu"
}
```
- Success response:
  - 201 Created
```json
{
  "message": "Student added successfully!",
  "student_id": 1
}
```
- Errors:
  - 400 Missing/invalid fields
  - 409 Email conflict
  - 500 Database error

#### Get All Students — GET /api/students
- Description: Retrieve all students.
- Success response (200 OK):
```json
{
  "count": 2,
  "students": [
    { "id": 1, "name": "John Doe", "domain": "Computer Science", "gpa": 3.8, "email": "john.doe@university.edu" },
    { "id": 2, "name": "Jane Smith", "domain": "EE", "gpa": 3.9, "email": "jane@university.edu" }
  ]
}
```

#### Get Student by ID — GET /api/students/<id>
- Description: Retrieve a single student by ID.
- Success response (200 OK):
```json
{
  "id": 1,
  "name": "John Doe",
  "domain": "Computer Science",
  "gpa": 3.8,
  "email": "john.doe@university.edu"
}
```
- Errors:
  - 404 Not Found (if student does not exist)

#### Update Student — PUT /api/students/<id>
- Description: Partial updates are accepted; only provided fields are updated.
- Request body example:
```json
{ "name": "John Updated", "gpa": 3.9 }
```
- Success response:
  - 200 OK
```json
{ "message": "Student updated successfully!" }
```
- Errors:
  - 400 No data / invalid format
  - 404 Not Found
  - 409 Email conflict
  - 500 Database error

#### Delete Student — DELETE /api/students/<id>
- Description: Permanently deletes the student record.
- Success response:
  - 200 OK
```json
{
  "message": "Student deleted successfully!",
  "deleted_student": { "id": 1, "name": "John Doe" }
}
```
- Errors:
  - 404 Not Found
  - 500 Database error

### Error Handling

Standard example response formats:

- 400 Bad Request
```json
{
  "error": "Missing required fields",
  "required_fields": ["name", "domain", "gpa", "email"]
}
```

- 404 Not Found
```json
{ "error": "Student not found" }
```

- 409 Conflict
```json
{ "error": "Email already exists" }
```

- 500 Internal Server Error
```json
{ "error": "Database error" }
```

## Complete Implementation Snippets

### App Factory (app/__init__.py)
```python
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .logger import setup_logger

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=None):
    app = Flask(__name__)

    # Configure the app
    if config_class:
        app.config.from_object(config_class)
    else:
        app.config.from_object('app.config.Config')


    # Initialize logger
    logger = setup_logger('student_logger', log_file='app.log')
    app.logger.info("Student Management API started successfully.")

    # Initialize database and migration
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models inside app context
    with app.app_context():
        from . import models

    # Import and register blueprints here (after db/models are ready)
    from .routes import student_bp
    app.register_blueprint(student_bp, url_prefix='/students')

    # Home route
    @app.route('/')
    def home():
        app.logger.info("Home page accessed")
        return "Welcome to the Student Management API!"

    # Health check route
    @app.route('/health')
    def health():
        app.logger.info("Health check accessed")
        return jsonify({"status": "ok"}), 200

    return app
```

## Testing the API

### Using curl
```bash
# Create
curl -X POST http://localhost:5000/api/students \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Johnson","domain":"Mathematics","gpa":3.7,"email":"alice@university.edu"}'

# Get all
curl http://localhost:5000/api/students

# Get one
curl http://localhost:5000/api/students/1

# Update
curl -X PUT http://localhost:5000/api/students/1 \
  -H "Content-Type: application/json" \
  -d '{"gpa":3.9}'

# Delete
curl -X DELETE http://localhost:5000/api/students/1
```

### Using Python requests
```python
import requests
BASE = "http://localhost:5000/api/students"

# Create
r = requests.post(BASE, json={
    "name": "Bob Wilson",
    "domain": "Physics",
    "gpa": 3.6,
    "email": "bob@university.edu"
})
print(r.status_code, r.json())

# List
r = requests.get(BASE)
print(r.status_code, r.json())
```

### Verification & Notes
- Ensure environment variables (DATABASE_URL or individual DB_* vars) are set and Flask app is configured with `FLASK_APP=app:create_app`.
- Run migrations with Flask-Migrate: `flask db init` (once), `flask db migrate -m "msg"`, `flask db upgrade`.
- Do not expose `.env` or secrets in VCS.
- Validate inputs further for production (email format, GPA ranges, rate-limiting, auth).

# Flask Student API — Postman Testing Documentation

> This README provides a complete Postman testing guide for the Student CRUD REST API built with Flask and PostgreSQL.

**Base URL (development)**

`http://localhost:5000/api/students`

---

## API Overview

This API exposes CRUD operations for student records.

- Base URL (example): `http://localhost:5000/api/students`

---

## Postman Collection (Import JSON)

To import into Postman use the following JSON structure (save as `Student Management API.postman_collection.json` or paste into Postman's Import → Raw Text):

```json
{
  "info": {
    "name": "Student Management API",
    "description": "Complete CRUD operations for Student records",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": "http://localhost:5000/api/students/health"
      }
    },
    {
      "name": "Create Student",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n    \"name\": \"John Doe\",\n    \"domain\": \"Computer Science\",\n    \"gpa\": 3.8,\n    \"email\": \"john.doe@university.edu\"\n}"
        },
        "url": "http://localhost:5000/api/students"
      }
    },
    {
      "name": "Get All Students",
      "request": {
        "method": "GET",
        "header": [],
        "url": "http://localhost:5000/api/students"
      }
    },
    {
      "name": "Get Student by ID",
      "request": {
        "method": "GET",
        "header": [],
        "url": "http://localhost:5000/api/students/1"
      }
    },
    {
      "name": "Update Student",
      "request": {
        "method": "PUT",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n    \"name\": \"John Updated\",\n    \"gpa\": 3.9\n}"
        },
        "url": "http://localhost:5000/api/students/1"
      }
    },
    {
      "name": "Delete Student",
      "request": {
        "method": "DELETE",
        "header": [],
        "url": "http://localhost:5000/api/students/1"
      }
    }
  ]
}
```

---

## Postman Environment Setup

Create a new environment (Postman → Environments → Create) named **Student API Local** and add these variables:

| Variable   | Initial Value                | Current Value                |
|------------|------------------------------|------------------------------|
| base_url   | http://localhost:5000        | http://localhost:5000        |
| student_id | 1                            | 1                            |

Use `{{base_url}}` and `{{student_id}}` in request URLs for portability.

---

## API Endpoints & Testing Guide

### 1. Health Check
- Method: GET  
- URL: `{{base_url}}/api/students/health`  
- Headers: None  
- Expected response (200 OK):
```json
{
  "status": "healthy",
  "message": "Student API is running",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### 2. Create Student — POST `/api/students`
- Method: POST  
- URL: `{{base_url}}/api/students`  
- Headers: `Content-Type: application/json`  
- Body (JSON):
```json
{
  "name": "Alice Johnson",
  "domain": "Computer Science",
  "gpa": 3.8,
  "email": "alice.johnson@university.edu"
}
```
- Success (201 Created):
```json
{
  "message": "Student added successfully!",
  "student_id": 1
}
```
- Error responses:
  - 400 Bad Request: missing fields / invalid GPA
  - 409 Conflict: email already exists
  - 500 Internal Server Error: DB error

---

### 3. Get All Students — GET `/api/students`
- Method: GET  
- URL: `{{base_url}}/api/students`  
- Success (200 OK) example:
```json
{
  "count": 2,
  "students": [
    {
      "id": 1,
      "name": "Alice Johnson",
      "domain": "Computer Science",
      "gpa": 3.8,
      "email": "alice.johnson@university.edu"
    },
    {
      "id": 2,
      "name": "Bob Smith",
      "domain": "Electrical Engineering",
      "gpa": 3.9,
      "email": "bob.smith@university.edu"
    }
  ]
}
```
- Empty DB:
```json
{
  "count": 0,
  "students": []
}
```

---

### 4. Get Student by ID — GET `/api/students/{{student_id}}`
- Method: GET  
- URL: `{{base_url}}/api/students/{{student_id}}`  
- Success (200 OK):
```json
{
  "id": 1,
  "name": "Alice Johnson",
  "domain": "Computer Science",
  "gpa": 3.8,
  "email": "alice.johnson@university.edu"
}
```
- 404 Not Found:
```json
{ "error": "Student not found" }
```

---

### 5. Update Student — PUT `/api/students/{{student_id}}`
- Method: PUT  
- URL: `{{base_url}}/api/students/{{student_id}}`  
- Headers: `Content-Type: application/json`  
- Body (partial update allowed):
```json
{
  "name": "Alice Johnson-Updated",
  "gpa": 3.9
}
```
- Success (200 OK):
```json
{ "message": "Student updated successfully!" }
```
- Errors:
  - 400 No data / invalid fields
  - 404 Not Found
  - 409 Email conflict

---

### 6. Delete Student — DELETE `/api/students/{{student_id}}`
- Method: DELETE  
- URL: `{{base_url}}/api/students/{{student_id}}`  
- Success (200 OK):
```json
{
  "message": "Student deleted successfully!",
  "deleted_student": {
    "id": 1,
    "name": "Alice Johnson-Updated"
  }
}
```
- 404 Not Found:
```json
{ "error": "Student not found" }
```

---

## Complete Testing Workflow

### Full CRUD Cycle (recommended)
1. Create a student (POST) → note returned `student_id`.  
2. Get all students (GET) → verify creation appears.  
3. Get specific student (GET `/{student_id}`) → verify fields.  
4. Update student (PUT `/{student_id}`) → verify success.  
5. Delete student (DELETE `/{student_id}`) → verify success.  
6. Verify deletion (GET `/{student_id}`) → should return 404.

---

## Error Scenario Testing

- Create with missing fields:
```json
{ "name": "Incomplete Student", "domain": "Physics" }
```
Expect: 400 Bad Request.

- Create with invalid GPA:
```json
{ "name": "Invalid GPA", "domain": "Chemistry", "gpa": "not_a_number", "email": "invalid@university.edu" }
```
Expect: 400 Bad Request.

- Update non-existent student:
PUT `/api/students/9999` with some body → Expect: 404 Not Found.

- Duplicate email creation:
Create same email twice → Expect: 409 Conflict.

---

## Quick cURL Commands

Create student:
```bash
curl -X POST http://localhost:5000/api/students \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Alice Johnson",
    "domain": "Computer Science",
    "gpa": 3.8,
    "email": "alice.johnson@university.edu"
  }'
```

Get all students:
```bash
curl http://localhost:5000/api/students
```

Get specific student:
```bash
curl http://localhost:5000/api/students/1
```

Update student:
```bash
curl -X PUT http://localhost:5000/api/students/1 \
  -H "Content-Type: application/json" \
  -d '{"gpa": 3.9, "name": "Alice Johnson-Updated"}'
```

Delete student:
```bash
curl -X DELETE http://localhost:5000/api/students/1
```

---

## Testing Notes & Best Practices

Pre-requisites:
- Flask app running on `localhost:5000`
- PostgreSQL running and connected
- Migrations applied (`flask db upgrade`)
- Virtual environment activated

Test data management:
- Use unique emails per test.
- Clean up test data after runs (or use disposable test DB).
- Consider automated Postman tests and a CI job to run them against a staging environment.

Postman tips:
- Put requests into a Collection and group by resource.
- Use Environment variables (e.g., `base_url`, `student_id`) to make requests portable.
- Add Tests in Postman to assert response codes and JSON structure.
- Use pre-request scripts to dynamically set `student_id` from response data.

Common issues:
- Connection refused — ensure Flask app is running and listening on port 5000.
- DB errors — confirm Postgres is running, credentials and `DATABASE_URL` are correct.
- 404 errors — check URL and `student_id`.
- Validation errors — ensure Content-Type header and JSON payloads are correct.


