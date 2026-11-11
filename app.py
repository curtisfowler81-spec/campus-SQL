import os
import secrets
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import mysql.connector
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_wtf.csrf import CSRFProtect
from models import MODELS, CollegeRepository

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ('.env' if (BASE_DIR / '.env').exists() else 'file.env'))
app = Flask(__name__)
app.config.update(SECRET_KEY=os.getenv('SECRET_KEY') or secrets.token_hex(32),
                  SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
                  MAX_CONTENT_LENGTH=65536)
CSRFProtect(app)

# Only these fixed table/column names are allowed in queries.
TABLES = {
 'Students': {'pk':'student_id', 'fields':[
 ('first_name','text',20,False), ('last_name','text',20,False),
 ('email','text',50,False), ('degree_path','text',50,True),
 ('credits','number',None,False), ('college_level','text',20,False)]},
 'Courses': {'pk':'course_id', 'fields':[
 ('course_name','text',50,False), ('course_code','text',20,False),
 ('professor','text',50,False), ('created_at','datetime-local',None,False)]},
 'Enrollments': {'pk':'enrollment_id', 'fields':[
 ('student_id','student',None,True), ('course_id','course',None,True)]}
}

@contextmanager
def database():
    connection = mysql.connector.connect(
        host=os.getenv('MYSQL_HOST','127.0.0.1'),
        port=int(os.getenv('MYSQL_PORT','3306')),
        user=os.getenv('MYSQL_USER','college_viewer'),
        password=os.getenv('MYSQL_PASSWORD',''),
        database=os.getenv('MYSQL_DATABASE','college_local_demo'),
        connection_timeout=10)
    try:
        yield connection
    finally:
        connection.close()

def spec_for(table):
    if table not in TABLES:
        abort(404)
    return TABLES[table]

@app.get('/')
def home():
    selected = request.args.get('table', 'All')
    if selected != 'All' and selected not in TABLES:
        abort(404)
    tables, error = [], None
    try:
        with database() as connection:
            repository = CollegeRepository(connection)
            objects = {name: repository.all(name) for name in TABLES}
            students = {s.student_id:s for s in objects['Students']}
            courses = {c.course_id:c for c in objects['Courses']}
            for name, spec in TABLES.items():
                if selected not in ('All',name):
                    continue
                columns = [spec['pk']] + [f[0] for f in spec['fields']]
                rows = [obj.to_record() for obj in objects[name]]
                if name == 'Enrollments':
                    columns += ['student_name','course_name','course_code']
                    for row in rows:
                        student = students.get(row['student_id'])
                        course = courses.get(row['course_id'])
                        row['student_name'] = student.full_name() if student else '(missing student)'
                        row['course_name'] = course.display_name() if course else '(missing course)'
                        row['course_code'] = course.course_code if course else None
                tables.append(dict(name=name,pk=spec['pk'],columns=columns,rows=rows))
    except Exception:
        app.logger.exception('Unable to load records')
        error = 'Unable to load records. Check the terminal for details.'
    return render_template('index.html',tables=tables,error=error)

@app.route('/edit/<table>/<int:record_id>', methods=['GET','POST'])
def edit(table, record_id):
    spec = spec_for(table)
    pk = spec['pk']
    try:
        with database() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(f'SELECT * FROM `{table}` WHERE `{pk}` = %s', (record_id,))
                row = cursor.fetchone()
                if row is None:
                    abort(404)
                if request.method == 'POST':
                    values = []
                    for name, kind, limit, required in spec['fields']:
                        value = request.form.get(name, '').strip()
                        if required and not value:
                            raise ValueError(f'{name} is required.')
                        if limit and len(value) > limit:
                            raise ValueError(f'{name} must be at most {limit} characters.')
                        if value and kind in ('number','student','course'):
                            try:
                                value = int(value)
                            except ValueError:
                                raise ValueError(f'{name} must be a whole number.')
                            if not -2147483648 <= value <= 2147483647:
                                raise ValueError(f'{name} is outside the MySQL INT range.')
                            if name == 'credits' and value < 0:
                                raise ValueError('credits cannot be negative.')
                        elif value and kind == 'datetime-local':
                            try:
                                value = datetime.fromisoformat(value)
                            except ValueError:
                                raise ValueError('Enter a valid date and time.')
                            if value.year < 1000:
                                raise ValueError('Date year must be at least 1000.')
                        values.append(None if value == '' else value)
                    try:
                        record = MODELS[table](**dict(zip([field[0] for field in spec['fields']], values)), **{pk: record_id})
                        CollegeRepository.update(cursor, table, record)
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
                    flash(f'{table} record {record_id} saved.', 'success')
                    return redirect(url_for('home'))
                students, courses = [], []
                if table == 'Enrollments':
                    cursor.execute('SELECT student_id, first_name, last_name FROM Students ORDER BY student_id')
                    students = cursor.fetchall()
                    cursor.execute('SELECT course_id, course_name FROM Courses ORDER BY course_id')
                    courses = cursor.fetchall()
                for name, kind, _, _ in spec['fields']:
                    if kind == 'datetime-local' and isinstance(row.get(name), datetime):
                        row[name] = row[name].isoformat(timespec='seconds')
                return render_template('edit.html', table=table, spec=spec, row=row,
                                       students=students, courses=courses)
            finally:
                cursor.close()
    except ValueError as exc:
        flash(str(exc), 'error')
    except mysql.connector.IntegrityError:
        app.logger.exception('Invalid enrollment reference or other constraint violation')
        flash('Save failed: check the selected student/course and database constraints.', 'error')
    except mysql.connector.Error:
        app.logger.exception('Database operation failed')
        flash('Database operation failed. Check the terminal; your account may need SELECT and UPDATE permissions.', 'error')
    except Exception:
        app.logger.exception('Unexpected edit error')
        flash('Could not save or load the record. Check the terminal for details.', 'error')
    return redirect(url_for('home'))


