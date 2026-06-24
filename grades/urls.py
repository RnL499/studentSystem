from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('login/', views.RoleLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('courses/enrollment/', views.course_enrollment_manage, name='course_enrollment_manage'),
    path('courses/schedule/', views.student_schedule, name='student_schedule'),
    path('courses/schedule/print/', views.student_schedule_print, name='student_schedule_print'),
    path('courses/', views.student_courses, name='student_courses'),
    path('courses/export/', views.export_my_grades, name='export_my_grades'),
    path('courses/available/', views.available_courses, name='available_courses'),
    path('courses/<int:course_id>/enroll/', views.enroll_student_course, name='enroll_student_course'),
    path('enrollment/<int:enrollment_id>/drop/', views.drop_course, name='drop_course'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    # teacher routes
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/courses/', views.teacher_courses, name='teacher_courses'),
    path('teacher/course/create/', views.create_course, name='create_course'),
    path('teacher/grades/', views.teacher_grade_hub, name='teacher_grade_hub'),
    path('teacher/grades/overview/', views.teacher_grade_overview, name='teacher_grade_overview'),
    path('teacher/grades/export-all/', views.export_all_grades, name='export_all_grades'),
    path('teacher/course/<int:course_id>/students/', views.teacher_course_students, name='teacher_course_students'),
    path('teacher/course/<int:course_id>/grades/', views.teacher_grade_manage, name='teacher_grade_manage'),
    path('teacher/course/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    path('teacher/course/<int:course_id>/delete/', views.remove_course, name='remove_course'),
    path('teacher/course/<int:course_id>/students/export/', views.export_course_students, name='export_course_students'),
    path('teacher/course/<int:course_id>/grades/export/', views.export_course_grades, name='export_course_grades'),
    path('teacher/enrollment/<int:enrollment_id>/approve/', views.approve_enrollment, name='approve_enrollment'),
    path('teacher/enrollment/<int:enrollment_id>/reject/', views.reject_enrollment, name='reject_enrollment'),
    # admin-only dashboard and course creation
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/course/add/', views.admin_add_course, name='admin_add_course'),
    path('teacher/enrollment/<int:enrollment_id>/grade/', views.update_enrollment_grade, name='update_enrollment_grade'),
    path('student/semester/<str:semester>/avg/', views.semester_average, name='semester_average'),
    # comments
    path('course/<int:course_id>/comment/add/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    # admin routes
    path('admin/create-teacher/', views.create_teacher, name='create_teacher'),
    path('admin/delete-teacher/<int:user_id>/', views.delete_teacher, name='delete_teacher'),
    path('admin/enrollment/<int:enrollment_id>/remove/', views.admin_remove_enrollment, name='admin_remove_enrollment'),
    path('admin/delete-user/<int:user_id>/', views.admin_delete_user, name='admin_delete_user'),
    # new admin routes
    path('admin/backup/', views.admin_backup_db, name='admin_backup_db'),
    path('admin/settings/toggle/', views.admin_toggle_settings, name='admin_toggle_settings'),
    path('admin/users/', views.admin_user_manage, name='admin_user_manage'),
]
