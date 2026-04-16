-- =============================================================================
-- Placify – Sample Data
-- Run after schema.sql, views.sql, procedures.sql, triggers.sql
-- =============================================================================

-- Skills master list
INSERT IGNORE INTO skills (skill_name, category) VALUES
('Python',         'programming'),
('Java',           'programming'),
('C++',            'programming'),
('JavaScript',     'programming'),
('SQL',            'database'),
('MySQL',          'database'),
('PostgreSQL',     'database'),
('MongoDB',        'database'),
('React',          'web_development'),
('Node.js',        'web_development'),
('Flask',          'web_development'),
('Django',         'web_development'),
('Machine Learning','data_science'),
('Data Analysis',  'data_science'),
('Power BI',       'data_science'),
('TensorFlow',     'data_science'),
('AWS',            'cloud'),
('Docker',         'devops'),
('Git',            'tools'),
('Linux',          'tools'),
('Communication',  'soft_skills'),
('Leadership',     'soft_skills'),
('Problem Solving','soft_skills'),
('MATLAB',         'engineering'),
('AutoCAD',        'engineering'),
('VLSI Design',    'engineering');

-- Student and admin user creation is now handled dynamically by setup_db.py 
-- to ensure correct password hashing for your environment.

-- =============================================================================
-- Companies
-- =============================================================================
INSERT IGNORE INTO companies
  (name, description, website, industry, company_type, job_role, job_description,
   job_location, ctc_lpa, is_dream, visit_date, registration_deadline, status)
VALUES
('Google India',
 'Software Engineering role — full-stack development on core products.',
 'https://careers.google.com', 'Technology', 'mnc',
 'Software Engineer', 'Design, develop and deploy large-scale distributed systems.',
 'Bengaluru', 24.00, TRUE,
 DATE_ADD(CURDATE(), INTERVAL 10 DAY),
 DATE_ADD(NOW(), INTERVAL 7 DAY), 'upcoming'),

('Infosys',
 'Systems Engineer — enterprise software development.',
 'https://www.infosys.com', 'Technology', 'service',
 'Systems Engineer', 'Work on enterprise Java/.NET projects for global clients.',
 'Pune', 3.60, FALSE,
 DATE_ADD(CURDATE(), INTERVAL 5 DAY),
 DATE_ADD(NOW(), INTERVAL 3 DAY), 'upcoming'),

('Tata Consultancy Services',
 'TCS NQT — National Qualifier Test for multiple roles.',
 'https://www.tcs.com', 'Technology', 'service',
 'Assistant System Engineer', 'Development and maintenance of client applications.',
 'Chennai', 3.36, FALSE,
 DATE_ADD(CURDATE(), INTERVAL 15 DAY),
 DATE_ADD(NOW(), INTERVAL 12 DAY), 'upcoming'),

('Amazon',
 'SDE-1 — Work on AWS and core Amazon products.',
 'https://amazon.jobs', 'Technology', 'mnc',
 'Software Development Engineer', 'Build highly available, scalable services.',
 'Hyderabad', 26.00, TRUE,
 DATE_ADD(CURDATE(), INTERVAL 20 DAY),
 DATE_ADD(NOW(), INTERVAL 17 DAY), 'upcoming'),

('BHEL',
 'Engineer Trainee — Power generation projects.',
 'https://www.bhel.com', 'Manufacturing', 'psu',
 'Engineer Trainee', 'Design and maintenance of power plant equipment.',
 'Multiple', 6.50, FALSE,
 DATE_ADD(CURDATE(), INTERVAL 8 DAY),
 DATE_ADD(NOW(), INTERVAL 5 DAY), 'upcoming');

-- =============================================================================
-- Eligibility Criteria
-- =============================================================================
INSERT IGNORE INTO eligibility_criteria
  (company_id, min_cgpa, max_backlogs, allowed_departments, min_batch_year, max_batch_year)
SELECT company_id, min_cgpa, max_backlogs, allowed_departments, 2025, 2025
FROM (
  SELECT company_id,
         CASE name
           WHEN 'Google India' THEN 8.0
           WHEN 'Amazon'       THEN 7.5
           WHEN 'BHEL'         THEN 6.0
           ELSE 6.0
         END AS min_cgpa,
         CASE name
           WHEN 'Google India' THEN 0
           WHEN 'Amazon'       THEN 0
           ELSE 2
         END AS max_backlogs,
         CASE name
           WHEN 'BHEL' THEN '["ME","EEE","CE"]'
           WHEN 'Google India' THEN '["CSE","IT","ECE"]'
           WHEN 'Amazon'       THEN '["CSE","IT","ECE"]'
           ELSE '["CSE","ECE","IT","ME","CE","EEE"]'
         END AS allowed_departments
  FROM companies
) x;
