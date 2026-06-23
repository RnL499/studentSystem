from django.db import models
from django.core.validators import MinValueValidator
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=150, blank=True, verbose_name="姓名")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="個人頭像")
    is_teacher = models.BooleanField(default=False, verbose_name="是否為教師")

    def __str__(self):
        return self.full_name or self.user.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    department = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.department}"


class Course(models.Model):
    SCHEDULE_CHOICES = [
        ('週一', [
            ('MON_1', '第1節 08:00-09:00'),
            ('MON_2', '第2節 09:10-10:10'),
            ('MON_3', '第3節 10:20-11:20'),
            ('MON_4', '第4節 11:30-12:30'),
            ('MON_5', '第5節 13:30-14:30'),
            ('MON_6', '第6節 14:40-15:40'),
            ('MON_7', '第7節 15:50-16:50'),
            ('MON_8', '第8節 17:00-18:00'),
        ]),
        ('週二', [
            ('TUE_1', '第1節 08:00-09:00'),
            ('TUE_2', '第2節 09:10-10:10'),
            ('TUE_3', '第3節 10:20-11:20'),
            ('TUE_4', '第4節 11:30-12:30'),
            ('TUE_5', '第5節 13:30-14:30'),
            ('TUE_6', '第6節 14:40-15:40'),
            ('TUE_7', '第7節 15:50-16:50'),
            ('TUE_8', '第8節 17:00-18:00'),
        ]),
        ('週三', [
            ('WED_1', '第1節 08:00-09:00'),
            ('WED_2', '第2節 09:10-10:10'),
            ('WED_3', '第3節 10:20-11:20'),
            ('WED_4', '第4節 11:30-12:30'),
            ('WED_5', '第5節 13:30-14:30'),
            ('WED_6', '第6節 14:40-15:40'),
            ('WED_7', '第7節 15:50-16:50'),
            ('WED_8', '第8節 17:00-18:00'),
        ]),
        ('週四', [
            ('THU_1', '第1節 08:00-09:00'),
            ('THU_2', '第2節 09:10-10:10'),
            ('THU_3', '第3節 10:20-11:20'),
            ('THU_4', '第4節 11:30-12:30'),
            ('THU_5', '第5節 13:30-14:30'),
            ('THU_6', '第6節 14:40-15:40'),
            ('THU_7', '第7節 15:50-16:50'),
            ('THU_8', '第8節 17:00-18:00'),
        ]),
        ('週五', [
            ('FRI_1', '第1節 08:00-09:00'),
            ('FRI_2', '第2節 09:10-10:10'),
            ('FRI_3', '第3節 10:20-11:20'),
            ('FRI_4', '第4節 11:30-12:30'),
            ('FRI_5', '第5節 13:30-14:30'),
            ('FRI_6', '第6節 14:40-15:40'),
            ('FRI_7', '第7節 15:50-16:50'),
            ('FRI_8', '第8節 17:00-18:00'),
        ]),
    ]

    name = models.CharField(max_length=100, verbose_name="課程名稱")
    code = models.CharField(max_length=20, unique=True, verbose_name="課程號碼")
    description = models.TextField(blank=True, verbose_name="課程描述")
    schedule = models.CharField(max_length=200, blank=False, verbose_name="上課時間")
    credits = models.PositiveSmallIntegerField(default=3, verbose_name="學分數")
    teacher = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='teaching_courses',
        verbose_name="任課教師",
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def schedule_list(self):
        if not self.schedule:
            return []
        return [item.strip() for item in self.schedule.split(',') if item.strip()]

    @property
    def schedule_labels(self):
        mapping = {code: label for _, choices in self.SCHEDULE_CHOICES for code, label in choices}
        return [mapping.get(code, code) for code in self.schedule_list]

    @property
    def schedule_display(self):
        if not self.schedule_list:
            return '未設定'
        return ', '.join(self.schedule_labels)

    def enrolled_students(self):
        return User.objects.filter(enrollment__course=self)


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="學生", related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程", related_name='enrollments')
    semester = models.CharField(max_length=20, blank=True, default='', verbose_name="學期")
    approved = models.BooleanField(default=False, verbose_name="審核通過")
    requested_at = models.DateTimeField(default=timezone.now, verbose_name="申請時間")
    # Allow larger numeric ranges for scores (e.g. up to 99999.99 if needed)
    midterm_grade = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="期中成績",
        validators=[MinValueValidator(0)],
    )
    final_grade = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="期末成績",
        validators=[MinValueValidator(0)],
    )

    def __str__(self):
        return f"{self.student.username} 選修 {self.course.code} ({self.semester})"

    class Meta:
        verbose_name = "選課紀錄"
        verbose_name_plural = "選課紀錄管理"


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="使用者", related_name='comments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="課程", related_name='comments')
    content = models.TextField(verbose_name="留言內容")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} @ {self.course.code}: {self.content[:30]}"


# Helper: compute a student's average grade across all enrollments (both midterm and final)
def _user_avg_grade(self):
    qs = Enrollment.objects.filter(student=self)
    total = 0.0
    count = 0
    for e in qs:
        for g in (e.midterm_grade, e.final_grade):
            if g is not None:
                try:
                    total += float(g)
                    count += 1
                except (TypeError, ValueError):
                    continue
    if count == 0:
        return None
    return round(total / count, 2)


def _user_avg_for_semester(self, semester):
    qs = Enrollment.objects.filter(student=self, semester=semester)
    total = 0.0
    count = 0
    for e in qs:
        for g in (e.midterm_grade, e.final_grade):
            if g is not None:
                try:
                    total += float(g)
                    count += 1
                except (TypeError, ValueError):
                    continue
    if count == 0:
        return None
    return round(total / count, 2)


# Attach helpers to User
User.avg_grade = _user_avg_grade
User.avg_grade_for_semester = _user_avg_for_semester


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # ensure a profile exists for existing users
        Profile.objects.get_or_create(user=instance)