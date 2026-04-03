from django.contrib import messages
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from students.forms import StudentCreateForm
from students.models import Student
from students.utils import recognize_student_from_upload

from .forms import BookCreateForm, BookIssueForm
from .models import Book, IssueRecord


def _refresh_student_book_count(student: Student) -> int:
    active_count = IssueRecord.objects.filter(student=student, returned_at__isnull=True).count()
    if student.books_issued != active_count:
        student.books_issued = active_count
        student.save(update_fields=['books_issued'])
    return active_count


def dashboard(request: HttpRequest) -> HttpResponse:
    summary = {
        'students': Student.objects.count(),
        'books': Book.objects.count(),
        'active_issues': IssueRecord.objects.filter(returned_at__isnull=True).count(),
        'available_books': Book.objects.aggregate(total=Sum('available_copies'))['total'] or 0,
    }
    recent_issues = IssueRecord.objects.select_related('student', 'book')[:8]
    top_students = (
        Student.objects.annotate(active_issues=Count('issue_records', filter=Q(issue_records__returned_at__isnull=True)))
        .order_by('-active_issues', 'name')[:8]
    )
    overdue_issues = IssueRecord.objects.filter(
        returned_at__isnull=True,
        due_date__lt=timezone.localdate(),
    ).select_related('student', 'book')[:8]
    low_stock_books = Book.objects.filter(available_copies__lte=F('total_copies') / 2).order_by('available_copies', 'title')[:8]
    return render(
        request,
        'books/dashboard.html',
        {
            'summary': summary,
            'recent_issues': recent_issues,
            'top_students': top_students,
            'overdue_issues': overdue_issues,
            'low_stock_books': low_stock_books,
        },
    )


def book_list(request: HttpRequest) -> HttpResponse:
    books = Book.objects.order_by('title')
    active_issues = IssueRecord.objects.filter(returned_at__isnull=True).select_related('student', 'book')
    return render(request, 'books/book_list.html', {'books': books, 'active_issues': active_issues})


@require_http_methods(['GET', 'POST'])
def issue_book(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = BookIssueForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                issue = form.save(commit=False)
                book = issue.book
                if book.available_copies < 1:
                    form.add_error('book', 'This book is not currently available.')
                else:
                    issue.save()
                    book.available_copies -= 1
                    book.save(update_fields=['available_copies'])
                    _refresh_student_book_count(issue.student)
                    messages.success(request, 'Book issued successfully.')
                    return redirect('book-list')
    else:
        form = BookIssueForm()
    return render(request, 'books/issue_form.html', {'form': form})


@require_POST
def return_book(request: HttpRequest, issue_id: int) -> HttpResponse:
    issue = get_object_or_404(IssueRecord.objects.select_related('student', 'book'), pk=issue_id)
    if issue.returned_at is None:
        with transaction.atomic():
            issue.mark_returned()
            book = issue.book
            book.available_copies = min(book.total_copies, book.available_copies + 1)
            book.save(update_fields=['available_copies'])
            _refresh_student_book_count(issue.student)
        messages.success(request, 'Book returned successfully.')
    else:
        messages.info(request, 'This issue record is already returned.')
    return redirect('book-list')


def student_ledger(request: HttpRequest, student_id: int) -> HttpResponse:
    student = get_object_or_404(Student, pk=student_id)
    active_count = _refresh_student_book_count(student)
    records = IssueRecord.objects.filter(student=student).select_related('book')
    active_records = records.filter(returned_at__isnull=True)
    returned_records = records.filter(returned_at__isnull=False)
    return render(
        request,
        'books/student_ledger.html',
        {
            'student': student,
            'active_count': active_count,
            'active_records': active_records,
            'returned_records': returned_records,
        },
    )


@require_http_methods(['GET', 'POST'])
def face_lookup_page(request: HttpRequest) -> HttpResponse:
    context = {'result': None, 'error': None}
    if request.method == 'POST':
        uploaded_file = request.FILES.get('image')
        if uploaded_file is None:
            context['error'] = 'Please upload an image.'
        else:
            try:
                result = recognize_student_from_upload(uploaded_file)
            except (ValueError, RuntimeError) as exc:
                context['error'] = str(exc)
            else:
                if result.student is None:
                    context['result'] = {'message': result.message, 'confidence': result.confidence, 'student': None}
                else:
                    student = result.student
                    active_count = _refresh_student_book_count(student)
                    active_records = list(
                        IssueRecord.objects.filter(student=student, returned_at__isnull=True)
                        .select_related('book')
                        .order_by('-issued_at')
                    )
                    context['result'] = {
                        'message': result.message,
                        'confidence': result.confidence,
                        'student': student,
                        'active_count': active_count,
                        'active_records': active_records,
                    }
    return render(request, 'books/face_lookup.html', context)


@require_http_methods(['GET', 'POST'])
def add_book(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = BookCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Book added successfully.')
            return redirect('book-list')
    else:
        form = BookCreateForm()
    return render(request, 'books/add_book.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def add_student(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = StudentCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully.')
            return redirect('dashboard')
    else:
        form = StudentCreateForm()
    return render(request, 'students/add_student.html', {'form': form})

