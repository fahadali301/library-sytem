from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('books/', views.book_list, name='book-list'),
    path('books/add/', views.add_book, name='book-add'),
    path('books/issue/', views.issue_book, name='book-issue'),
    path('students/add/', views.add_student, name='student-add'),
    path('issues/<int:issue_id>/return/', views.return_book, name='book-return'),
    path('students/<int:student_id>/', views.student_ledger, name='student-ledger'),
    path('face-lookup/', views.face_lookup_page, name='face-lookup-page'),
]
