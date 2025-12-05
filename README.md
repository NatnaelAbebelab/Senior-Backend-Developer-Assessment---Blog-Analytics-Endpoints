Senior Backend Developer Assessment

**Author**: Natnael Abebe  
**Date**: December 2025

---

### Features Implemented

| API | Endpoint                     | Key Features |
|-----|------------------------------|--------------|
| #1  | `/analytics/blog-views/`     | Group by country/user, time range (month/week/year), dynamic filters (and/or/not) |
| #2  | `/analytics/top/`            | Top 10 blogs/users/countries, time range, dynamic filters |
| #3  | `/analytics/performance/`    | Time-series performance, growth/decline %, blog creation count, no gaps, supports day/week/month/year |

All APIs:
- Use **only 2 models** (`Blog`, `BlogView`)
- Share **one reusable dynamic filter engine** (AND/OR/NOT + nested)
- **Zero N+1 queries**
- Production-grade performance & clean architecture
- Fully tested with realistic data

---

### Tech Stack

- Django 4.2+ (LTS)
- Django REST Framework
- SQLite (default Django database — zero setup)
- Python 3.10+

---

### Setup & Installation (30 seconds — no external DB needed)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# or
venv\Scripts\activate             # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Load realistic test data
python manage.py shell < initial_data.py
# OR: python manage.py shell → paste the script from the file

# 6. Run the server
python manage.py runserver

---

### Sample Requests
# Top 10 blogs
curl "http://127.0.0.1:8000/analytics/top/?top=blog"

# Views by country (last year)
curl "http://127.0.0.1:8000/analytics/blog-views/?object_type=country&range=month"

# Performance for author #3
curl "http://127.0.0.1:8000/analytics/performance/?compare=month&user_id=3"
