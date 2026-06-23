from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django import forms
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.db.models import Count

from .models import Course, Enrollment
from .models import Comment
from .forms import StudentRegistrationForm, UserRegistrationForm, ProfileForm, CommentForm, CreateTeacherForm, GradeForm
from django.contrib.auth.decorators import login_required, user_passes_test

# Placeholder until Course model has schedule/credits/capacity fields
DEFAULT_COURSE_CAPACITY = 40
DEFAULT_COURSE_CREDITS = 3
DEFAULT_COURSE_SCHEDULE = '—'
SCHEDULE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4']


def _user_display_name(user):
    profile = getattr(user, 'profile', None)
    if profile and profile.full_name:
        return profile.full_name
    return user.username


def _teacher_display(user):
    if not user:
        return '未分配'
    return _user_display_name(user)


def _course_row_meta(course):
    enrolled_count = course.enrollments.count()
    capacity = DEFAULT_COURSE_CAPACITY
    remaining = max(0, capacity - enrolled_count)
    return {
        'credits': DEFAULT_COURSE_CREDITS,
        'schedule': DEFAULT_COURSE_SCHEDULE,
        'capacity': capacity,
        'enrolled_count': enrolled_count,
        'remaining': remaining,
        'is_full': enrolled_count >= capacity,
        'teacher_name': _teacher_display(course.teacher),
    }


def _post_login_url(user):
    if user.is_staff:
        return reverse('create_teacher')
    if _is_teacher(user):
        return reverse('teacher_courses')
    return reverse('course_enrollment_manage')


class RoleLoginView(auth_views.LoginView):
    template_name = 'registration/login.html'

    def get_success_url(self):
        return _post_login_url(self.request.user)


def index(request):
    """Index page with link to main grade system."""
    if request.user.is_authenticated:
        return redirect(_post_login_url(request.user))
    return redirect('login')


def main(request):
    """Main page: show students, their enrolled courses and average score."""
    # Redirect based on role: teachers -> teacher dashboard; students -> student dashboard
    if request.user.is_authenticated:
        return redirect(_post_login_url(request.user))
    # exclude staff/admin users from the student listing
    students = User.objects.filter(is_staff=False).order_by('username')
    rows = []
    for s in students:
        enrollments = Enrollment.objects.filter(student=s).select_related('course')
        # Use User.avg_grade if present (we attach it in models.py), otherwise compute here
        avg = None
        if hasattr(s, 'avg_grade') and callable(getattr(s, 'avg_grade')):
            try:
                avg = s.avg_grade()
            except Exception:
                avg = None
        rows.append({'student': s, 'enrollments': enrollments, 'avg': avg})

    courses = Course.objects.all().order_by('code')
    return render(request, 'main.html', {'rows': rows, 'courses': courses})


def _is_teacher_or_staff(user):
    if not user.is_authenticated:
        return False
    if user.is_staff:
        return True
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.is_teacher)


def _is_teacher(user):
    if not user.is_authenticated:
        return False
    # prefer group membership; fallback to profile flag for compatibility
    try:
        if user.groups.filter(name='Teacher').exists():
            return True
    except Exception:
        pass
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.is_teacher)


@user_passes_test(_is_teacher)
def teacher_courses(request):
    """Redirect to first course roster, or show empty state."""
    courses = Course.objects.filter(teacher=request.user).order_by('code')
    if courses.exists():
        return redirect('teacher_course_students', course_id=courses.first().id)
    return render(request, 'uiux/teacher_student_roster.html', {
        'courses': courses,
        'course': None,
        'enrollments': [],
        'active_nav': 'roster',
    })


@user_passes_test(_is_teacher)
def teacher_course_students(request, course_id):
    """Show students for a course."""
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    courses = Course.objects.filter(teacher=request.user).order_by('code')
    enrollments = Enrollment.objects.filter(course=course).select_related('student', 'student__profile')
    return render(request, 'uiux/teacher_student_roster.html', {
        'course': course,
        'courses': courses,
        'enrollments': enrollments,
        'active_nav': 'roster',
    })


