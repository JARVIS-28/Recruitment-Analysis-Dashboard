from datetime import datetime
from flask import Flask, render_template, request, redirect, session, flash,url_for
import mysql.connector
import os
import bcrypt
from mysql.connector.errors import IntegrityError
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Function to connect to MySQL database
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",  
            password="ramani77",  
            database="req_analysis_dashboard"  
        )
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route('/')
def landing_page():
    return render_template('landing.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_password = request.form['admin-password']
        
        if admin_password == os.getenv('ADMIN_PASSWORD', 'mainAdmin123'):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Incorrect password. Please try again.', 'danger')
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin_logged_in' not in session:
        return redirect('admin_login')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        if 'delete_username' in request.form:
            # Handle deletion of sub-admin
            delete_username = request.form['delete_username']
            try:
                cursor.execute("REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@'localhost'", (delete_username,))
                cursor.execute("DROP USER %s@'localhost'", (delete_username,))
                conn.commit()
                flash(f'Sub-admin {delete_username} deleted successfully!', 'success')
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'Error deleting sub-admin: {err}', 'danger')

        elif 'revoke_username' in request.form:
            # Handle privilege revocation
            revoke_username = request.form['revoke_username']
            revoke_table = request.form['revoke_table']
            revoke_privileges = request.form.getlist('revoke_privileges')
            
            try:
                # Dynamically build REVOKE statement based on selected privileges
                if 'all' in revoke_privileges:
                    # Revoke all privileges on the specific table
                    revoke_query = f"REVOKE ALL PRIVILEGES ON {revoke_table} FROM %s@'localhost'"
                else:
                    # Revoke specific selected privileges
                    privileges_to_revoke = ', '.join(revoke_privileges)
                    revoke_query = f"REVOKE {privileges_to_revoke} ON {revoke_table} FROM %s@'localhost'"
                
                cursor.execute(revoke_query, (revoke_username,))
                conn.commit()
                flash(f'Privileges for {revoke_username} on {revoke_table} revoked successfully!', 'success')
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'Error revoking privileges: {err}', 'danger')

        else:
            #creation of sub-admin
            username = request.form['username']
            password = request.form['password']
            user_type = request.form['user_type']
            try:
                # Check if the user already exists
                cursor.execute("SELECT COUNT(*) AS count FROM mysql.user WHERE user = %s AND host = 'localhost'", (username,))
                result = cursor.fetchone()
                if result['count'] > 0:
                    flash(f'User {username} already exists.', 'danger')
                else:
                    cursor.execute("CREATE USER %s@'localhost' IDENTIFIED BY %s", (username, password))
                    if user_type == 'candidate_admin':
                        cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON candidates TO %s@'localhost'", (username,))
                    elif user_type == 'recruiter_admin':
                        cursor.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON recruiters TO %s@'localhost'", (username,))
                    conn.commit()
                    flash('Sub-admin created successfully!', 'success')
            except mysql.connector.Error as err:
                conn.rollback()
                flash(f'Error creating sub-admin: {err}', 'danger')
    # Fetch sub-admins created by the main admin for this particular database
    cursor.execute("SELECT user FROM mysql.user WHERE user LIKE 'subadmin%' AND host = 'localhost'")
    sub_admins = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin.html', sub_admins=sub_admins)


# Login function
@app.route('/login', methods=['GET', 'POST'])
def login():
    user_type = request.args.get('type')  # Check if it's 'candidate' or 'recruiter'

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        table = 'candidates' if user_type == 'candidate' else 'recruiters'
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Fetch the hashed password from the database
        cursor.execute(f'SELECT * FROM {table} WHERE email = %s', (email,))
        account = cursor.fetchone()
        
        # Use bcrypt.checkpw to compare password
        if account and bcrypt.checkpw(password.encode('utf-8'), account['password'].encode('utf-8')):
            session['loggedin'] = True
            session['user_id'] = account[f'{user_type}_id']
            session['user_type'] = user_type
            return redirect(f'/home_{user_type}')
        else:
            flash('Invalid credentials', 'danger')
        
        cursor.close()
        conn.close()

    return render_template('login.html', user_type=user_type)

