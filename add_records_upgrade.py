from pathlib import Path
from datetime import datetime
import ast

ROUTE = "\n# ADD_RECORDS_V1\n@app.route('/add/<table>', methods=['GET', 'POST'])\ndef add_record(table):\n    spec = spec_for(table)\n    values_in = request.form.to_dict() if request.method == 'POST' else {}\n    error = None\n    students, courses = [], []\n    try:\n        with database() as connection:\n            cursor = connection.cursor(dictionary=True)\n            try:\n                if table == 'Enrollments':\n                    cursor.execute('SELECT student_id, first_name, last_name FROM Students ORDER BY student_id')\n                    students = cursor.fetchall()\n                    cursor.execute('SELECT course_id, course_name FROM Courses ORDER BY course_id')\n                    courses = cursor.fetchall()\n                if request.method == 'POST':\n                    try:\n                        fields = list(spec['fields'])\n                        if table != 'Enrollments':\n                            fields.insert(0, (spec['pk'], 'number', None, True))\n                        columns, values = [], []\n                        for name, kind, limit, required in fields:\n                            value = request.form.get(name, '').strip()\n                            if required and not value:\n                                raise ValueError(f'{name} is required.')\n                            if limit and len(value) > limit:\n                                raise ValueError(f'{name} must be at most {limit} characters.')\n                            if value and kind in ('number', 'student', 'course'):\n                                try:\n                                    value = int(value)\n                                except ValueError:\n                                    raise ValueError(f'{name} must be a whole number.')\n                                if not -2147483648 <= value <= 2147483647:\n                                    raise ValueError(f'{name} is outside the MySQL INT range.')\n                                if name == 'credits' and value < 0:\n                                    raise ValueError('credits cannot be negative.')\n                            elif value and kind == 'datetime-local':\n                                try:\n                                    value = datetime.fromisoformat(value)\n                                except ValueError:\n                                    raise ValueError('Enter a valid date and time.')\n                                if value.year < 1000:\n                                    raise ValueError('Date year must be at least 1000.')\n                            columns.append(name)\n                            values.append(None if value == '' else value)\n                        column_sql = ', '.join('`' + name + '`' for name in columns)\n                        placeholders = ', '.join(['%s'] * len(values))\n                        cursor.execute(f'INSERT INTO `{table}` ({column_sql}) VALUES ({placeholders})', tuple(values))\n                        new_id = cursor.lastrowid if table == 'Enrollments' else values[0]\n                        connection.commit()\n                        flash(f'{table} record {new_id} added.', 'success')\n                        return redirect(url_for('edit', table=table, record_id=new_id))\n                    except ValueError as exc:\n                        connection.rollback()\n                        error = str(exc)\n                    except mysql.connector.IntegrityError as exc:\n                        connection.rollback()\n                        app.logger.exception('Insert constraint violation')\n                        error = ('That ID already exists. Choose an unused ID.' if exc.errno == 1062\n                                 else 'Cannot add record: check selected student/course and database constraints.')\n                    except mysql.connector.Error:\n                        connection.rollback()\n                        app.logger.exception('Insert failed')\n                        error = 'Could not add record. Check terminal details and INSERT permissions.'\n            finally:\n                cursor.close()\n    except Exception:\n        app.logger.exception('Could not load add-record form')\n        error = 'Could not connect or load form choices. Check the terminal.'\n    fields = list(spec['fields'])\n    if table != 'Enrollments':\n        fields.insert(0, (spec['pk'], 'number', None, True))\n    return render_template('add.html', table=table, fields=fields, values=values_in,\n                           students=students, courses=courses, error=error)\n\n"
TEMPLATE = '{% extends \'base.html\' %}{% block content %}<section class="form">\n<h2>Add {{ table }}</h2>\n{% if error %}<p class="error" role="alert">{{ error }}</p>{% endif %}\n{% if table == \'Enrollments\' %}<p>MySQL assigns the enrollment ID automatically.</p>{% else %}<p>Enter an unused ID. Student and course IDs are not automatically generated in your original schema.</p>{% endif %}\n<form method="post"><input type="hidden" name="csrf_token" value="{{ csrf_token() }}">\n{% for name,kind,limit,required in fields %}<label>{{ name }}{% if required %} (required){% endif %}\n{% if kind == \'student\' %}<select name="{{ name }}" required><option value="">Choose a student</option>{% for item in students %}<option value="{{ item.student_id }}" {% if values.get(name) == item.student_id|string %}selected{% endif %}>{{ item.student_id }} — {{ item.first_name or \'\' }} {{ item.last_name or \'\' }}</option>{% endfor %}</select>\n{% elif kind == \'course\' %}<select name="{{ name }}" required><option value="">Choose a course</option>{% for item in courses %}<option value="{{ item.course_id }}" {% if values.get(name) == item.course_id|string %}selected{% endif %}>{{ item.course_id }} — {{ item.course_name or \'\' }}</option>{% endfor %}</select>\n{% else %}<input type="{{ kind }}" name="{{ name }}" value="{{ values.get(name, \'\') }}" {% if required %}required{% endif %} {% if limit %}maxlength="{{ limit }}"{% endif %} {% if kind == \'number\' %}step="1" min="{{ 0 if name == \'credits\' else -2147483648 }}" max="2147483647"{% endif %} {% if kind == \'datetime-local\' %}step="1"{% endif %}>{% endif %}</label>{% endfor %}\n<button type="submit" {% if table == \'Enrollments\' and (not students or not courses) %}disabled{% endif %}>Add record to MySQL</button> <a href="{{ url_for(\'home\') }}">Cancel</a>\n{% if table == \'Enrollments\' and (not students or not courses) %}<p>Add at least one student and one course first.</p>{% endif %}\n</form></section>{% endblock %}'

