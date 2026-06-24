from django import forms
from django.contrib.auth.models import User, Group
from django.contrib.auth.forms import UserCreationForm
from .models import Profile, Teacher, Course

from .models import Comment


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={'rows':3, 'class':'form-control', 'placeholder':'在此留言...'}),
        }


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('full_name', 'avatar')


class CourseForm(forms.ModelForm):
    schedule = forms.MultipleChoiceField(
        choices=[(code, label) for _, choices in Course.SCHEDULE_CHOICES for code, label in choices],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'schedule-grid'}),
        required=True,
        label='課程時間',
    )
    credits = forms.IntegerField(min_value=1, max_value=10, required=True, label='學分數')
    capacity = forms.IntegerField(min_value=1, max_value=500, required=True, label='課程人數上限')

    class Meta:
        model = Course
        fields = ('name', 'code', 'teacher', 'credits', 'capacity', 'schedule', 'description')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False
        self.fields['schedule'].required = True
        if self.instance and self.instance.pk and self.instance.schedule:
            self.initial['schedule'] = self.instance.schedule.split(',')
        if 'teacher' in self.fields:
            self.fields['teacher'].queryset = User.objects.filter(profile__is_teacher=True)

    def clean(self):
        cleaned_data = super().clean()
        schedule = cleaned_data.get('schedule')
        code = cleaned_data.get('code')

        if not code:
            cleaned_data['code'] = self.generate_code_from_schedule(schedule)

        return cleaned_data

    def clean_code(self):
        code = self.cleaned_data.get('code')
        if not code:
            code = self.generate_code_from_schedule(self.cleaned_data.get('schedule'))
        return code

    def clean_schedule(self):
        schedule = self.cleaned_data.get('schedule')
        if isinstance(schedule, list):
            return ','.join(schedule)
        return schedule

    def save(self, commit=True):
        instance = super().save(commit=False)
        schedule = self.cleaned_data.get('schedule')
        if isinstance(schedule, list):
            instance.schedule = ','.join(schedule)
        if commit:
            instance.save()
            self.save_m2m()
        return instance

    def generate_code_from_schedule(self, schedule):
        if not schedule:
            base = 'CRS'
        else:
            if isinstance(schedule, list):
                schedule = schedule[0]
            if isinstance(schedule, str) and ',' in schedule:
                schedule = schedule.split(',')[0]
            base = ''.join([c for c in str(schedule).split()[0] if c.isalnum()]).upper()[:6] or 'CRS'
        base = base[:6]
        suffix = 1
        code = f"{base}{suffix:02d}"
        while Course.objects.filter(code=code).exists():
            suffix += 1
            code = f"{base}{suffix:02d}"
        return code


class CourseEditForm(CourseForm):
    class Meta(CourseForm.Meta):
        fields = ('name', 'code', 'teacher', 'credits', 'capacity', 'schedule', 'description')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and not user.is_staff:
            if 'teacher' in self.fields:
                self.fields['teacher'].disabled = True


class StudentRegistrationForm(UserRegistrationForm):
    """Registration form for students; ensure profile.is_teacher=False on save."""
    full_name = forms.CharField(max_length=150, required=True, label='中文姓名')

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.is_teacher = False
            profile.full_name = self.cleaned_data.get('full_name', '')
            profile.save()
        return user


class GradeForm(forms.ModelForm):
    class Meta:
        model = None  # set in __init__ to Enrollment
        fields = ('midterm_grade', 'final_grade')

    midterm_grade = forms.DecimalField(max_digits=7, decimal_places=2, required=False, min_value=0, label='期中')
    final_grade = forms.DecimalField(max_digits=7, decimal_places=2, required=False, min_value=0, label='期末')

    def __init__(self, *args, **kwargs):
        # Accept an Enrollment instance via 'instance'
        self.instance = kwargs.get('instance', None)
        # dynamically set Meta.model to Enrollment to satisfy ModelForm behavior
        from .models import Enrollment
        self.__class__.Meta.model = Enrollment
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields['midterm_grade'].initial = getattr(self.instance, 'midterm_grade', None)
            self.fields['final_grade'].initial = getattr(self.instance, 'final_grade', None)

    def __init__(self, *args, **kwargs):
        # Accept an Enrollment instance via 'instance'
        self.instance = kwargs.get('instance', None)
        super().__init__(*args, **kwargs)
        if self.instance is not None:
            self.fields['midterm_grade'].initial = getattr(self.instance, 'midterm_grade', None)
            self.fields['final_grade'].initial = getattr(self.instance, 'final_grade', None)

    def save(self, commit=True):
        if self.instance is None:
            raise ValueError('GradeForm requires an Enrollment instance via ``instance`` kwarg')
        self.instance.midterm_grade = self.cleaned_data.get('midterm_grade')
        self.instance.final_grade = self.cleaned_data.get('final_grade')
        if commit:
            self.instance.save()
        return self.instance


class CreateTeacherForm(UserCreationForm):
    """Form for admin to create a new teacher account."""
    email = forms.EmailField(required=False)
    full_name = forms.CharField(max_length=100, required=False, label='教師姓名')
    department = forms.ChoiceField(
        choices=[
            ('資訊管理學系', '資訊管理學系'),
            ('數位內容設計系', '數位內容設計系'),
            ('企業管理學系', '企業管理學系'),
        ],
        required=False,
        label='所屬系所'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'full_name', 'department')

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            # Teachers are not staff by default; admin manages them
            user.save()
            # Create or update profile with is_teacher=True
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.is_teacher = True
            profile.full_name = self.cleaned_data.get('full_name', '')
            profile.save()
            # Ensure 'Teacher' group exists and add the user to it
            teacher_group, _ = Group.objects.get_or_create(name='Teacher')
            user.groups.add(teacher_group)
            # Create Teacher model instance with department if provided
            department = self.cleaned_data.get('department', '')
            Teacher.objects.update_or_create(user=user, defaults={'department': department})
        return user
