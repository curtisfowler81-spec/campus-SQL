# College Management Web Application

A local Python/Flask application backed by MySQL. Users can create and edit
students and courses, enroll students in courses, and view all current records.

## Prerequisites

- Python 3.10 or later (developed for a modern Python 3 environment)
- A running MySQL server (MySQL 8.x recommended)
- MySQL Workbench or another MySQL client to execute setup SQL
- Internet access for initial Python dependency installation

Workbench is a client; the MySQL server must also be installed and running.
This is a Python web application: no separate compilation step is needed.

## Project files

```text
app.py                 Flask entry point, routes, form validation
models.py              Student, Course, Enrollment, CollegeRepository
requirements.txt       Python dependencies
schema.sql             Creates the database and tables without DROP TABLE
.env.example           Configuration template without real credentials
.gitignore             Excludes credentials and local environment files
templates/
    base.html
    index.html
    add.html
    edit.html
```

## Installation and setup

1. Clone or download this repository and open a terminal in its root folder.
2. In Workbench, connect to a running MySQL server, open `schema.sql`, and execute
   it. This creates `college_local_demo` and its three tables. It requires database
   creation privileges. No sample records are inserted; empty tables are expected.
   `IF NOT EXISTS` does not migrate an existing database with a different schema.
3. Create a Python virtual environment:

   ```sh
   python -m venv .venv
   ```

4. Install dependencies on Windows PowerShell:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   On macOS/Linux:

   ```sh
   .venv/bin/python -m pip install -r requirements.txt
   cp .env.example .env
   ```

5. Edit `.env`: enter your server host, port, existing MySQL username, password
   and schema name. The example does not create a MySQL account. Use an account
   with SELECT, INSERT, UPDATE privileges on these tables. Setup SQL may require
   an administrative account; normal app use does not require administrator rights.
   Never commit `.env` or `file.env`.
6. Start the application:

   Windows:

   ```powershell
   .\.venv\Scripts\python.exe app.py
   ```

   macOS/Linux:

   ```sh
   .venv/bin/python app.py
   ```

7. Open `http://localhost:5000`. Stop with Ctrl+C. Restart after changing settings.

## Demonstration

1. Click Add new record under Students. Enter an unused student ID and a degree
   path, along with optional details, and save.
2. Add a course using an unused course ID.
3. Add an enrollment by selecting the student and course. MySQL generates its ID.
4. Use Show All Students, Show All Courses and Show All Enrollments. Enrollment
   rows show student and course names. Show All Records shows all three sections.
5. Edit a record, save, and verify it in the webpage or Workbench.

For database verification:

```sql
USE college_local_demo;
SELECT * FROM Students;
SELECT * FROM Courses;
SELECT * FROM Enrollments;
```

## Object-oriented design

`Student`, `Course`, and `Enrollment` represent records with attributes matching
the database schema. They use Python dataclasses. `Student` validates its degree
path and credits. `Enrollment` requires student and course references.

`CollegeRepository` converts query results into model objects. The form handlers
construct model objects and call repository create/update methods to persist
attributes through parameterized SQL. The enrollment view uses
`Student.full_name()` and `Course.display_name()`.

These classes are the project's proposed model. Compare them against any separate
instructor-provided UML or required class design; exact alignment has not been
verified.

## Security and limitations

- Localhost-only development application, not production hosting.
- No authentication, deletion, audit history, or concurrent-edit conflict checks.
- Forms use CSRF protection; SQL values are parameterized.
- Show All loads all three tables into memory; suitable for a small class project.
- Student/course IDs are manual; enrollment IDs are automatic.
- Optional empty fields save as NULL. Dates are timezone-naive.
- Duplicate student/course enrollments are allowed by the schema.
- Edit validation failures redirect home without retaining unsaved input.
- Domain validation may reject preexisting empty degree paths or negative credits.
- Refresh forms after restarting the app because the default CSRF secret changes.
- Database contents are not stored in GitHub; schema.sql lets another machine
  recreate empty tables. Do not include real student personal information.

## Troubleshooting

- Missing module: install requirements using the same `.venv` Python used to run.
- Access denied: check MySQL credentials and account privileges.
- Unknown database/table: run schema.sql and confirm MYSQL_DATABASE in `.env`.
- Cannot connect: confirm MySQL server is running and host/port match.
- Save failed: inspect terminal output; check INSERT/UPDATE grants and IDs.

No prior add_records_upgrade.py script is needed with the current app.