# Candidate signup page
@app.route('/signup_candidate', methods=['GET', 'POST'])
def signup_candidate():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form['phone']
        resume_link = request.form['resume_link']  # Get the resume link

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO candidates (first_name, last_name, email, password, phone, resume_link) VALUES (%s, %s, %s, %s, %s, %s)',
                           (first_name, last_name, email, hashed_password.decode('utf-8'), phone, resume_link))
            conn.commit()
            flash('Candidate account created successfully!', 'success')
            return redirect('/login?type=candidate')
        except mysql.connector.IntegrityError as e:
            if 'email' in str(e):
                flash('Email is already in use. Please use a different email.', 'danger')
            else:
                flash('An error occurred while creating the account. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('signup_candidate.html')

# Recruiter signup page
@app.route('/signup_recruiter', methods=['GET', 'POST'])
def signup_recruiter():
    if request.method == 'POST':
        recruiter_name = request.form['recruiter_name']
        email = request.form['email']
        password = request.form['password']

        # Hash the password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO recruiters (recruiter_name, email, password) VALUES (%s, %s, %s)',
                           (recruiter_name, email, hashed_password.decode('utf-8')))
            conn.commit()
            flash('Recruiter account created successfully!', 'success')
            return redirect('/login?type=recruiter')
        except mysql.connector.IntegrityError as e:
            if 'email' in str(e):
                flash('Email is already in use. Please use a different email.', 'danger')
            else:
                flash('An error occurred while creating the account. Please try again.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('signup_recruiter.html')
# Home page for candidates
@app.route('/home_candidate', methods=['GET', 'POST'])
def home_candidate():
    if 'loggedin' not in session or session['user_type'] != 'candidate':
        return redirect('/login?type=candidate')
    
    candidate_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Update candidate profile logic
        email = request.form.get('email')
        phone = request.form.get('phone')
        resume_link = request.form.get('resume_link')

        # Only update the fields provided
        cursor.execute("""
            UPDATE candidates 
            SET email = COALESCE(%s, email), 
                phone = COALESCE(%s, phone), 
                resume_link = COALESCE(%s, resume_link) 
            WHERE candidate_id = %s
        """, (email, phone, resume_link, candidate_id))
        conn.commit()
        flash('Profile updated successfully!', 'success')

    # Fetch candidate information
    cursor.execute('SELECT * FROM candidates WHERE candidate_id = %s', (candidate_id,))
    candidate = cursor.fetchone()

    # Fetch available job postings
    cursor.execute('SELECT * FROM jobs')
    job_postings = cursor.fetchall()

    # Fetch applications made by the candidate
    cursor.execute("""
        SELECT a.application_id, j.job_title, a.status 
        FROM applications a
        JOIN jobs j ON a.job_id = j.job_id 
        WHERE a.candidate_id = %s
    """, (candidate_id,))
    applications = cursor.fetchall()

    # Fetch scheduled interviews
    cursor.execute("""
        SELECT i.interview_date, i.status, j.job_title 
        FROM interviews i
        JOIN applications a ON i.application_id = a.application_id
        JOIN jobs j ON a.job_id = j.job_id
        WHERE a.candidate_id = %s
    """, (candidate_id,))
    interviews = cursor.fetchall()

    cursor.close()
    conn.close()
     # Get the current date
    current_date = datetime.today().date()
    return render_template('home_candidate.html', candidate=candidate, job_postings=job_postings, applications=applications, interviews=interviews,current_date=current_date)

# Home page for recruiters
@app.route('/home_recruiter', methods=['GET', 'POST'])
def home_recruiter():
    if 'loggedin' not in session or session['user_type'] != 'recruiter':
        return redirect('/login?type=recruiter')

    recruiter_id = session['user_id']
    conn = get_db_connection()
    
    if request.method == 'POST':
        cursor = conn.cursor()
        
        # Check if the form is for adding a job or updating profile
        if 'job_title' in request.form:
            # Add new job posting logic
            job_title = request.form.get('job_title')
            description = request.form.get('description')
            requirements = request.form.get('requirements')
            last_date = request.form.get('last_date')
            
            last_date_obj = datetime.strptime(last_date, '%Y-%m-%d')
            current_date = datetime.now().date()

            # Check if the last_date is not in the past
            if last_date_obj.date() < current_date:
                flash('The last date to apply cannot be in the past. Please select a valid date.', 'error')
                cursor.close()
                conn.close()
                return redirect('/home_recruiter')
            cursor.execute('SELECT * FROM jobs WHERE job_title = %s AND recruiter_id = %s AND last_date = %s', 
                       (job_title, recruiter_id, last_date))
            existing_job = cursor.fetchone()
        
            if existing_job:
                flash('A job posting with the same title and last date already exists. Please update it instead.', 'danger')
                return redirect('/home_recruiter')
            # Fetch the recruiter name from the recruiters table
            cursor.execute('SELECT recruiter_name FROM recruiters WHERE recruiter_id = %s', (recruiter_id,))
            recruiter = cursor.fetchone()  # This will return a tuple
            recruiter_name = recruiter[0] if recruiter else "Unknown Recruiter"  # Accessing as tuple

            # Insert job posting with recruiter name included
            cursor.execute(""" 
                INSERT INTO jobs (job_title, description, recruiter_id, recruiter_name, requirements, last_date) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (job_title, description, recruiter_id, recruiter_name, requirements, last_date))
            conn.commit()
            flash('Job posting added successfully!', 'success')

        elif 'email' in request.form:
            # Update email only
            email = request.form['email']
            cursor.execute("""
                UPDATE recruiters SET email = %s WHERE recruiter_id = %s
            """, (email, recruiter_id))
            conn.commit()
            flash('Email updated successfully!', 'success')

        cursor.close()
        return redirect('/home_recruiter')
        
    # Retrieve recruiter details for the profile
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM recruiters WHERE recruiter_id = %s', (recruiter_id,))
    recruiter = cursor.fetchone()

    # Fetch all job postings by the recruiter along with applications and candidates data
    cursor.execute("""
        SELECT jobs.job_id, jobs.job_title, jobs.description, jobs.recruiter_name, jobs.requirements, jobs.last_date, 
               applications.application_id, applications.status
        FROM jobs
        LEFT JOIN applications ON jobs.job_id = applications.job_id
        LEFT JOIN candidates ON applications.candidate_id = candidates.candidate_id
        WHERE jobs.recruiter_id = %s
    """, (recruiter_id,))
    
    job_postings = cursor.fetchall()  # This will fetch all job postings along with the corresponding applications

    for job in job_postings:
        if job['last_date'] < datetime.now().date():
            job['status'] = 'closed'
        else:
            job['status'] = 'open'
    # Fetch upcoming interviews for the recruiter
    cursor.execute("""
        SELECT interviews.interview_id, candidates.first_name, candidates.last_name, jobs.job_title, interviews.interview_date, interviews.status
        FROM interviews
        JOIN applications ON interviews.application_id = applications.application_id
        JOIN jobs ON applications.job_id = jobs.job_id
        JOIN candidates ON applications.candidate_id = candidates.candidate_id
        WHERE jobs.recruiter_id = %s AND DATE(interviews.interview_date) >= CURDATE()
        ORDER BY interviews.interview_date ASC
    """, (recruiter_id,))
    
    upcoming_interviews = cursor.fetchall()

    cursor.close()
    conn.close()
    
    return render_template('home_recruiter.html', recruiter=recruiter, job_postings=job_postings, upcoming_interviews=upcoming_interviews)


#update job status

def update_job_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the current date
    current_date = datetime.now().date()
    
    # Update job status to 'closed' where the last date to apply has passed
    cursor.execute("""
        UPDATE job_postings
        SET status = 'closed'
        WHERE last_date_to_apply < %s AND status = 'open'
    """, (current_date,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Job status updated successfully!', 'success')
    return redirect('/home_recruiter')
    
    # update inteview status
@app.route('/update_interview_status', methods=['POST'])
def update_interview_status():
    interview_id = request.form['interview_id']
    new_status = request.form['status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Update the interview status
    cursor.execute('UPDATE interviews SET status = %s WHERE interview_id = %s', (new_status, interview_id))
    
    #if new_status == 'cancelled':
        #cursor.execute('SELECT application_id FROM interviews WHERE interview_id = %s', (interview_id,))
        #application_id = cursor.fetchone()[0]
        #cursor.execute('UPDATE applications SET status = %s WHERE application_id = %s', ('rejected', application_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Interview status updated successfully!', 'success')
    return redirect('/home_recruiter')

    #update application status
@app.route('/update_application_status', methods=['POST'])
def update_application_status():
    interview_id = request.form['interview_id']
    application_status = request.form['application_status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT application_id FROM interviews WHERE interview_id = %s', (interview_id,))
    application_id = cursor.fetchone()[0]
    
    # Update the application status
    cursor.execute('UPDATE applications SET status = %s WHERE application_id = %s', (application_status, application_id))
    
    # Update the interview status to 'completed'
    cursor.execute('UPDATE interviews SET status = %s WHERE interview_id = %s', ('completed', interview_id))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Application status updated successfully!', 'success')
    return redirect('/home_recruiter')


# Route for applying to a job (Candidate submits job application)
@app.route('/apply_job', methods=['POST'])
def apply_job():
    if 'loggedin' not in session or session['user_type'] != 'candidate':
        return redirect('/login?type=candidate')

    job_id = request.form['job_id']
    candidate_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Ensure the job ID exists before inserting the application
    cursor.execute('SELECT * FROM jobs WHERE job_id = %s', (job_id,))
    job = cursor.fetchone()

    if not job:
        flash('Job not found.', 'danger')
        return redirect('/home_candidate')
    last_date = job['last_date']
    if last_date and last_date < datetime.now().date():
        flash('The application period for this job is over.', 'danger')
        cursor.close()
        conn.close()
        return redirect('/home_candidate')
    # Insert application for candidate
    cursor.execute("""
        INSERT INTO applications (candidate_id, job_id, status) 
        VALUES (%s, %s, 'applied')
    """, (candidate_id, job_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Application submitted successfully!', 'success')
    return redirect('/home_candidate')

@app.route('/view_applicants/<int:job_id>')
def view_applicants(job_id):
    # Check if the recruiter is logged in
    if 'loggedin' not in session or session['user_type'] != 'recruiter':
        return redirect('/login?type=recruiter')

    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch the job details (optional, if you want to display them on the page)
    cursor.execute("""
        SELECT job_title
        FROM jobs
        WHERE job_id = %s
    """, (job_id,))
    job = cursor.fetchone()

    # Fetch applicants for the specified job, including application_id
    cursor.execute("""
        SELECT a.application_id, c.candidate_id, c.first_name, c.last_name, c.email, c.phone, c.resume_link, a.status
        FROM applications a
        JOIN candidates c ON a.candidate_id = c.candidate_id
        WHERE a.job_id = %s
    """, (job_id,))
    applicants = cursor.fetchall()

    cursor.close()
    conn.close()

    # Check if there are no applicants
    if not applicants:
        flash('No applicants found for this job.', 'info')

    # Render the 'view_applicants.html' template, passing job and applicant details
    return render_template('view_applicants.html', job=job, applicants=applicants)

@app.route('/schedule_interview', methods=['POST'])
def schedule_interview():
    if 'loggedin' not in session or session['user_type'] != 'recruiter':
        return redirect('/login?type=recruiter')

    application_id = request.form['application_id']
    interview_date = request.form['interview_date']

    interview_datetime = datetime.strptime(interview_date, '%Y-%m-%dT%H:%M')
    if interview_datetime < datetime.now():
        flash('Cannot schedule an interview for a past date.', 'danger')
        return redirect('/home_recruiter')
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Insert interview details into the database
        query = """
        INSERT INTO interviews (application_id, interview_date, status)
        VALUES (%s, %s, 'scheduled')
        """
        cursor.execute(query, (application_id, interview_date))

        # Update the application status to 'interviewing'
        update_query = """
        UPDATE applications
        SET status = 'interviewing'
        WHERE application_id = %s
        """
        cursor.execute(update_query, (application_id,))

        conn.commit()
        flash('Interview scheduled successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Error scheduling interview: {e}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect('/home_recruiter')
    
    
# Route for candidate profile deletion
@app.route('/delete_candidate_profile', methods=['POST'])
def delete_candidate_profile():
    if 'loggedin' not in session or session['user_type'] != 'candidate':
        return redirect('/login?type=candidate')
    
    candidate_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the candidate profile from the database
    cursor.callproc('DeleteCandidate', (candidate_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    session.clear()  # Clear session after deletion
    flash('Your profile has been deleted successfully!', 'success')
    return redirect('/')


# Route for recruiter profile deletion
@app.route('/delete_recruiter_profile', methods=['POST'])
def delete_recruiter_profile():
    if 'loggedin' not in session or session['user_type'] != 'recruiter':
        return redirect('/login?type=recruiter')
    
    recruiter_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete the recruiter profile from the database
    cursor.callproc('DeleteRecruiter', (recruiter_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    session.clear()  # Clear session after deletion
    flash('Your profile has been deleted successfully!', 'success')
    return redirect('/')    
    
# Route for viewing the dashboard (for candidates)
@app.route('/dashboard_candidate')
def dash_candidate():
    if 'loggedin' not in session or session['user_type'] != 'candidate':
        return redirect('/login?type=candidate')

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Query to fetch candidate's total applications, interviews, and interview statuses
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM applications WHERE candidate_id = %s) AS total_applications,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.candidate_id = %s) AS total_interviews,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.candidate_id = %s AND i.status = 'completed') AS total_completed_interviews,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.candidate_id = %s AND i.status = 'cancelled') AS total_cancelled_interviews,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.candidate_id = %s AND i.status = 'scheduled') AS total_scheduled_interviews
    """, (user_id, user_id, user_id, user_id, user_id))
    
    stats = cursor.fetchone()

    # Calculate additional statistics
    if stats['total_applications'] > 0:
        stats['total_applications_percentage'] = (stats['total_applications'] / stats['total_applications']) * 100  # Example for display, adjust as needed
    else:
        stats['total_applications_percentage'] = 0

    if stats['total_interviews'] > 0:
        stats['total_interviews_percentage'] = (stats['total_interviews'] / stats['total_interviews']) * 100  # Example for display, adjust as needed
    else:
        stats['total_interviews_percentage'] = 0

    # Calculate ratios for completed, cancelled, and scheduled interviews
    total_interview_count = (stats['total_completed_interviews'] + 
                             stats['total_cancelled_interviews'] + 
                             stats['total_scheduled_interviews'])

    if total_interview_count > 0:
        stats['completed_ratio'] = (stats['total_completed_interviews'] / total_interview_count) * 100
        stats['cancelled_ratio'] = (stats['total_cancelled_interviews'] / total_interview_count) * 100
        stats['scheduled_ratio'] = (stats['total_scheduled_interviews'] / total_interview_count) * 100
    else:
        stats['completed_ratio'] = 0
        stats['cancelled_ratio'] = 0
        stats['scheduled_ratio'] = 0

    cursor.close()
    conn.close()

    return render_template('dashboard_candidate.html', stats=stats, user_type='candidate')

# Route for viewing the dashboard (for recruiters)

@app.route('/dashboard_recruiter')
def dashboard_recruiter():
    if 'loggedin' not in session or session['user_type'] != 'recruiter':
        return redirect('/login?type=recruiter')

    recruiter_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch statistics
    cursor.execute("""
        SELECT 
            (SELECT COUNT(*) FROM jobs WHERE recruiter_id = %s) AS total_jobs,
            (SELECT COUNT(*) FROM applications WHERE job_id IN (SELECT job_id FROM jobs WHERE recruiter_id = %s)) AS total_applications,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.job_id IN (SELECT job_id FROM jobs WHERE recruiter_id = %s) AND i.status = 'completed') AS completed_interviews,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.job_id IN (SELECT job_id FROM jobs WHERE recruiter_id = %s)) AS total_interviews,
            (SELECT COUNT(*) FROM interviews i 
             JOIN applications a ON i.application_id = a.application_id 
             WHERE a.job_id IN (SELECT job_id FROM jobs WHERE recruiter_id = %s) AND i.status = 'hired') AS successful_interviews
    """, (recruiter_id, recruiter_id, recruiter_id, recruiter_id, recruiter_id))
    
    stats = cursor.fetchone()

    if stats['total_applications'] > 0:
        stats['success_rate'] = (stats['successful_interviews'] / stats['total_interviews'] * 100) if stats['total_interviews'] > 0 else 0
        stats['total_jobs_percentage'] = (stats['total_jobs'] / stats['total_applications']) * 100  # Adjusted to be a percentage of total applications
        stats['total_applications_percentage'] = (stats['total_applications'] / stats['total_applications']) * 100  # This will always be 100%
        stats['total_interviews_percentage'] = (stats['total_interviews'] / stats['total_applications']) * 100  # Adjusted to be a percentage of total applications
        
        stats['avg_applications_per_job'] = (stats['total_applications'] / stats['total_jobs']) if stats['total_jobs'] > 0 else 0
    else:
        stats['success_rate'] = 0
        stats['total_jobs_percentage'] = 0
        stats['total_applications_percentage'] = 0
        stats['total_interviews_percentage'] = 0

    # Fetch job postings by status
    cursor.execute("""
        SELECT status, COUNT(*) AS count
        FROM jobs
        WHERE recruiter_id = %s
        GROUP BY status
    """, (recruiter_id,))
    job_postings_status = cursor.fetchall()

    job_postings_labels = [row['status'] for row in job_postings_status]
    job_postings_counts = [row['count'] for row in job_postings_status]

    # Fetch applications by status
    cursor.execute("""
        SELECT status, COUNT(*) AS count
        FROM applications
        WHERE job_id IN (SELECT job_id FROM jobs WHERE recruiter_id = %s)
        GROUP BY status
    """, (recruiter_id,))
    applications_status = cursor.fetchall()

    applications_labels = [row['status'] for row in applications_status]
    applications_counts = [row['count'] for row in applications_status]

    # Fetch recent job postings by the recruiter
    cursor.execute("""
        SELECT job_id, job_title, description, last_date 
        FROM jobs 
        WHERE recruiter_id = %s 
        ORDER BY last_date DESC 
        LIMIT 5
    """, (recruiter_id,))
    recent_jobs = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('dashboard_recruiter.html', stats=stats, 
                           job_postings_labels=job_postings_labels, job_postings_counts=job_postings_counts,
                           applications_labels=applications_labels, applications_counts=applications_counts,
                           recent_jobs=recent_jobs, user_type='recruiter')

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