@user_passes_test(_is_teacher)
def teacher_grade_hub(request):
    """Entry point for grade management nav — pick first course."""
    courses = Course.objects.filter(teacher=request.user).order_by('code')
    if courses.exists():
        return redirect('teacher_grade_manage', course_id=courses.first().id)
    return redirect('create_course')


@user_passes_test(_is_teacher)
def teacher_grade_manage(request, course_id):
    """Grade input page with midterm/final tabs."""
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    courses = Course.objects.filter(teacher=request.user).order_by('code')
    enrollments = Enrollment.objects.filter(course=course).select_related('student', 'student__profile')
    grade_tab = request.GET.get('tab', 'midterm')
    if grade_tab not in ('midterm', 'final'):
        grade_tab = 'midterm'
    return render(request, 'uiux/teacher_grade_manage.html', {
        'course': course,
        'courses': courses,
        'enrollments': enrollments,
        'grade_tab': grade_tab,
        'active_nav': 'grades',
    })


@user_passes_test(_is_teacher)
def update_enrollment_grade(request, enrollment_id):
    """Handle grade updates for an enrollment (POST)."""
    if request.method != 'POST':
        return redirect('teacher_courses')
    enrollment = get_object_or_404(Enrollment, id=enrollment_id)
    # ensure the current user is the instructor for the course (or staff)
    course_teacher_user = getattr(enrollment.course, 'teacher', None)
    if not (course_teacher_user == request.user):
        messages.error(request, '沒有權限修改成績')
        return redirect('teacher_courses')

    mid = request.POST.get('midterm_grade')
    fin = request.POST.get('final_grade')
    # simple validation: allow empty to mean null
    try:
        enrollment.midterm_grade = Decimal(mid) if mid not in (None, '') else None
    except (InvalidOperation, ValueError):
        messages.error(request, '期中成績格式錯誤')
        return redirect('teacher_grade_manage', course_id=enrollment.course.id)
    try:
        enrollment.final_grade = Decimal(fin) if fin not in (None, '') else None
    except (InvalidOperation, ValueError):
        messages.error(request, '期末成績格式錯誤')
        return redirect('teacher_grade_manage', course_id=enrollment.course.id)
    # Disallow negative scores at view level
    if enrollment.midterm_grade is not None and enrollment.midterm_grade < 0:
        messages.error(request, '期中成績不得為負數')
        return redirect('teacher_grade_manage', course_id=enrollment.course.id)
    if enrollment.final_grade is not None and enrollment.final_grade < 0:
        messages.error(request, '期末成績不得為負數')
        return redirect('teacher_grade_manage', course_id=enrollment.course.id)

    enrollment.save()
    messages.success(request, '成績已更新')
    tab = request.POST.get('grade_tab', 'midterm')
    url = reverse('teacher_grade_manage', args=[enrollment.course.id])
    return redirect(f'{url}?tab={tab}')


@user_passes_test(_is_teacher)
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        course_code = request.POST.get('course_code')
        if course_name and course_code:
            course.name = course_name
            course.code = course_code
            course.save()
            messages.success(request, '課程資訊已更新')
            return redirect('teacher_courses')
        else:
            messages.error(request, '請填寫完整資訊')
    return render(request, 'uiux/teacher_edit_course.html', {
        'course': course,
        'active_nav': 'create_course',
    })

import csv
from django.http import HttpResponse

