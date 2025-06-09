from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, get_user_model
from django.utils.translation import gettext as _
from .models import Question, CustomUser


class UserLoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self, *args, **kwargs):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("This user does not exists")
            if not user.check_password(password):
                raise forms.ValidationError("Incorrect password")
            if not user.is_active:
                raise forms.ValidationError("This user is not active")
        return super(UserLoginForm, self).clean(*args, **kwargs)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super(RegistrationForm, self).save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']

        if commit:
            user.save()

        return user


class UploadFileForm(forms.Form):
    file = forms.FileField()


from django import forms
from .models import ExperimentReport

class ExperimentReportForm(forms.ModelForm):
    class Meta:
        model = ExperimentReport
        fields = ['observation', 'data', 'report_file']
        widgets = {
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'data': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'report_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'observation': 'Observation',
            'data': 'Data Collected',
            'report_file': 'Attach Report File (optional)',
        }

