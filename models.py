from dataclasses import dataclass, asdict
from datetime import datetime

class Record:
    def to_record(self):
        return asdict(self)

@dataclass
class Student(Record):
    student_id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    degree_path: str = ''
    credits: int | None = None
    college_level: str | None = None
    def __post_init__(self):
        if not self.degree_path or not self.degree_path.strip():
            raise ValueError('degree_path is required.')
        if self.credits is not None and self.credits < 0:
            raise ValueError('credits cannot be negative.')
    def full_name(self):
        return ' '.join(v for v in (self.first_name, self.last_name) if v)

@dataclass
class Course(Record):
    course_id: int
    course_name: str | None = None
    course_code: str | None = None
    professor: str | None = None
    created_at: datetime | None = None
    def display_name(self):
        return self.course_name or f'Course {self.course_id}'

@dataclass
class Enrollment(Record):
    enrollment_id: int | None = None
    student_id: int | None = None
    course_id: int | None = None
    def __post_init__(self):
        if self.student_id is None or self.course_id is None:
            raise ValueError('Student and course are required.')

MODELS = {'Students': Student, 'Courses': Course, 'Enrollments': Enrollment}

class CollegeRepository:
    def __init__(self, connection):
        self.connection = connection
    def all(self, table):
        model = MODELS[table]
        pk = {'Students':'student_id','Courses':'course_id','Enrollments':'enrollment_id'}[table]
        columns = ', '.join('`'+name+'`' for name in model.__dataclass_fields__)
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(f'SELECT {columns} FROM `{table}` ORDER BY `{pk}`')
            return [model(**row) for row in cursor.fetchall()]
        finally:
            cursor.close()
    @staticmethod
    def create(cursor, table, record):
        if table not in MODELS or not isinstance(record, MODELS[table]):
            raise ValueError('Invalid record type.')
        data = record.to_record()
        if table == 'Enrollments':
            data.pop('enrollment_id')
        columns = ', '.join('`'+name+'`' for name in data)
        placeholders = ', '.join(['%s']*len(data))
        cursor.execute(f'INSERT INTO `{table}` ({columns}) VALUES ({placeholders})', tuple(data.values()))
    @staticmethod
    def update(cursor, table, record):
        if table not in MODELS or not isinstance(record, MODELS[table]):
            raise ValueError('Invalid record type.')
        pk = {'Students':'student_id','Courses':'course_id','Enrollments':'enrollment_id'}[table]
        data = record.to_record()
        record_id = data.pop(pk)
        assignments = ', '.join('`'+name+'` = %s' for name in data)
        cursor.execute(f'UPDATE `{table}` SET {assignments} WHERE `{pk}` = %s', tuple(data.values())+(record_id,))
