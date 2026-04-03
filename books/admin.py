from django.contrib import admin

from .models import Book, IssueRecord


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'isbn', 'available_copies', 'total_copies')
    search_fields = ('title', 'author', 'isbn')


@admin.register(IssueRecord)
class IssueRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'book', 'issued_at', 'due_date', 'returned_at')
    list_filter = ('returned_at', 'due_date')
    search_fields = ('student__name', 'student__roll_number', 'book__title', 'book__isbn')
