-- Create the database
CREATE DATABASE IF NOT EXISTS req_analysis_dashboard;

USE req_analysis_dashboard;

-- Create candidates table
CREATE TABLE IF NOT EXISTS candidates (
    candidate_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(15),
    resume_link VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
ALTER TABLE candidates
ADD COLUMN password VARCHAR(255);

-- Create recruiters table
CREATE TABLE IF NOT EXISTS recruiters (
    recruiter_id INT AUTO_INCREMENT PRIMARY KEY,
    recruiter_name VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(100)
);
ALTER TABLE recruiters
MODIFY COLUMN password VARCHAR(255);


-- Create jobs table
CREATE TABLE IF NOT EXISTS jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    job_title VARCHAR(100),
    description TEXT,
    recruiter_id INT,
    FOREIGN KEY (recruiter_id) REFERENCES recruiters(recruiter_id) ON DELETE CASCADE
);
ALTER TABLE jobs
ADD COLUMN recruiter_name VARCHAR(255);
ALTER TABLE jobs
ADD COLUMN requirements VARCHAR(255),
ADD COLUMN last_date DATE;
ALTER TABLE jobs ADD COLUMN status ENUM('open', 'closed', 'pending') DEFAULT 'open';

-- Create applications table
CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    job_id INT,
    status ENUM('applied', 'interviewing', 'hired', 'rejected') DEFAULT 'applied',
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
);

-- Create interview table
CREATE TABLE IF NOT EXISTS interviews (
    interview_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT,                -- Reference to the application
    interview_date DATETIME NOT NULL,  -- Date and time of the interview
    status ENUM('scheduled', 'completed', 'cancelled') DEFAULT 'scheduled',  -- Status of the interview
    feedback TEXT,                    -- Feedback from the interview (optional)
    FOREIGN KEY (application_id) REFERENCES applications(application_id) ON DELETE CASCADE  -- Foreign key constraint
);
ALTER TABLE interviews
DROP COLUMN feedback;


-- Stored Procedures for deleting candidates and recruiters

DELIMITER //

CREATE PROCEDURE DeleteCandidate(IN candidateId INT)
BEGIN
    DELETE FROM candidates WHERE candidate_id = candidateId;
END;
//

CREATE PROCEDURE DeleteRecruiter(IN recruiterId INT)
BEGIN
    DELETE FROM recruiters WHERE recruiter_id = recruiterId;
END;
//

DELIMITER ;



-- Trigger to update application status after interview update

DELIMITER //

CREATE TRIGGER update_application_status_after_interview_update
AFTER UPDATE ON interviews
FOR EACH ROW
BEGIN
    IF NEW.status = 'cancelled' THEN
        UPDATE applications
        SET status = 'rejected'
        WHERE application_id = NEW.application_id;
    END IF;
    -- If NEW.status = 'completed', no action is needed, so no ELSE block is necessary.
END//

DELIMITER ;

-- user Creation and assigning privileges

CREATE USER 'Admin'@'localhost' IDENTIFIED BY 'mainAdmin123';
GRANT ALL PRIVILEGES ON *.* TO 'Admin'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;

