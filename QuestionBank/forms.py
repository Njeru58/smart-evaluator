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
        fields = [
            'group_members',
            'objective',
            'theory',
            'apparatus_scope',
            'procedure',
            'results',
            'data_analysis',
            'discussion',
            'conclusion',
            'references',
            'observation',
            'data',
            'graph_x_values',
            'graph_y_values',
            'report_file'
        ]
        widgets = {
            'group_members': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'objective': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'theory': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'apparatus_scope': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'procedure': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'results': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'data_analysis': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'discussion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'conclusion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'references': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'data': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'graph_x_values': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g. 0, 2, 4, 6, 8'
            }),
            'graph_y_values': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g. 10, 15, 22, 28, 35'
            }),
            'report_file': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'group_members': 'Group Members',
            'objective': 'Aim/Objectives of the Experiment',
            'theory': 'Introduction / Theory',
            'apparatus_scope': 'Apparatus Used',
            'procedure': 'Method / Procedure',
            'results': 'Experimental Results',
            'data_analysis': 'Data & Error Analysis',
            'discussion': 'Discussion',
            'conclusion': 'Conclusion',
            'references': 'References',
            'observation': 'Auto-filled Observation',
            'data': 'Auto-filled Data',
            'graph_x_values': 'X-Axis Values (comma-separated)',
            'graph_y_values': 'Y-Axis Values (comma-separated)',
            'report_file': 'Attach Report File (optional)',
        }


from django import forms
from .models import ExperimentDraft

class ExperimentDraftForm(forms.ModelForm):
    class Meta:
        model = ExperimentDraft
        fields = ['observation', 'data', 'image']
        widgets = {
            'observation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Write your observations here...'
            }),
            'data': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Record your data points or values here...'
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            })
        }