@user_passes_test(_is_teacher)
def export_course_students(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student', 'student__profile')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="students_{course.code}.csv"'
    response.write(u'\ufeff'.encode('utf8'))  # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow(['學號', '姓名', '電子郵件'])
    for e in enrollments:
        full_name = e.student.profile.full_name if hasattr(e.student, 'profile') else ''
        writer.writerow([e.student.username, full_name, e.student.email])
        
    return response


@user_passes_test(_is_teacher)
def export_course_grades(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    enrollments = Enrollment.objects.filter(course=course).select_related('student', 'student__profile')
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="grades_{course.code}.csv"'
    response.write(u'\ufeff'.encode('utf8'))  # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow(['學號', '姓名', '期中成績', '期末成績', '學期成績'])
    for e in enrollments:
        full_name = e.student.profile.full_name if hasattr(e.student, 'profile') else ''
        mid = float(e.midterm_grade) if e.midterm_grade is not None else None
        fin = float(e.final_grade) if e.final_grade is not None else None
        avg = (mid + fin) / 2 if mid is not None and fin is not None else ''
        writer.writerow([
            e.student.username, 
            full_name, 
            e.midterm_grade if e.midterm_grade is not None else '',
            e.final_grade if e.final_grade is not None else '',
            round(avg, 2) if avg != '' else ''
        ])
        
    return response


def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    enrollments = Enrollment.objects.filter(course=course).select_related('student')
    # students not enrolled (for quick enroll form)
    enrolled_student_ids = [e.student.id for e in enrollments]
    other_students = User.objects.exclude(id__in=enrolled_student_ids).filter(is_staff=False).order_by('username')
    comments = Comment.objects.filter(course=course).select_related('user').order_by('-created_at')
    # comment form
    comment_form = CommentForm()
    # pass a safe user_profile to templates to avoid AttributeError for AnonymousUser
    user_profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    return render(request, 'course.html', {
        'course': course,
        'enrollments': enrollments,
        'other_students': other_students,
        'comments': comments,
        'comment_form': comment_form,
        'user_profile': user_profile,
    })

@user_passes_test(_is_teacher)
def add_course(request):
    class CourseForm(forms.ModelForm):
        class Meta:
            model = Course
            fields = ['name', 'code', 'teacher']

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '課程已新增')
            return redirect('main')
    else:
        form = CourseForm()
    # restrict instructor choices to users marked as teachers
    try:
        form.fields['teacher'].queryset = User.objects.filter(profile__is_teacher=True)
    except Exception:
        pass
    return render(request, 'add_course.html', {'form': form})


@user_passes_test(lambda u: u.is_authenticated and u.is_staff)
def admin_add_course(request):
    """Admin-only: create a course and assign a Teacher."""
    class CourseForm(forms.ModelForm):
        class Meta:
            model = Course
            fields = ['name', 'code', 'teacher']

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '課程已由管理者建立')
            return redirect('main')
    else:
        form = CourseForm()
    try:
        form.fields['teacher'].queryset = User.objects.filter(profile__is_teacher=True)
    except Exception:
        pass
    return render(request, 'uiux/admin_add_course.html', {'form': form, 'active_nav': 'add_course'})


@user_passes_test(_is_teacher)
def create_course(request):
    """Allow a logged-in teacher to create a course assigned to themselves."""
    if request.method == 'POST':
        course_name = request.POST.get('course_name')
        course_code = request.POST.get('course_code')
        Course.objects.create(name=course_name, code=course_code, teacher=request.user)
        messages.success(request, '課程已建立')
        return redirect('teacher_courses')

    return render(request, 'uiux/teacher_create_course.html', {
        'display_name': _user_display_name(request.user),
        'active_nav': 'create_course',
    })