def main():
    root = Path(__file__).resolve().parent
    app_file = root / 'app.py'
    index_file = root / 'templates' / 'index.html'
    if not app_file.exists() or not index_file.exists():
        raise SystemExit('Place this script inside your working college_dashboard folder first.')
    source = app_file.read_text(encoding='utf-8')
    index = index_file.read_text(encoding='utf-8')
    if '# ADD_RECORDS_V1' in source:
        raise SystemExit('Add-record upgrade is already installed. No files changed.')
    required = ['def spec_for(', 'def database(', 'CSRFProtect(app)', 'TABLES =']
    if not all(text in source for text in required):
        raise SystemExit('This script requires the previously supplied working college editor. No files changed.')
    tree = ast.parse(source)
    guards = [node for node in tree.body if isinstance(node, ast.If)
              and isinstance(node.test, ast.Compare)
              and isinstance(node.test.left, ast.Name) and node.test.left.id == '__name__']
    if len(guards) != 1:
        raise SystemExit('Could not identify the startup block. No files changed.')
    target = '<h2>{{ table.name }}</h2>'
    if target not in index:
        raise SystemExit('Dashboard template differs from expected version. No files changed.')
    lines = source.splitlines(keepends=True)
    position = guards[0].lineno - 1
    updated = ''.join(lines[:position]) + ROUTE + ''.join(lines[position:])
    compile(updated, str(app_file), 'exec')
    button = target + "\n<p><a class=\"button\" href=\"{{ url_for('add_record', table=table.name) }}\">Add new record</a></p>"
    updated_index = index.replace(target, button)
    from jinja2 import Environment
    for text in (TEMPLATE, updated_index):
        Environment().parse(text)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = root / ('backup_before_add_' + stamp)
    backup.mkdir()
    (backup / 'app.py').write_text(source, encoding='utf-8')
    (backup / 'index.html').write_text(index, encoding='utf-8')
    old_add = root / 'templates' / 'add.html'
    if old_add.exists():
        (backup / 'add.html').write_bytes(old_add.read_bytes())
    app_file.write_text(updated, encoding='utf-8')
    index_file.write_text(updated_index, encoding='utf-8')
    old_add.write_text(TEMPLATE, encoding='utf-8')
    print('Upgrade installed. Backup folder: ' + backup.name)
    print('Your .env and database were not modified. Restart app.py.')

if __name__ == '__main__':
    main()
