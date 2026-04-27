<div align="center">

<img src="static/assets/logo.png" alt="Placify Logo" width="200"/>

# Placify — Campus Placement Management System

**A full-stack DBMS project demonstrating advanced SQL concepts through a real-world campus placement portal.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=for-the-badge&logo=mysql&logoColor=white)](https://mysql.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[Live Demo](#-quick-start) · [Features](#-features) · [Architecture](#-architecture) · [SQL Concepts](#-dbms-concepts-demonstrated) · [Setup Guide](#-installation--setup)

</div>

---

## 📋 Overview

Placify is a **comprehensive campus placement management system** built as a DBMS course project. It models the entire campus recruitment lifecycle — from student registration and company drive management to multi-round interviews, offer processing, and analytics — while demonstrating **20+ advanced SQL/DBMS concepts** in a production-grade web application.

The system features **three distinct portals** (Student, Company/HR, and Admin), each with role-based access control, real-time analytics dashboards, and ACID-compliant transaction processing.

---

## ✨ Features

### 🎓 Student Portal
| Feature | Description |
|---------|-------------|
| **Dashboard** | Personalized stats — applications, selections, offers, best package |
| **Company Browser** | View eligible companies with CGPA/backlog-based filtering |
| **Application Tracker** | Real-time status updates across all applications |
| **Round Progress** | Score tracking across aptitude, coding, technical, and HR rounds |
| **Offer Management** | Accept/decline offers with ACID-compliant transaction processing |
| **Profile & Skills** | Academic profile, resume upload, and verified skill management |

### 🏢 Company / HR Portal
| Feature | Description |
|---------|-------------|
| **Recruiter Dashboard** | At-a-glance hiring funnel — applicants, shortlisted, selected, offers |
| **Drive Management** | Configure job descriptions, CTC, deadlines, and eligibility criteria |
| **Applicant Pipeline** | Filterable candidate view with profile drill-down |
| **Interview Rounds** | Schedule and manage multi-round interview processes |
| **Results & Shortlisting** | Score-based candidate progression with round-level analytics |
| **Offer Release** | Digital offer letter issuance with acceptance deadline tracking |
| **Hiring Analytics** | Funnel visualization, selection ratios, and package statistics |
| **Communications** | Automated notification system for interviews and offers |

### 🛡️ Admin Portal
| Feature | Description |
|---------|-------------|
| **Global Dashboard** | Institution-wide placement statistics and KPIs |
| **Student Management** | View, edit, and manage all registered students |
| **Company Management** | Register companies, set eligibility, manage drives |
| **Analytics Suite** | Department-wise stats, batch comparison, leaderboard |
| **Audit Trail** | Trigger-based logging of all database mutations |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PLACIFY SYSTEM                           │
├─────────────┬───────────────────┬───────────────────────────────┤
│  FRONTEND   │    BACKEND API    │         DATABASE              │
│             │                   │                               │
│  Jinja2     │    Flask 3.0      │    MySQL 8.0                  │
│  Templates  │    Python 3.10+   │                               │
│             │                   │    ┌───────────────────┐      │
│  ┌────────┐ │  ┌─────────────┐  │    │ Tables (11)       │      │
│  │Student │◄├──┤ app.py      │──├───►│ Views  (8)        │      │
│  │Portal  │ │  │ (1200+ LOC) │  │    │ Procedures (5)    │      │
│  ├────────┤ │  ├─────────────┤  │    │ Functions (4)     │      │
│  │Company │◄├──┤ db.py       │──├───►│ Triggers (6)      │      │
│  │Portal  │ │  │ (Pool Mgmt) │  │    │ Constraints (FK)  │      │
│  ├────────┤ │  ├─────────────┤  │    └───────────────────┘      │
│  │Admin   │◄├──┤ config.py   │  │                               │
│  │Portal  │ │  └─────────────┘  │    Connection Pooling (5)     │
│  └────────┘ │                   │    Parameterized Queries      │
│             │  Role-Based Auth  │    ACID Transactions          │
│  Chart.js   │  Session Mgmt    │    Audit Logging              │
│  Inter Font │  CSRF Protection  │    Stored Programs            │
└─────────────┴───────────────────┴───────────────────────────────┘
```

---

## 📊 DBMS Concepts Demonstrated

> This project was designed to comprehensively cover the DBMS syllabus. Each concept is implemented in production context, not as an isolated example.

### Core Database Design
| Concept | Implementation | File |
|---------|---------------|------|
| **ER Modeling → Relational Schema** | 11 normalized tables with proper relationships | [`schema.sql`](schema.sql) |
| **Normalization (3NF)** | Decomposed tables: `students`, `skills`, `student_skills` | [`schema.sql`](schema.sql) |
| **Foreign Keys & Referential Integrity** | `ON DELETE CASCADE`, `ON UPDATE CASCADE` constraints | [`schema.sql`](schema.sql) |
| **CHECK Constraints** | CGPA range, status enums, batch year validation | [`schema.sql`](schema.sql) |
| **UNIQUE & Composite Keys** | `(student_id, company_id)` in applications | [`schema.sql`](schema.sql) |

### Stored Programs
| Concept | Implementation | File |
|---------|---------------|------|
| **Stored Procedures** | `sp_apply_for_company`, `sp_create_offer`, `sp_accept_offer` | [`procedures.sql`](procedures.sql) |
| **Stored Functions** | `fn_get_student_highest_package`, `fn_get_placement_rank` | [`functions.sql`](functions.sql) |
| **Cursors** | `sp_get_eligible_companies` with cursor-based iteration | [`procedures.sql`](procedures.sql) |
| **Exception Handling** | `DECLARE HANDLER` for duplicate/constraint violations | [`procedures.sql`](procedures.sql) |
| **OUT Parameters** | Procedures returning status codes and messages | [`procedures.sql`](procedures.sql) |

### Views & Aggregation
| Concept | Implementation | File |
|---------|---------------|------|
| **Complex Views** | 8 analytics views with multi-table JOINs | [`views.sql`](views.sql) |
| **Aggregate Functions** | `COUNT`, `AVG`, `MAX`, `MIN`, `SUM` across dashboards | [`views.sql`](views.sql) |
| **GROUP BY + HAVING** | Department-wise stats with minimum thresholds | [`views.sql`](views.sql) |
| **Subqueries** | Correlated subqueries in `fn_get_placement_rank` | [`functions.sql`](functions.sql) |
| **CASE Expressions** | Dynamic status categorization in views | [`views.sql`](views.sql) |

### Triggers & Transactions
| Concept | Implementation | File |
|---------|---------------|------|
| **AFTER INSERT Triggers** | Auto audit logging on `applications`, `offers` | [`triggers.sql`](triggers.sql) |
| **AFTER UPDATE Triggers** | Track status changes with JSON diff logging | [`triggers.sql`](triggers.sql) |
| **BEFORE INSERT Triggers** | Duplicate application prevention | [`triggers.sql`](triggers.sql) |
| **ACID Transactions** | Offer acceptance with atomic status updates | [`procedures.sql`](procedures.sql) |

### Advanced Patterns
| Concept | Implementation | File |
|---------|---------------|------|
| **Connection Pooling** | 5-connection MySQL pool with auto-reconnect | [`db.py`](db.py) |
| **Parameterized Queries** | All queries use `%s` placeholders (SQL injection prevention) | [`db.py`](db.py) |
| **JSON Storage** | `eligibility_criteria.allowed_departments` as JSON array | [`schema.sql`](schema.sql) |
| **Decimal Precision** | `DECIMAL(10,2)` for all financial fields (CTC, packages) | [`schema.sql`](schema.sql) |
| **Audit Trail** | Complete mutation history via trigger → `audit_logs` table | [`triggers.sql`](triggers.sql) |

---

## 🚀 Installation & Setup

### Prerequisites

- **Python** 3.10+
- **MySQL** 8.0+
- **pip** (Python package manager)

### 1. Clone the repository

```bash
git clone https://github.com/Satvik-Shashank/Placify_DBMS_project.git
cd Placify_DBMS_project
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure your database

```bash
cp .env.example .env
```

Edit `.env` and set your MySQL credentials:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DATABASE=campus_placement
```

### 4. Initialize the database & seed data

```bash
python setup_db.py
```

This will automatically:
- Create the `campus_placement` database
- Execute `schema.sql` (tables & constraints)
- Execute `views.sql`, `procedures.sql`, `functions.sql`, `triggers.sql`
- Seed sample companies, students, and eligibility criteria

### 5. Run the application

```bash
python app.py
```

Open **[http://localhost:5000](http://localhost:5000)** in your browser.

---

## 🔐 Demo Credentials

| Portal | Email | Password | Description |
|--------|-------|----------|-------------|
| **Admin** | `admin@placify.com` | `admin123` | Full system access |
| **Company (Microsoft)** | `microsoft@placify.com` | `microsoft123` | HR recruiter view |
| **Student (Satvik)** | `student@placify.com` | `student123` | Placed student with offers |
| **Student (Arjun)** | `cs_arjun@placify.com` | `student123` | Mid-tier with pending offers |
| **Student (Sneha)** | `it_sneha@placify.com` | `student123` | Active applications |

---

## 📁 Project Structure

```
Placify_DBMS_project/
│
├── app.py                    # Flask routes — all 3 portals (1200+ lines)
├── db.py                     # MySQL connection pool + query helpers
├── config.py                 # Environment configuration loader
├── setup_db.py               # One-shot database setup & seed script
├── seed_more_data.py         # Additional realistic demo data
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
│
├── sql/                      # SQL source files
│   └── sample_data.sql       # Seed data (companies, eligibility)
│
├── schema.sql                # Tables, constraints, indexes
├── views.sql                 # 8 analytics views
├── procedures.sql            # 5 stored procedures
├── functions.sql             # 4 stored functions
├── triggers.sql              # 6 database triggers
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Shared layout (sidebar + topbar)
│   ├── auth/
│   │   └── login.html        # Authentication page
│   ├── components/           # Reusable sidebar partials
│   │   ├── sidebar_admin.html
│   │   ├── sidebar_company.html
│   │   └── sidebar_student.html
│   ├── student/              # Student portal (6 pages)
│   │   ├── dashboard.html
│   │   ├── profile.html
│   │   ├── companies.html
│   │   ├── applications.html
│   │   ├── rounds.html
│   │   └── offers.html
│   ├── company/              # Company portal (9 pages)
│   │   ├── dashboard.html
│   │   ├── analytics.html
│   │   ├── pipeline.html
│   │   ├── rounds.html
│   │   ├── shortlisting.html
│   │   ├── offers.html
│   │   ├── drive.html
│   │   ├── applicant_review.html
│   │   └── communications.html
│   └── admin/                # Admin portal pages
│
├── static/
│   ├── css/
│   │   └── main.css          # Complete design system (950+ lines)
│   ├── js/
│   │   └── main.js           # UI interactions & sidebar logic
│   └── assets/               # Logo, favicon, images
│
└── uploads/                  # Resume uploads (auto-created)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Flask 3.0, Python 3.10+ | API routing, session management, template rendering |
| **Database** | MySQL 8.0 | Relational data storage, stored programs, triggers |
| **Frontend** | Jinja2, HTML5, CSS3 | Server-side templating with responsive design |
| **Styling** | Custom CSS Design System | Inter font, blue theme, 950+ lines of utility classes |
| **Charts** | Chart.js | Hiring funnel and analytics visualizations |
| **Auth** | Werkzeug + Flask Sessions | Password hashing (pbkdf2:sha256), role-based access |
| **DB Pool** | mysql-connector-python | Connection pooling with 5 reusable connections |

---

## 📈 Database Schema (ER Summary)

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│  users   │────►│   students   │────►│ student_skills│
│          │     │              │     │              │
│ user_id  │     │ student_id   │     │ skill_id  ──►│──► skills
│ email    │     │ name, cgpa   │     │ proficiency  │
│ role     │     │ department   │     └──────────────┘
└──────────┘     │ is_placed    │
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐     ┌──────────────┐
                 │ applications │────►│    offers     │
                 │              │     │              │
                 │ company_id ──│──►  │ offered_ctc  │
                 │ status       │     │ status       │
                 └──────┬───────┘     └──────────────┘
                        │
                 ┌──────▼───────┐
                 │    rounds    │────► round_results
                 │ round_type   │
                 │ scheduled_at │
                 └──────────────┘

                 ┌──────────────┐     ┌──────────────────────┐
                 │  companies   │────►│ eligibility_criteria  │
                 │ name, ctc    │     │ min_cgpa, max_backlogs│
                 │ is_dream     │     │ allowed_departments   │
                 └──────────────┘     └──────────────────────┘

                 ┌──────────────┐
                 │  audit_logs  │  ◄── Populated by triggers
                 └──────────────┘
```

---

## 👥 Contributors

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/Satvik-Shashank">
        <img src="https://github.com/Satvik-Shashank.png" width="80px;" alt="Satvik"/>
        <br />
        <sub><b>Satvik Shashank</b></sub>
      </a>
    </td>
  </tr>
</table>

---

## 📄 License

This project is built for academic purposes as part of a **Database Management Systems (DBMS)** course project.

---

<div align="center">

**Built with ❤️ using Flask, MySQL & vanilla CSS**

</div>
