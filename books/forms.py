from django import forms

from .models import Book, IssueRecord


class BookCreateForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ('title', 'author', 'isbn', 'total_copies', 'available_copies')

    def clean(self):
        cleaned_data = super().clean()
        total = cleaned_data.get('total_copies')
        available = cleaned_data.get('available_copies')
        if total is not None and available is not None and available > total:
            self.add_error('available_copies', 'Available copies cannot be greater than total copies.')
        return cleaned_data


class BookIssueForm(forms.ModelForm):
    class Meta:
        model = IssueRecord
        fields = ('student', 'book', 'due_date')
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['book'].queryset = Book.objects.filter(available_copies__gt=0).order_by('title')
