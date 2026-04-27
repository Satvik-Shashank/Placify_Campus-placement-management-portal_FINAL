# =============================================================================
# PLACIFY – CAMPUS PLACEMENT MANAGEMENT SYSTEM
# File: app.py
# =============================================================================

import os
import json
from functools import wraps
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import get_config
from db import execute_query, call_procedure, call_procedure_with_out_params

# =============================================================================
# APP INIT
# =============================================================================

app = Flask(__name__)
config = get_config()
app.config.from_object(config)
app.secret_key = config.SECRET_KEY

os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

# =============================================================================
# TEMPLATE FILTERS
# =============================================================================

@app.template_filter('fmt_date')
def fmt_date(value):
    if value is None:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime('%d %b %Y')
    return str(value)

@app.template_filter('fmt_datetime')
def fmt_datetime(value):
    if value is None:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime('%d %b %Y, %H:%M')
    return str(value)

@app.template_filter('fmt_ctc')
def fmt_ctc(value):
    if value is None:
        return '—'
    return f'₹{float(value):.2f} LPA'

@app.template_filter('parse_json')
def parse_json(value):
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return []
    return []

# =============================================================================
# AUTH DECORATORS
# =============================================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def student_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Student access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def company_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'company':
            flash('Recruiter access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# AUTH ROUTES
# =============================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        if session['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif session['role'] == 'company':
            return redirect(url_for('company_dashboard'))
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('auth/login.html')

        result = execute_query(
            "SELECT user_id, email, password_hash, role, is_active FROM users WHERE email = %s",
            (email,), fetch_one=True
        )

        if not result['success'] or not result['data']:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        user = result['data']
        if not user['is_active']:
            flash('Account deactivated. Contact admin.', 'warning')
            return render_template('auth/login.html')

        try:
            is_valid = check_password_hash(user['password_hash'], password)
        except Exception:
            is_valid = False

        if not is_valid:
            flash('Invalid email or password.', 'danger')
            return render_template('auth/login.html')

        execute_query("UPDATE users SET last_login = NOW() WHERE user_id = %s",
                      (user['user_id'],), fetch=False)

        session.permanent = True
        session['user_id'] = user['user_id']
        session['role']    = user['role']
        session['email']   = user['email']

        if user['role'] == 'student':
            s = execute_query(
                "SELECT student_id, name, department FROM students WHERE user_id = %s",
                (user['user_id'],), fetch_one=True
            )
            if s['success'] and s['data']:
                session['student_id']  = s['data']['student_id']
                session['name']        = s['data']['name']
                session['department']  = s['data']['department']
            return redirect(url_for('student_dashboard'))
            
        elif user['role'] == 'company':
            c = execute_query(
                """SELECT c.company_id, c.name FROM companies c 
                   JOIN users u ON c.company_id = u.company_id 
                   WHERE u.user_id = %s""",
                (user['user_id'],), fetch_one=True
            )
            if c['success'] and c['data']:
                session['company_id'] = c['data']['company_id']
                session['name']       = c['data']['name'] + ' HR'
            else:
                session['name'] = 'Recruiter'
            return redirect(url_for('company_dashboard'))

        session['name'] = 'Administrator'
        return redirect(url_for('admin_dashboard'))

    return render_template('auth/login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()
        roll_num = request.form.get('roll_number', '').strip()

        if not all([name, email, password, department, roll_num]):
            flash('All fields are required.', 'danger')
            return render_template('auth/register.html')

        # Check if email exists
        res = execute_query("SELECT user_id FROM users WHERE email = %s", (email,), fetch_one=True)
        if res['success'] and res['data']:
            flash('Email already registered. Try logging in.', 'danger')
            return render_template('auth/register.html')

        try:
            pw_hash = generate_password_hash(password)
            user_res = execute_query(
                "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'student')",
                (email, pw_hash), fetch=False
            )
            
            if user_res['success']:
                uid = user_res['lastrowid']
                # Create basic student record
                student_res = execute_query(
                    """INSERT INTO students (user_id, roll_number, name, email, department, batch_year, cgpa, backlogs)
                       VALUES (%s, %s, %s, %s, %s, YEAR(CURDATE()), 0.0, 0)""",
                    (uid, roll_num, name, email, department), fetch=False
                )
                
                if student_res['success']:
                    flash('Account created successfully! You can now log in.', 'success')
                    return redirect(url_for('login'))
                else:
                    # rollback users
                    execute_query("DELETE FROM users WHERE user_id = %s", (uid,), fetch=False)
                    flash('Failed to create student profile.', 'danger')
            else:
                flash('Database error during registration.', 'danger')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('auth/register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out.', 'info')
    return redirect(url_for('login'))

# =============================================================================
# STUDENT ROUTES
# =============================================================================

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    sid = session['student_id']

    dash = execute_query("SELECT * FROM vw_student_dashboard WHERE student_id = %s",
                         (sid,), fetch_one=True)
    student = dash['data'] if dash['success'] else {}

    drives_q = execute_query(
        """SELECT c.company_id, c.name, c.job_role, c.ctc_lpa, c.visit_date, c.is_dream,
                  e.min_cgpa, DATEDIFF(c.registration_deadline, NOW()) AS days_left
           FROM companies c JOIN eligibility_criteria e ON c.company_id = e.company_id
           WHERE c.status = 'upcoming' AND c.registration_deadline > NOW()
           ORDER BY c.visit_date ASC LIMIT 5"""
    )
    upcoming = drives_q['data'] if drives_q['success'] else []

    apps_q = execute_query(
        """SELECT a.application_id, c.name AS company_name, c.job_role, a.status, a.applied_at
           FROM applications a JOIN companies c ON a.company_id = c.company_id
           WHERE a.student_id = %s ORDER BY a.applied_at DESC LIMIT 5""",
        (sid,)
    )
    recent_apps = apps_q['data'] if apps_q['success'] else []

    offers_q = execute_query(
        """SELECT o.offer_id, c.name AS company_name, o.offered_ctc, o.status,
                  o.acceptance_deadline
           FROM offers o
           JOIN applications a ON o.application_id = a.application_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE a.student_id = %s AND o.status = 'pending'
           ORDER BY o.acceptance_deadline ASC""",
        (sid,)
    )
    pending_offers = offers_q['data'] if offers_q['success'] else []

    return render_template('student/dashboard.html',
                           student=student, upcoming=upcoming,
                           recent_apps=recent_apps, pending_offers=pending_offers,
                           now=datetime.now())


@app.route('/student/profile', methods=['GET', 'POST'])
@student_required
def student_profile():
    sid = session['student_id']

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'upload_resume':
            f = request.files.get('resume')
            if f and f.filename:
                ext = f.filename.rsplit('.', 1)[-1].lower()
                if ext in config.ALLOWED_EXTENSIONS:
                    fname = secure_filename(f"resume_{sid}.{ext}")
                    f.save(os.path.join(config.UPLOAD_FOLDER, fname))
                    execute_query("UPDATE students SET resume_path = %s WHERE student_id = %s",
                                  (fname, sid), fetch=False)
                    flash('Resume uploaded successfully.', 'success')
                else:
                    flash('Only PDF, DOC, DOCX files allowed.', 'danger')

        elif action == 'add_skill':
            skill_id    = request.form.get('skill_id')
            proficiency = request.form.get('proficiency')
            if skill_id and proficiency:
                r = execute_query(
                    "INSERT IGNORE INTO student_skills (student_id, skill_id, proficiency) VALUES (%s,%s,%s)",
                    (sid, skill_id, proficiency), fetch=False
                )
                flash('Skill added.' if r['success'] else 'Skill already exists.', 'success' if r['success'] else 'warning')

        elif action == 'remove_skill':
            ss_id = request.form.get('student_skill_id')
            execute_query("DELETE FROM student_skills WHERE student_skill_id = %s AND student_id = %s",
                          (ss_id, sid), fetch=False)
            flash('Skill removed.', 'info')

        return redirect(url_for('student_profile'))

    student_r = execute_query("SELECT * FROM students WHERE student_id = %s", (sid,), fetch_one=True)
    student   = student_r['data'] if student_r['success'] else {}

    skills_r  = execute_query(
        """SELECT ss.student_skill_id, sk.skill_name, sk.category, ss.proficiency
           FROM student_skills ss JOIN skills sk ON ss.skill_id = sk.skill_id
           WHERE ss.student_id = %s ORDER BY sk.category, sk.skill_name""",
        (sid,)
    )
    skills = skills_r['data'] if skills_r['success'] else []

    all_skills_r = execute_query("SELECT skill_id, skill_name, category FROM skills ORDER BY category, skill_name")
    all_skills   = all_skills_r['data'] if all_skills_r['success'] else []

    return render_template('student/profile.html',
                           student=student, skills=skills, all_skills=all_skills)


@app.route('/student/companies')
@student_required
def student_companies():
    sid = session['student_id']

    # Uses stored procedure with CURSOR (DBMS concept visible to faculty)
    result = call_procedure('sp_get_eligible_companies', args=(sid,))
    companies = result['data'] if result['success'] else []

    if not result['success']:
        fb = execute_query(
            """SELECT c.company_id, c.name AS company_name, c.ctc_lpa, c.is_dream,
                      c.visit_date, c.registration_deadline, 'Eligible' AS eligibility_status
               FROM companies c JOIN eligibility_criteria e ON c.company_id = e.company_id
               WHERE c.status = 'upcoming' AND c.registration_deadline > NOW()
               ORDER BY c.visit_date"""
        )
        companies = fb['data'] if fb['success'] else []

    # Know which ones the student has already applied
    applied_r = execute_query(
        "SELECT company_id FROM applications WHERE student_id = %s", (sid,)
    )
    applied_ids = {r['company_id'] for r in (applied_r['data'] or [])} if applied_r['success'] else set()

    return render_template('student/companies.html',
                           companies=companies, applied_ids=applied_ids)


@app.route('/student/companies/<int:company_id>/apply', methods=['POST'])
@student_required
def student_apply(company_id):
    sid = session['student_id']
    result = call_procedure_with_out_params(
        'sp_apply_for_company', in_args=(sid, company_id), out_param_count=2
    )
    if result['success'] and result.get('out_params'):
        msg = result['out_params'][1] or 'Applied successfully!'
        flash(msg, 'success')
    else:
        flash(result.get('error', 'Application failed. Check your eligibility.'), 'danger')
    return redirect(url_for('student_companies'))


@app.route('/student/applications')
@student_required
def student_applications():
    sid = session['student_id']
    result = execute_query(
        """SELECT a.application_id, c.name AS company_name, c.job_role, c.ctc_lpa,
                  c.is_dream, a.status, a.applied_at,
                  o.offer_id, o.offered_ctc, o.status AS offer_status, o.acceptance_deadline,
                  (SELECT COUNT(*) FROM round_results rr
                   JOIN rounds r2 ON rr.round_id = r2.round_id
                   WHERE rr.application_id = a.application_id AND rr.status = 'shortlisted')
                  AS rounds_cleared
           FROM applications a
           JOIN companies c ON a.company_id = c.company_id
           LEFT JOIN offers o ON a.application_id = o.application_id
           WHERE a.student_id = %s
           ORDER BY a.applied_at DESC""",
        (sid,)
    )
    applications = result['data'] if result['success'] else []
    return render_template('student/applications.html', applications=applications)


@app.route('/student/applications/<int:app_id>/withdraw', methods=['POST'])
@student_required
def student_withdraw(app_id):
    sid = session['student_id']
    check = execute_query(
        "SELECT application_id FROM applications WHERE application_id = %s AND student_id = %s",
        (app_id, sid), fetch_one=True
    )
    if not check['success'] or not check['data']:
        flash('Application not found.', 'danger')
        return redirect(url_for('student_applications'))

    result = call_procedure_with_out_params(
        'sp_withdraw_application', in_args=(app_id,), out_param_count=2
    )
    if result['success']:
        flash(result['out_params'][1] if result.get('out_params') else 'Application withdrawn.', 'success')
    else:
        flash(result.get('error', 'Could not withdraw.'), 'danger')
    return redirect(url_for('student_applications'))


@app.route('/student/rounds')
@student_required
def student_rounds():
    sid = session['student_id']
    result = execute_query(
        """SELECT r.round_name, r.round_type, r.round_number, r.scheduled_date,
                  c.name AS company_name, rr.status AS result_status,
                  rr.score, rr.feedback, rr.attended, a.application_id
           FROM round_results rr
           JOIN rounds r ON rr.round_id = r.round_id
           JOIN applications a ON rr.application_id = a.application_id
           JOIN companies c ON r.company_id = c.company_id
           WHERE a.student_id = %s
           ORDER BY c.name, r.round_number""",
        (sid,)
    )
    rounds = result['data'] if result['success'] else []
    return render_template('student/rounds.html', rounds=rounds)


@app.route('/student/offers')
@student_required
def student_offers():
    sid = session['student_id']
    result = execute_query(
        """SELECT o.offer_id, o.offered_ctc, o.offered_role, o.job_location,
                  o.joining_date, o.status, o.acceptance_deadline, o.accepted_at,
                  c.name AS company_name, c.company_type, c.is_dream
           FROM offers o
           JOIN applications a ON o.application_id = a.application_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE a.student_id = %s
           ORDER BY o.created_at DESC""",
        (sid,)
    )
    offers = result['data'] if result['success'] else []
    return render_template('student/offers.html', offers=offers)


@app.route('/student/offers/<int:offer_id>/accept', methods=['POST'])
@student_required
def student_accept_offer(offer_id):
    result = call_procedure_with_out_params(
        'sp_accept_offer', in_args=(offer_id,), out_param_count=2
    )
    if result['success']:
        flash(result['out_params'][1] if result.get('out_params') else 'Offer accepted! Congratulations! 🎉', 'success')
    else:
        flash(result.get('error', 'Could not accept offer.'), 'danger')
    return redirect(url_for('student_offers'))


@app.route('/student/offers/<int:offer_id>/decline', methods=['POST'])
@student_required
def student_decline_offer(offer_id):
    result = call_procedure_with_out_params(
        'sp_decline_offer', in_args=(offer_id,), out_param_count=2
    )
    flash('Offer declined.' if result['success'] else result.get('error', 'Could not decline.'),
          'info' if result['success'] else 'danger')
    return redirect(url_for('student_offers'))

# =============================================================================
# ADMIN ROUTES
# =============================================================================

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    def scalar(q, p=None):
        r = execute_query(q, p, fetch_one=True)
        return r['data']['v'] if r['success'] and r['data'] else 0

    stats = {
        'total_students':   scalar("SELECT COUNT(*) AS v FROM students"),
        'placed_students':  scalar("SELECT COUNT(*) AS v FROM students WHERE is_placed = TRUE"),
        'active_companies': scalar("SELECT COUNT(*) AS v FROM companies WHERE status IN ('upcoming','ongoing')"),
        'total_applications': scalar("SELECT COUNT(*) AS v FROM applications"),
        'pending_offers':   scalar("SELECT COUNT(*) AS v FROM offers WHERE status = 'pending'"),
        'dream_placements': scalar("SELECT COUNT(*) AS v FROM students WHERE placement_type = 'dream'"),
    }
    stats['placement_pct'] = round(
        stats['placed_students'] / stats['total_students'] * 100
        if stats['total_students'] > 0 else 0, 1
    )
    pkg = execute_query("SELECT MAX(offered_ctc) AS v FROM offers WHERE status = 'accepted'", fetch_one=True)
    stats['highest_package'] = pkg['data']['v'] if pkg['success'] and pkg['data'] else 0

    dept_r     = execute_query("SELECT * FROM vw_department_placement_stats ORDER BY batch_year DESC, department")
    dept_stats = dept_r['data'] if dept_r['success'] else []

    audit_r   = execute_query(
        """SELECT al.action_type, al.table_name, al.created_at, u.email AS user_email
           FROM audit_logs al LEFT JOIN users u ON al.user_id = u.user_id
           ORDER BY al.created_at DESC LIMIT 8"""
    )
    recent_activity = audit_r['data'] if audit_r['success'] else []

    comp_r  = execute_query(
        """SELECT name, ctc_lpa, is_dream, status,
                  (SELECT COUNT(*) FROM applications WHERE company_id = companies.company_id) AS applicants
           FROM companies ORDER BY ctc_lpa DESC LIMIT 5"""
    )
    top_companies = comp_r['data'] if comp_r['success'] else []

    return render_template('admin/dashboard.html',
                           stats=stats, dept_stats=dept_stats,
                           recent_activity=recent_activity, top_companies=top_companies)


@app.route('/admin/students')
@admin_required
def admin_students():
    dept   = request.args.get('dept', '')
    search = request.args.get('search', '')
    placed = request.args.get('placed', '')

    q = """SELECT s.student_id, s.roll_number, s.name, s.email, s.department,
                  s.batch_year, s.cgpa, s.backlogs, s.is_placed, s.placement_type, s.phone
           FROM students s WHERE 1=1"""
    params = []
    if dept:   q += " AND s.department = %s";  params.append(dept)
    if search: q += " AND (s.name LIKE %s OR s.roll_number LIKE %s OR s.email LIKE %s)"; like = f"%{search}%"; params.extend([like,like,like])
    if placed == '1': q += " AND s.is_placed = TRUE"
    elif placed == '0': q += " AND s.is_placed = FALSE"
    q += " ORDER BY s.batch_year DESC, s.department, s.name"

    result   = execute_query(q, tuple(params) if params else None)
    students = result['data'] if result['success'] else []

    total_r  = execute_query("SELECT COUNT(*) AS v FROM students", fetch_one=True)
    placed_r = execute_query("SELECT COUNT(*) AS v FROM students WHERE is_placed = TRUE", fetch_one=True)

    return render_template('admin/students.html',
                           students=students, dept=dept, search=search, placed=placed,
                           total_students=total_r['data']['v'] if total_r['success'] else 0,
                           placed_students=placed_r['data']['v'] if placed_r['success'] else 0)


@app.route('/admin/students/add', methods=['POST'])
@admin_required
def admin_add_student():
    f = request.form
    email = f.get('email', '').strip().lower()
    if execute_query("SELECT user_id FROM users WHERE email = %s", (email,), fetch_one=True)['data']:
        flash('Email already registered.', 'danger')
        return redirect(url_for('admin_students'))
    try:
        pw_hash = generate_password_hash(f.get('password', 'Placify@123'))
        ur = execute_query("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'student')",
                           (email, pw_hash), fetch=False)
        if not ur['success']:
            flash('User creation failed.', 'danger')
            return redirect(url_for('admin_students'))
        uid = ur['lastrowid']
        sr = execute_query(
            """INSERT INTO students (user_id, roll_number, name, email, phone, gender, dob,
                                    department, batch_year, cgpa, backlogs)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (uid, f.get('roll_number'), f.get('name'), email, f.get('phone'),
             f.get('gender'), f.get('dob'), f.get('department'),
             f.get('batch_year'), f.get('cgpa'), f.get('backlogs', 0)),
            fetch=False
        )
        flash(f'Student {f.get("name")} added. Default password: {f.get("password","Placify@123")}',
              'success' if sr['success'] else 'danger')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_students'))


@app.route('/admin/students/<int:sid>/update', methods=['POST'])
@admin_required
def admin_update_student(sid):
    f = request.form
    r = execute_query(
        "UPDATE students SET cgpa=%s, backlogs=%s, is_placed=%s, placement_type=%s, updated_at=NOW() WHERE student_id=%s",
        (f.get('cgpa'), f.get('backlogs'),
         1 if f.get('is_placed') == '1' else 0,
         f.get('placement_type') or None, sid),
        fetch=False
    )
    flash('Student updated.' if r['success'] else 'Update failed.', 'success' if r['success'] else 'danger')
    return redirect(url_for('admin_students'))


@app.route('/admin/students/<int:sid>/delete', methods=['POST'])
@admin_required
def admin_delete_student(sid):
    s = execute_query("SELECT user_id FROM students WHERE student_id = %s", (sid,), fetch_one=True)
    if s['success'] and s['data']:
        execute_query("DELETE FROM users WHERE user_id = %s", (s['data']['user_id'],), fetch=False)
        flash('Student deleted.', 'success')
    else:
        flash('Student not found.', 'danger')
    return redirect(url_for('admin_students'))


@app.route('/admin/companies')
@admin_required
def admin_companies():
    status_f = request.args.get('status', '')
    search   = request.args.get('search', '')
    q = """SELECT c.company_id, c.name, c.job_role, c.ctc_lpa, c.is_dream, c.company_type,
                  c.visit_date, c.registration_deadline, c.status, c.industry,
                  (SELECT COUNT(*) FROM applications WHERE company_id = c.company_id) AS applicants
           FROM companies c WHERE 1=1"""
    params = []
    if status_f: q += " AND c.status = %s"; params.append(status_f)
    if search:   q += " AND (c.name LIKE %s OR c.job_role LIKE %s)"; like=f"%{search}%"; params.extend([like,like])
    q += " ORDER BY c.visit_date DESC"

    result    = execute_query(q, tuple(params) if params else None)
    companies = result['data'] if result['success'] else []
    return render_template('admin/companies.html',
                           companies=companies, status_f=status_f, search=search)


@app.route('/admin/companies/add', methods=['POST'])
@admin_required
def admin_add_company():
    f     = request.form
    depts = request.form.getlist('allowed_departments')
    try:
        cr = execute_query(
            """INSERT INTO companies (name, description, website, industry, company_type,
                                     job_role, job_description, job_location, ctc_lpa,
                                     is_dream, visit_date, registration_deadline, status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'upcoming')""",
            (f.get('name'), f.get('description'), f.get('website'), f.get('industry'),
             f.get('company_type'), f.get('job_role'), f.get('job_description'),
             f.get('job_location'), f.get('ctc_lpa'),
             1 if f.get('is_dream') else 0,
             f.get('visit_date'), f.get('registration_deadline')),
            fetch=False
        )
        if cr['success']:
            cid = cr['lastrowid']
            execute_query(
                """INSERT INTO eligibility_criteria
                   (company_id, min_cgpa, max_backlogs, allowed_departments, min_batch_year, max_batch_year)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (cid, f.get('min_cgpa', 0), f.get('max_backlogs', 0),
                 json.dumps(depts or ['CSE','ECE','IT','ME','CE','EEE']),
                 f.get('min_batch_year') or None, f.get('max_batch_year') or None),
                fetch=False
            )
            flash(f'Company "{f.get("name")}" added.', 'success')
        else:
            flash('Failed to add company.', 'danger')
    except Exception as e:
        flash(f'Error: {e}', 'danger')
    return redirect(url_for('admin_companies'))


@app.route('/admin/companies/<int:cid>/update', methods=['POST'])
@admin_required
def admin_update_company(cid):
    f = request.form
    r = execute_query(
        "UPDATE companies SET status=%s, visit_date=%s, registration_deadline=%s, updated_at=NOW() WHERE company_id=%s",
        (f.get('status'), f.get('visit_date'), f.get('registration_deadline'), cid),
        fetch=False
    )
    flash('Company updated.' if r['success'] else 'Update failed.', 'success' if r['success'] else 'danger')
    return redirect(url_for('admin_companies'))


@app.route('/admin/eligibility')
@admin_required
def admin_eligibility():
    result = execute_query(
        """SELECT c.company_id, c.name, c.ctc_lpa, c.is_dream, c.status,
                  e.criteria_id, e.min_cgpa, e.max_backlogs,
                  e.allowed_departments, e.min_batch_year, e.max_batch_year
           FROM companies c JOIN eligibility_criteria e ON c.company_id = e.company_id
           ORDER BY c.name"""
    )
    companies = result['data'] if result['success'] else []
    for c in companies:
        c['allowed_departments'] = parse_json(c.get('allowed_departments', '[]'))
    return render_template('admin/eligibility.html', companies=companies)


@app.route('/admin/eligibility/<int:cid>/update', methods=['POST'])
@admin_required
def admin_update_eligibility(cid):
    f     = request.form
    depts = request.form.getlist('allowed_departments')
    r = execute_query(
        """UPDATE eligibility_criteria
           SET min_cgpa=%s, max_backlogs=%s, allowed_departments=%s,
               min_batch_year=%s, max_batch_year=%s, updated_at=NOW()
           WHERE company_id=%s""",
        (f.get('min_cgpa'), f.get('max_backlogs'), json.dumps(depts or []),
         f.get('min_batch_year') or None, f.get('max_batch_year') or None, cid),
        fetch=False
    )
    flash('Eligibility rules updated.' if r['success'] else 'Update failed.',
          'success' if r['success'] else 'danger')
    return redirect(url_for('admin_eligibility'))


@app.route('/admin/applications')
@admin_required
def admin_applications():
    comp_f  = request.args.get('company', '')
    stat_f  = request.args.get('status', '')
    dept_f  = request.args.get('dept', '')

    q = """SELECT a.application_id, s.name AS student_name, s.roll_number,
                  s.department, s.cgpa, s.backlogs,
                  c.company_id, c.name AS company_name, c.is_dream,
                  a.status, a.applied_at
           FROM applications a
           JOIN students s ON a.student_id = s.student_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE 1=1"""
    params = []
    if comp_f: q += " AND a.company_id = %s"; params.append(comp_f)
    if stat_f: q += " AND a.status = %s";     params.append(stat_f)
    if dept_f: q += " AND s.department = %s"; params.append(dept_f)
    q += " ORDER BY a.applied_at DESC"

    result       = execute_query(q, tuple(params) if params else None)
    applications = result['data'] if result['success'] else []

    comp_r    = execute_query("SELECT company_id, name FROM companies ORDER BY name")
    companies = comp_r['data'] if comp_r['success'] else []

    return render_template('admin/applications.html',
                           applications=applications, companies=companies,
                           comp_f=comp_f, stat_f=stat_f, dept_f=dept_f)


@app.route('/admin/applications/<int:app_id>/shortlist', methods=['POST'])
@admin_required
def admin_shortlist(app_id):
    r = execute_query(
        "UPDATE applications SET status='in_progress', updated_at=NOW() WHERE application_id=%s",
        (app_id,), fetch=False
    )
    flash('Application shortlisted.' if r['success'] else 'Action failed.',
          'success' if r['success'] else 'danger')
    return redirect(url_for('admin_applications'))


@app.route('/admin/applications/<int:app_id>/reject', methods=['POST'])
@admin_required
def admin_reject(app_id):
    r = execute_query(
        "UPDATE applications SET status='rejected', updated_at=NOW() WHERE application_id=%s",
        (app_id,), fetch=False
    )
    flash('Application rejected.' if r['success'] else 'Action failed.',
          'info' if r['success'] else 'danger')
    return redirect(url_for('admin_applications'))


@app.route('/admin/rounds')
@admin_required
def admin_rounds():
    comp_f = request.args.get('company', '')
    q = """SELECT r.round_id, r.round_number, r.round_type, r.round_name,
                  r.scheduled_date, r.status AS round_status, r.venue,
                  c.company_id, c.name AS company_name,
                  (SELECT COUNT(*) FROM round_results rr WHERE rr.round_id = r.round_id) AS participants,
                  (SELECT COUNT(*) FROM round_results rr WHERE rr.round_id = r.round_id AND rr.status='shortlisted') AS shortlisted
           FROM rounds r JOIN companies c ON r.company_id = c.company_id WHERE 1=1"""
    params = []
    if comp_f: q += " AND r.company_id = %s"; params.append(comp_f)
    q += " ORDER BY c.name, r.round_number"

    result = execute_query(q, tuple(params) if params else None)
    rounds = result['data'] if result['success'] else []

    comp_r    = execute_query("SELECT company_id, name FROM companies WHERE status IN ('upcoming','ongoing') ORDER BY name")
    companies = comp_r['data'] if comp_r['success'] else []

    apps_r    = execute_query(
        """SELECT a.application_id, s.name AS student_name, s.roll_number, c.name AS company_name
           FROM applications a
           JOIN students s ON a.student_id = s.student_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE a.status IN ('applied','in_progress') ORDER BY c.name, s.name"""
    )
    active_apps = apps_r['data'] if apps_r['success'] else []

    rounds_r = execute_query("SELECT round_id, round_name, round_number, company_id FROM rounds WHERE status != 'cancelled' ORDER BY round_id")
    all_rounds = rounds_r['data'] if rounds_r['success'] else []

    return render_template('admin/rounds.html',
                           rounds=rounds, companies=companies,
                           active_apps=active_apps, all_rounds=all_rounds, comp_f=comp_f)


@app.route('/admin/rounds/add', methods=['POST'])
@admin_required
def admin_add_round():
    f = request.form
    r = execute_query(
        """INSERT INTO rounds (company_id, round_number, round_type, round_name,
                              description, scheduled_date, venue, duration_minutes, status)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'scheduled')""",
        (f.get('company_id'), f.get('round_number'), f.get('round_type'),
         f.get('round_name'), f.get('description'),
         f.get('scheduled_date') or None, f.get('venue'),
         f.get('duration_minutes') or None),
        fetch=False
    )
    flash('Round created.' if r['success'] else f'Error: {r.get("error","")}',
          'success' if r['success'] else 'danger')
    return redirect(url_for('admin_rounds'))


@app.route('/admin/rounds/result', methods=['POST'])
@admin_required
def admin_round_result():
    f = request.form
    result = call_procedure_with_out_params(
        'sp_update_round_result',
        in_args=(int(f.get('round_id')), int(f.get('application_id')),
                 f.get('status'), float(f.get('score') or 0),
                 f.get('feedback') or None, 1 if f.get('attended') else 0),
        out_param_count=2
    )
    flash('Result updated.' if result['success'] else result.get('error', 'Update failed.'),
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin_rounds'))


@app.route('/admin/rounds/<int:round_id>/bulk-shortlist', methods=['POST'])
@admin_required
def admin_bulk_shortlist(round_id):
    min_score = float(request.form.get('min_score', 60))
    result    = call_procedure('sp_process_round_shortlist', args=(round_id, min_score))
    if result['success']:
        n = result['data'][0].get('shortlisted_count', 0) if result['data'] else 0
        flash(f'Bulk shortlist done — {n} candidates shortlisted.', 'success')
    else:
        flash(result.get('error', 'Bulk shortlist failed.'), 'danger')
    return redirect(url_for('admin_rounds'))


@app.route('/admin/offers')
@admin_required
def admin_offers():
    comp_f = request.args.get('company', '')
    stat_f = request.args.get('status', '')

    q = """SELECT o.offer_id, o.offered_ctc, o.offered_role, o.job_location,
                  o.joining_date, o.status, o.acceptance_deadline, o.accepted_at,
                  s.name AS student_name, s.roll_number, s.department,
                  c.name AS company_name, c.is_dream, c.company_id
           FROM offers o
           JOIN applications a ON o.application_id = a.application_id
           JOIN students s ON a.student_id = s.student_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE 1=1"""
    params = []
    if comp_f: q += " AND c.company_id = %s"; params.append(comp_f)
    if stat_f: q += " AND o.status = %s";     params.append(stat_f)
    q += " ORDER BY o.created_at DESC"

    result = execute_query(q, tuple(params) if params else None)
    offers = result['data'] if result['success'] else []

    sel_r = execute_query(
        """SELECT a.application_id, s.name AS student_name, s.roll_number, c.name AS company_name
           FROM applications a
           JOIN students s ON a.student_id = s.student_id
           JOIN companies c ON a.company_id = c.company_id
           WHERE a.status = 'selected'
           AND a.application_id NOT IN (SELECT application_id FROM offers)"""
    )
    eligible_for_offer = sel_r['data'] if sel_r['success'] else []

    comp_r    = execute_query("SELECT company_id, name FROM companies ORDER BY name")
    companies = comp_r['data'] if comp_r['success'] else []

    return render_template('admin/offers.html',
                           offers=offers, eligible_for_offer=eligible_for_offer,
                           companies=companies, comp_f=comp_f, stat_f=stat_f)


@app.route('/admin/offers/create', methods=['POST'])
@admin_required
def admin_create_offer():
    f = request.form
    result = call_procedure_with_out_params(
        'sp_create_offer',
        in_args=(int(f.get('application_id')), float(f.get('offered_ctc')),
                 f.get('offered_role'), f.get('job_location'),
                 f.get('joining_date') or None, f.get('acceptance_deadline')),
        out_param_count=2
    )
    flash('Offer created.' if result['success'] else result.get('error', 'Offer creation failed.'),
          'success' if result['success'] else 'danger')
    return redirect(url_for('admin_offers'))


@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    dept_r   = execute_query("SELECT * FROM vw_department_placement_stats")
    dept_stats = dept_r['data'] if dept_r['success'] else []

    comp_r   = execute_query("SELECT * FROM vw_company_statistics ORDER BY total_applications DESC")
    comp_stats = comp_r['data'] if comp_r['success'] else []

    batch_r  = execute_query("SELECT * FROM vw_batch_placement_comparison ORDER BY batch_year DESC")
    batch_stats = batch_r['data'] if batch_r['success'] else []

    pkg_r    = execute_query(
        "SELECT MIN(offered_ctc) AS min_p, MAX(offered_ctc) AS max_p, AVG(offered_ctc) AS avg_p, COUNT(*) AS n FROM offers WHERE status='accepted'",
        fetch_one=True
    )
    pkg_stats = pkg_r['data'] if pkg_r['success'] else {}

    leaders_r  = execute_query("SELECT * FROM vw_placement_leaderboard LIMIT 10")
    leaderboard = leaders_r['data'] if leaders_r['success'] else []

    dream_r      = execute_query("SELECT * FROM vw_dream_company_placements LIMIT 10")
    dream_placements = dream_r['data'] if dream_r['success'] else []

    return render_template('admin/analytics.html',
                           dept_stats=dept_stats, comp_stats=comp_stats,
                           batch_stats=batch_stats, pkg_stats=pkg_stats,
                           leaderboard=leaderboard, dream_placements=dream_placements)


@app.route('/admin/audit')
@admin_required
def admin_audit():
    table_f  = request.args.get('table', '')
    action_f = request.args.get('action', '')

    q = "SELECT * FROM vw_audit_trail WHERE 1=1"
    params = []
    if table_f:  q += " AND table_name = %s";   params.append(table_f)
    if action_f: q += " AND action_type = %s";  params.append(action_f)
    q += " ORDER BY action_timestamp DESC LIMIT 200"

    result = execute_query(q, tuple(params) if params else None)
    logs   = result['data'] if result['success'] else []

    tables_r = execute_query("SELECT DISTINCT table_name FROM audit_logs ORDER BY table_name")
    tables   = [r['table_name'] for r in (tables_r['data'] or [])] if tables_r['success'] else []

    return render_template('admin/audit.html',
                           logs=logs, tables=tables, table_f=table_f, action_f=action_f)


# =============================================================================
# AJAX / API ENDPOINTS
# =============================================================================

@app.route('/api/dept-chart')
@admin_required
def api_dept_chart():
    r = execute_query("SELECT department, placed_students, unplaced_students, placement_percentage FROM vw_department_placement_stats ORDER BY department")
    return jsonify(r['data'] if r['success'] else [])


@app.route('/api/batch-chart')
@admin_required
def api_batch_chart():
    r = execute_query("SELECT batch_year, placed_count, total_students, placement_percentage FROM vw_batch_placement_comparison ORDER BY batch_year")
    return jsonify(r['data'] if r['success'] else [])

@app.route('/api/company-chart')
@admin_required
def api_company_chart():
    r = execute_query("SELECT company_name, total_applications, selected_count FROM vw_company_statistics ORDER BY total_applications DESC LIMIT 8")
    return jsonify(r['data'] if r['success'] else [])


@app.route('/health')
def health():
    from db import test_connection
    return jsonify({'status': 'ok', 'db_connected': test_connection()})


# =============================================================================
# COMPANY / RECRUITER ROUTES
# =============================================================================

@app.route('/company/dashboard')
@company_required
def company_dashboard():
    cid = session.get('company_id')
    if not cid:
        flash('No company linked to your profile.', 'danger')
        return redirect(url_for('logout'))
        
    def scalar(q, p=None):
        r = execute_query(q, p, fetch_one=True)
        return r['data']['v'] if r['success'] and r['data'] else 0

    stats = {
        'total_applicants': scalar("SELECT COUNT(*) AS v FROM applications WHERE company_id = %s", (cid,)),
        'shortlisted': scalar("SELECT COUNT(*) AS v FROM applications WHERE company_id = %s AND status = 'in_progress'", (cid,)),
        'selected': scalar("SELECT COUNT(*) AS v FROM applications WHERE company_id = %s AND status = 'selected'", (cid,)),
        'offers_released': scalar("SELECT COUNT(*) AS v FROM offers o JOIN applications a ON o.application_id = a.application_id WHERE a.company_id = %s", (cid,)),
    }
    
    stats['acceptance_rate'] = 0
    if stats['offers_released'] > 0:
        accepted = scalar("SELECT COUNT(*) AS v FROM offers o JOIN applications a ON o.application_id = a.application_id WHERE a.company_id = %s AND o.status = 'accepted'", (cid,))
        stats['acceptance_rate'] = round(accepted / stats['offers_released'] * 100, 1)

    rounds = execute_query("SELECT * FROM rounds WHERE company_id = %s ORDER BY round_number", (cid,))
    active_rounds = rounds['data'] if rounds['success'] else []
    
    company = execute_query("SELECT * FROM companies WHERE company_id=%s", (cid,), fetch_one=True)['data']
    
    return render_template('company/dashboard.html', stats=stats, active_rounds=active_rounds, company=company)

@app.route('/company/drives', methods=['GET', 'POST'])
@company_required
def company_drive():
    cid = session['company_id']
    if request.method == 'POST':
        f = request.form
        execute_query(
            "UPDATE companies SET job_description=%s, ctc_lpa=%s, registration_deadline=%s, status=%s WHERE company_id=%s",
            (f.get('job_description'), f.get('ctc_lpa'), f.get('registration_deadline'), f.get('status'), cid),
            fetch=False
        )
        flash('Drive details updated.', 'success')
        return redirect(url_for('company_drive'))
        
    company = execute_query("SELECT * FROM companies WHERE company_id=%s", (cid,), fetch_one=True)['data']
    eligibility = execute_query("SELECT * FROM eligibility_criteria WHERE company_id=%s", (cid,), fetch_one=True)['data']
    return render_template('company/drive.html', company=company, eligibility=eligibility)

@app.route('/company/pipeline')
@company_required
def company_pipeline():
    cid = session['company_id']
    status_f = request.args.get('status', '')
    
    q = """SELECT a.application_id, a.status, s.student_id, s.name, s.department, s.cgpa, s.resume_path
           FROM applications a JOIN students s ON a.student_id = s.student_id 
           WHERE a.company_id = %s"""
    params = [cid]
    if status_f:
        q += " AND a.status = %s"
        params.append(status_f)
        
    q += " ORDER BY s.cgpa DESC"
    result = execute_query(q, tuple(params))
    applicants = result['data'] if result['success'] else []
    
    return render_template('company/pipeline.html', applicants=applicants, status_f=status_f)

@app.route('/company/applicant/<int:student_id>')
@company_required
def company_applicant_review(student_id):
    student = execute_query("SELECT * FROM students WHERE student_id=%s", (student_id,), fetch_one=True)['data']
    if not student: return "Not found", 404
    
    skills = execute_query("SELECT sk.skill_name, ss.proficiency FROM student_skills ss JOIN skills sk ON ss.skill_id = sk.skill_id WHERE ss.student_id = %s", (student_id,))['data']
    
    return render_template('company/applicant_review.html', student=student, skills=skills)

@app.route('/company/rounds', methods=['GET', 'POST'])
@company_required
def company_rounds():
    cid = session['company_id']
    if request.method == 'POST':
        f = request.form
        execute_query("INSERT INTO rounds (company_id, round_number, round_type, round_name, scheduled_date, venue) VALUES (%s,%s,%s,%s,%s,%s)",
                     (cid, f.get('round_number'), f.get('round_type'), f.get('round_name'), f.get('scheduled_date'), f.get('venue')), fetch=False)
        flash('Round added', 'success')
        return redirect(url_for('company_rounds'))
        
    rounds = execute_query("SELECT * FROM rounds WHERE company_id=%s ORDER BY round_number", (cid,))['data']
    return render_template('company/rounds.html', rounds=rounds)

@app.route('/company/shortlist')
@company_required
def company_shortlist():
    cid = session['company_id']
    rounds = execute_query("SELECT * FROM rounds WHERE company_id=%s ORDER BY round_number", (cid,))['data']
    
    r_id = request.args.get('round_id')
    results = []
    if r_id:
        results = execute_query(
            "SELECT rr.*, s.name, s.department FROM round_results rr JOIN applications a ON rr.application_id = a.application_id JOIN students s ON a.student_id = s.student_id WHERE rr.round_id=%s",
            (r_id,)
        )['data']
        
    return render_template('company/shortlisting.html', rounds=rounds, results=results, selected_round=r_id)

@app.route('/company/offers', methods=['GET', 'POST'])
@company_required
def company_offers():
    cid = session['company_id']
    if request.method == 'POST':
        app_id = request.form.get('application_id')
        ctc = request.form.get('ctc')
        role = request.form.get('role')
        deadline = request.form.get('deadline')
        res = call_procedure_with_out_params('sp_create_offer', in_args=(app_id, ctc, role, 'Remote', None, deadline), out_param_count=2)
        if res['success']: flash('Offer Released!', 'success')
        else: flash(res.get('error', 'Error'), 'danger')
        return redirect(url_for('company_offers'))
        
    offers = execute_query(
        "SELECT o.*, s.name, s.department FROM offers o JOIN applications a ON o.application_id = a.application_id JOIN students s ON a.student_id = s.student_id WHERE a.company_id=%s ORDER BY o.created_at DESC",
        (cid,)
    )['data']
    
    apps = execute_query("SELECT a.application_id, s.name FROM applications a JOIN students s ON a.student_id=s.student_id WHERE a.company_id=%s AND a.status='selected' AND a.application_id NOT IN (SELECT application_id FROM offers)", (cid,))['data']
    
    return render_template('company/offers.html', offers=offers, apps=apps or [])

@app.route('/company/analytics')
@company_required
def company_analytics():
    cid = session['company_id']
    comp = execute_query("SELECT * FROM vw_company_statistics WHERE company_id=%s", (cid,), fetch_one=True)['data'] or {}
    return render_template('company/analytics.html', stats=comp)

@app.route('/company/communications')
@company_required
def company_communications():
    return render_template('company/communications.html')


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('auth/login.html'), 404

@app.errorhandler(500)
def server_error(e):
    flash('A server error occurred. Please try again.', 'danger')
    return redirect(url_for('index'))


# =============================================================================
# CLI COMMANDS
# =============================================================================

@app.cli.command('create-admin')
def create_admin():
    """Create default admin: admin@placify.edu / Admin@123"""
    ph = generate_password_hash('Admin@123')
    r = execute_query("INSERT INTO users (email, password_hash, role) VALUES (%s, %s, 'admin')",
                      ('admin@placify.edu', ph), fetch=False)
    print('✓ Admin created: admin@placify.edu / Admin@123' if r['success'] else f'✗ Error: {r["error"]}')


# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
