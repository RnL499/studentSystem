from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from grades.models import Course, Enrollment, Profile, Teacher
from django.db import transaction

class Command(BaseCommand):
    help = 'Load demo users, teachers, courses and enrollments for presentation/demo.'

    def handle(self, *args, **options):
        demo_students = [
            ('s001', 'student one'),
            ('s002', 'student two'),
            ('s003', 'student three'),
            ('s004', 'student four'),
        ]
        demo_teachers = [
            ('t001', 'Prof. Alice'),
            ('t002', 'Dr. Bob'),
        ]

        demo_courses = [
            ('CS101', 'Introduction to Programming', 'MON_1,MON_2,TUE_3', 't001'),
            ('MATH201', 'Calculus I', 'TUE_2,THU_2', 't002'),
            ('ENG103', 'Academic English', 'WED_3,FRI_3', 't001'),
            ('HIST210', 'World History', 'MON_4,THU_4', None),
        ]

        with transaction.atomic():
            # Create teachers
            for username, fullname in demo_teachers:
                user, created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
                if created:
                    user.set_password('password')
                    user.save()
                profile = getattr(user, 'profile', None)
                if profile:
                    profile.full_name = fullname
                    profile.is_teacher = True
                    profile.save()
                else:
                    Profile.objects.update_or_create(user=user, defaults={'full_name': fullname, 'is_teacher': True})

            # Create students
            for username, fullname in demo_students:
                user, created = User.objects.get_or_create(username=username, defaults={'email': f'{username}@example.com'})
                if created:
                    user.set_password('password')
                    user.save()
                profile = getattr(user, 'profile', None)
                if profile:
                    profile.full_name = fullname
                    profile.is_teacher = False
                    profile.save()
                else:
                    Profile.objects.update_or_create(user=user, defaults={'full_name': fullname, 'is_teacher': False})

            # Create teacher model entries (optional)
            for username, _ in demo_teachers:
                try:
                    tuser = User.objects.get(username=username)
                    Teacher.objects.get_or_create(user=tuser)
                except User.DoesNotExist:
                    continue

            # Create courses
            for code, name, schedule, teacher_username in demo_courses:
                if teacher_username:
                    try:
                        teacher = User.objects.get(username=teacher_username)
                    except User.DoesNotExist:
                        teacher = None
                else:
                    teacher = None
                course, created = Course.objects.get_or_create(code=code, defaults={'name': name, 'schedule': schedule, 'teacher': teacher, 'credits': 3})
                if not created:
                    course.name = name
                    course.schedule = schedule
                    course.teacher = teacher
                    course.credits = 3
                    course.save()

            # Create enrollments
            # s001 in CS101 (approved), MATH201 (approved)
            # s002 in CS101 (pending)
            # s003 in ENG103 (approved)
            s1 = User.objects.get(username='s001')
            s2 = User.objects.get(username='s002')
            s3 = User.objects.get(username='s003')
            cs101 = Course.objects.get(code='CS101')
            math201 = Course.objects.get(code='MATH201')
            eng103 = Course.objects.get(code='ENG103')

            Enrollment.objects.update_or_create(student=s1, course=cs101, defaults={'approved': True})
            Enrollment.objects.update_or_create(student=s1, course=math201, defaults={'approved': True})
            Enrollment.objects.update_or_create(student=s2, course=cs101, defaults={'approved': False})
            Enrollment.objects.update_or_create(student=s3, course=eng103, defaults={'approved': True})

        self.stdout.write(self.style.SUCCESS('Demo data loaded.'))