def enroll_course(request):
    """Toggle enroll/drop for a student in a course via POST.

    Expects POST keys: course_id, student_id, action ('enroll'|'drop').
    """
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        student_id = request.POST.get('student_id')
        action = request.POST.get('action')
        course = get_object_or_404(Course, id=course_id)

        # determine student: if student_id provided, use it (admin/teacher action);
        # otherwise require login and use the current user.
        if student_id:
            try:
                student = get_object_or_404(User, id=int(student_id))
            except (ValueError, TypeError):
                messages.error(request, '選取的學生無效')
                return redirect(request.META.get('HTTP_REFERER', reverse('main')))
            # If acting on behalf of someone else, require staff/instructor/teacher
            if not request.user.is_authenticated:
                messages.error(request, '請先登入以加退選課程')
                return redirect('login')
            if student != request.user:
                course_teacher_user = getattr(course, 'teacher', None)
                if not (
                    request.user.is_staff or request.user == course_teacher_user or
                    (hasattr(request.user, 'profile') and getattr(request.user.profile, 'is_teacher', False))
                ):
                    messages.error(request, '只有授課教師或管理員可以替學生加退選')
                    return redirect(request.META.get('HTTP_REFERER', reverse('main')))
        else:
            if not request.user.is_authenticated:
                messages.error(request, '請先登入以加退選課程')
                return redirect('login')
            student = request.user

        if action == 'enroll':
            Enrollment.objects.get_or_create(student=student, course=course)
            messages.success(request, f"{student.username} 已加入 {course.code}")
        else:
            Enrollment.objects.filter(student=student, course=course).delete()
            messages.success(request, f"{student.username} 已從 {course.code} 退選")

    return redirect(request.META.get('HTTP_REFERER', reverse('main')))


def register(request):
    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('course_enrollment_manage')
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
        return render(request, 'registration/login.html', {'show_register': True})
    return redirect('login')


@login_required
def edit_profile(request):
    if _is_teacher(request.user) or request.user.is_staff:
        return redirect(_post_login_url(request.user))
    profile = getattr(request.user, 'profile', None)
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            email = request.POST.get('email', '').strip()
            if email:
                request.user.email = email
                request.user.save(update_fields=['email'])
            messages.success(request, '個人資料已更新')
            return redirect('edit_profile')
    else:
        form = ProfileForm(instance=profile)
    return render(request, 'uiux/profile_edit.html', {
        'form': form,
        'active_nav': 'profile',
    })


@login_required
def student_courses(request):
    """Show student's enrolled courses with grades and semester average."""
    if _is_teacher(request.user) or request.user.is_staff:
        return redirect(_post_login_url(request.user))
        
    all_enrollments = Enrollment.objects.filter(student=request.user)
    semesters = sorted(list(set(all_enrollments.exclude(semester='').values_list('semester', flat=True))), reverse=True)
    if not semesters:
        semesters = ['本學期']
        
    selected_semester = request.GET.get('semester')
    
    enrollments = all_enrollments.select_related(
        'course', 'course__teacher', 'course__teacher__profile',
    )
    
    if selected_semester and selected_semester != 'all':
        enrollments = enrollments.filter(semester=selected_semester)
        semester_label = selected_semester
    elif selected_semester == 'all':
        semester_label = '歷年所有成績'
    else:
        # Default
        if semesters and semesters[0] != '本學期':
            semester_label = semesters[0]
            enrollments = enrollments.filter(semester=semesters[0])
            selected_semester = semesters[0]
        else:
            semester_label = '本學期'

    grade_rows = []
    total_credits = 0
    avg_values = []
    for e in enrollments:
        meta = _course_row_meta(e.course)
        mid = float(e.midterm_grade) if e.midterm_grade is not None else None
        fin = float(e.final_grade) if e.final_grade is not None else None
        avg = (mid + fin) / 2 if mid is not None and fin is not None else None
        if avg is not None:
            avg_values.append(avg)
        total_credits += meta['credits']
        grade_rows.append({
            'course': e.course,
            'teacher_name': meta['teacher_name'],
            'credits': meta['credits'],
            'midterm': e.midterm_grade,
            'final': e.final_grade,
            'avg': avg,
        })
    overall_avg = round(sum(avg_values) / len(avg_values), 1) if avg_values else None
    
    return render(request, 'uiux/student_grade_report.html', {
        'grade_rows': grade_rows,
        'total_credits': total_credits,
        'overall_avg': overall_avg,
        'semester_label': semester_label,
        'display_name': _user_display_name(request.user),
        'active_nav': 'grades',
        'semesters': semesters,
        'selected_semester': selected_semester,
    })


