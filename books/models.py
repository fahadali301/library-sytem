from django.db import models
from django.db.models import Q
from django.utils import timezone


class Book(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=120)
    isbn = models.CharField(max_length=20, unique=True)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('title',)

    def __str__(self):
        return f'{self.title} - {self.author}'


class IssueRecord(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='issue_records')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='issue_records')
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(blank=True, null=True)
    returned_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ('-issued_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'book'),
                condition=Q(returned_at__isnull=True),
                name='unique_active_issue_per_student_book',
            )
        ]

    def __str__(self):
        return f'{self.student.roll_number} -> {self.book.title}'

    @property
    def is_returned(self):
        return self.returned_at is not None

    def mark_returned(self):
        if self.returned_at is None:
            self.returned_at = timezone.now()
            self.save(update_fields=['returned_at'])
