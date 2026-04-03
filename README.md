# Managment

A Django-based library management project with:
- student records + face recognition (OpenCV)
- books catalog
- issue/return workflow
- frontend dashboard and ledger pages

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Frontend Pages

- `/` - dashboard (stats, overdue issues, low stock, quick actions)
- `/books/` - books list + active issue records
- `/books/add/` - add book from frontend
- `/students/add/` - add student from frontend with face image
- `/books/issue/` - issue form
- `/students/<id>/` - student ledger
- `/face-lookup/` - camera detect + fallback upload and student books

## API

`POST /api/face-book-lookup/` as multipart form-data with key `image`.

Response includes recognized student info, `books_issued`, and `active_books` list.

## Camera Usage

Open `/face-lookup/`, click `Start Camera`, then `Capture and Detect`.
The page sends a captured frame to the API, so manual upload is not required.

## Tests

```bash
source .venv/bin/activate
python manage.py test -v 2
```