@login_required
def export_my_grades(request):
    """Export the student's own grades to CSV."""
    if _is_teacher(request.user) or request.user.is_staff:
        return redirect(_post_login_url(request.user))
        
    selected_semester = request.GET.get('semester')
    
    enrollments = Enrollment.objects.filter(student=request.user).select_related(
        'course', 'course__teacher', 'course__teacher__profile',
    )
    
    if selected_semester and selected_semester != 'all':
        enrollments = enrollments.filter(semester=selected_semester)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="my_grades.csv"'
    response.write(u'\ufeff'.encode('utf8'))  # BOM for Excel
    
    writer = csv.writer(response)
    writer.writerow(['學期', '課程代碼', '課程名稱', '授課教師', '學分', '期中成績', '期末成績', '學期成績'])
    
    for e in enrollments:
        meta = _course_row_meta(e.course)
        mid = float(e.midterm_grade) if e.midterm_grade is not None else None
        fin = float(e.final_grade) if e.final_grade is not None else None
        avg = (mid + fin) / 2 if mid is not None and fin is not None else ''
        
        writer.writerow([
            e.semester,
            e.course.code,
            e.course.name,
            meta['teacher_name'],
            meta['credits'],
            e.midterm_grade if e.midterm_grade is not None else '',
            e.final_grade if e.final_grade is not None else '',
            round(avg, 2) if avg != '' else ''
        ])
        
    return response


@login_required
def semester_average(request, semester):
    from django.db.models import Avg, F, ExpressionWrapper, FloatField
    qs = Enrollment.objects.filter(student=request.user, semester=semester)
    # compute per-enrollment avg then average across enrollments
    annotated = qs.annotate(enroll_avg=ExpressionWrapper((F('midterm_grade') + F('final_grade')) / 2.0, output_field=FloatField()))
    avg = annotated.aggregate(avg=Avg('enroll_avg'))['avg']
    return render(request, 'semester_average.html', {'semester': semester, 'avg': avg})


@user_passes_test(_is_teacher)
def remove_course(request, course_id):
    course = get_object_or_404(Course, id=course_id, teacher=request.user)
    if request.method == 'POST':
        course.delete()
        messages.success(request, '課程已刪除')
        return redirect('teacher_courses')
    return render(request, 'uiux/confirm_delete_course.html', {'course': course, 'active_nav': 'create_course'})


@login_required
def drop_course(request, enrollment_id):
    """Drop course for the logged-in student."""
    if request.method != 'POST':
        return redirect('course_enrollment_manage')
    enrollment = get_object_or_404(Enrollment, id=enrollment_id, student=request.user)
    course = enrollment.course
    enrollment.delete()
    messages.success(request, f'已從 {course.code} 退選')
    return redirect('course_enrollment_manage')


@login_required
def available_courses(request):
    """Show all courses available to enroll, with search functionality."""
    enrolled_course_ids = Enrollment.objects.filter(student=request.user).values_list('course_id', flat=True)
    available = Course.objects.exclude(id__in=enrolled_course_ids).order_by('code')
    
    # Handle search query
    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        available = available.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query)
        )
    
    return render(request, 'available_courses.html', {
        'courses': available,
        'search_query': search_query
    })


@login_required
def enroll_student_course(request, course_id):
    """Student enrolls in a course."""
    if request.method != 'POST':
        return redirect('course_enrollment_manage')
    course = get_object_or_404(Course, id=course_id)
    meta = _course_row_meta(course)
    if meta['is_full']:
        messages.error(request, f'{course.code} 已額滿，無法加選')
        return redirect('course_enrollment_manage')
    enrollment, created = Enrollment.objects.get_or_create(student=request.user, course=course)
    if created:
        messages.success(request, f'已加選 {course.code}')
    else:
        messages.info(request, f'您已經加選 {course.code}')
    return redirect('course_enrollment_manage')


