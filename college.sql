DROP TABLE IF EXISTS Enrollments;
DROP TABLE IF EXISTS Courses;
DROP TABLE IF EXISTS Students;

CREATE TABLE Students (
    student_id INT NOT NULL PRIMARY KEY,
    first_name VARCHAR(20),
    last_name VARCHAR(20),
    email VARCHAR(50),
    degree_path VARCHAR(50) NOT NULL,
    credits INT,
    college_level VARCHAR(20) NULL
);

CREATE TABLE Courses (
    course_id INT PRIMARY KEY,
    course_name VARCHAR(50),
    course_code VARCHAR(20),
    professor VARCHAR(50),
    created_at DATETIME
);

CREATE TABLE Enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    course_id INT NOT NULL,
    FOREIGN KEY (student_id) 
        REFERENCES Students (student_id) 
        ON DELETE CASCADE,
    FOREIGN KEY (course_id) 
        REFERENCES Courses (course_id) 
        ON DELETE CASCADE
);
    
    