# ADD_RECORDS_V1
@app.route('/add/<table>', methods=['GET', 'POST'])
def add_record(table):
    spec = spec_for(table)
    values_in = request.form.to_dict() if request.method == 'POST' else {}
    error = None
    students, courses = [], []
    try:
        with database() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                if table == 'Enrollments':
                    cursor.execute('SELECT student_id, first_name, last_name FROM Students ORDER BY student_id')
                    students = cursor.fetchall()
                    cursor.execute('SELECT course_id, course_name FROM Courses ORDER BY course_id')
                    courses = cursor.fetchall()
                if request.method == 'POST':
                    try:
                        fields = list(spec['fields'])
                        if table != 'Enrollments':
                            fields.insert(0, (spec['pk'], 'number', None, True))
                        columns, values = [], []
                        for name, kind, limit, required in fields:
                            value = request.form.get(name, '').strip()
                            if required and not value:
                                raise ValueError(f'{name} is required.')
                            if limit and len(value) > limit:
                                raise ValueError(f'{name} must be at most {limit} characters.')
                            if value and kind in ('number', 'student', 'course'):
                                try:
                                    value = int(value)
                                except ValueError:
                                    raise ValueError(f'{name} must be a whole number.')
                                if not -2147483648 <= value <= 2147483647:
                                    raise ValueError(f'{name} is outside the MySQL INT range.')
                                if name == 'credits' and value < 0:
                                    raise ValueError('credits cannot be negative.')
                            elif value and kind == 'datetime-local':
                                try:
                                    value = datetime.fromisoformat(value)
                                except ValueError:
                                    raise ValueError('Enter a valid date and time.')
                                if value.year < 1000:
                                    raise ValueError('Date year must be at least 1000.')
                            columns.append(name)
                            values.append(None if value == '' else value)
                        record = MODELS[table](**dict(zip(columns, values)))
                        CollegeRepository.create(cursor, table, record)
                        new_id = cursor.lastrowid if table == 'Enrollments' else values[0]
                        connection.commit()
                        flash(f'{table} record {new_id} added.', 'success')
                        return redirect(url_for('edit', table=table, record_id=new_id))
                    except ValueError as exc:
                        connection.rollback()
                        error = str(exc)
                    except mysql.connector.IntegrityError as exc:
                        connection.rollback()
                        app.logger.exception('Insert constraint violation')
                        error = ('That ID already exists. Choose an unused ID.' if exc.errno == 1062
                                 else 'Cannot add record: check selected student/course and database constraints.')
                    except mysql.connector.Error:
                        connection.rollback()
                        app.logger.exception('Insert failed')
                        error = 'Could not add record. Check terminal details and INSERT permissions.'
            finally:
                cursor.close()
    except Exception:
        app.logger.exception('Could not load add-record form')
        error = 'Could not connect or load form choices. Check the terminal.'
    fields = list(spec['fields'])
    if table != 'Enrollments':
        fields.insert(0, (spec['pk'], 'number', None, True))
    return render_template('add.html', table=table, fields=fields, values=values_in,
                           students=students, courses=courses, error=error)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