@login_required
def course_enrollment_manage(request):
    """Student course enrollment hub: available courses + enrolled courses."""
    if _is_teacher(request.user) or request.user.is_staff:
        return redirect(_post_login_url(request.user))

    enrolled_qs = Enrollment.objects.filter(student=request.user).select_related(
        'course', 'course__teacher', 'course__teacher__profile',
    )
    enrolled_ids = enrolled_qs.values_list('course_id', flat=True)

    available_qs = Course.objects.exclude(id__in=enrolled_ids).select_related(
        'teacher', 'teacher__profile',
    ).annotate(enrolled_count=Count('enrollments')).order_by('code')

    search_query = request.GET.get('search', '').strip()
    if search_query:
        from django.db.models import Q
        available_qs = available_qs.filter(
            Q(name__icontains=search_query) | Q(code__icontains=search_query),
        )

    enrolled_rows = []
    for enrollment in enrolled_qs:
        meta = _course_row_meta(enrollment.course)
        enrolled_rows.append({
            'enrollment': enrollment,
            'course': enrollment.course,
            **meta,
        })

    available_rows = []
    for course in available_qs:
        meta = _course_row_meta(course)
        available_rows.append({'course': course, **meta})

    return render(request, 'uiux/course_enrollment_manage.html', {
        'enrolled_rows': enrolled_rows,
        'available_rows': available_rows,
        'display_name': _user_display_name(request.user),
        'search_query': search_query,
        'active_nav': 'enrollment',
    })


@login_required
def student_schedule(request):
    """Student schedule — list view until Course has time-slot fields."""
    if _is_teacher(request.user) or request.user.is_staff:
        return redirect(_post_login_url(request.user))
    enrollments = Enrollment.objects.filter(student=request.user).select_related(
        'course', 'course__teacher', 'course__teacher__profile',
    )
    schedule_rows = []
    for i, enrollment in enumerate(enrollments):
        meta = _course_row_meta(enrollment.course)
        schedule_rows.append({
            'course': enrollment.course,
            'teacher_name': meta['teacher_name'],
            'schedule': meta['schedule'],
            'credits': meta['credits'],
            'color': SCHEDULE_COLORS[i % len(SCHEDULE_COLORS)],
        })
    semester_label = '本學期'
    first_enrollment = enrollments.first()
    if first_enrollment and first_enrollment.semester:
        semester_label = first_enrollment.semester
    return render(request, 'uiux/student_schedule.html', {
        'schedule_rows': schedule_rows,
        'semester_label': semester_label,
        'active_nav': 'schedule',
    })


@login_required
def add_comment(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            c = form.save(commit=False)
            c.user = request.user
            c.course = course
            c.save()
            messages.success(request, '留言已新增')
    return redirect('course_detail', course_id=course_id)


@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user:
        messages.error(request, '沒有權限編輯這則留言')
        return redirect('course_detail', course_id=comment.course.id)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, '留言已更新')
            return redirect('course_detail', course_id=comment.course.id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'comment_edit.html', {'form': form, 'comment': comment})


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user and not request.user.is_staff:
        messages.error(request, '沒有權限刪除這則留言')
        return redirect('course_detail', course_id=comment.course.id)
    course_id = comment.course.id
    comment.delete()
    messages.success(request, '留言已刪除')
    return redirect('course_detail', course_id=course_id)


@login_required
def create_teacher(request):
    """Admin-only view to create a new teacher account."""
    if not request.user.is_staff:
        messages.error(request, '只有管理員可以建立教師帳號')
        return redirect('main')
    
    if request.method == 'POST':
        form = CreateTeacherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, '教師帳號建立成功')
            return redirect('create_teacher')
    else:
        form = CreateTeacherForm()
    
    return render(request, 'uiux/admin_create_teacher.html', {
        'form': form,
        'active_nav': 'create_teacher',
    })