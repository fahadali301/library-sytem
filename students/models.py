from django.db import models


class Student(models.Model):
    name = models.CharField(max_length=120)
    roll_number = models.CharField(max_length=40, unique=True)
    books_issued = models.PositiveIntegerField(default=0)
    face_image = models.ImageField(upload_to='student_faces/')

    def __str__(self):
        return f'{self.name} ({self.roll_number})'
