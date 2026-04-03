from django import forms

from .models import Student


class StudentCreateForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ('name', 'roll_number', 'face_image')

