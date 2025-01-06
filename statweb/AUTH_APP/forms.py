from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.contrib.auth import authenticate
from django.utils.text import slugify
from django import forms
from .models import *
import re

class CustomLoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=254)
    motdepass = forms.CharField(label='Password', strip=False, widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('motdepass')

        if email and password:
            user = authenticate(request=self.request, username=email, password=password)
            if not user:
                raise forms.ValidationError('Invalid email or password')
        return self.cleaned_data

    def get_user(self):
        return self.user_cache
class UsersForm(forms.ModelForm):
    motdepass_confirm = forms.CharField(widget=forms.PasswordInput)
    motdepass = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Users
        fields = ["email", "first_name", "last_name", "motdepass"]

    def save(self, commit=True):
        cleaned_data = self.cleaned_data
        email = cleaned_data['email']
        last_name= cleaned_data['last_name']
        first_name = cleaned_data['first_name']
        base_username = slugify(email.split('@')[0])
        username = base_username
        counter = 1
        while Users.objects.filter(username=username).exists():
            username = f"{base_username}-{counter}"
            counter += 1
        user = Users(
            last_name=last_name,
            first_name=first_name,
            username=username,
            email=email,
            password=make_password(cleaned_data['motdepass'])
        )
        if commit:
            user.save()
            return user



    def clean_motdepass(self):
        motdepass = self.cleaned_data.get('motdepass')
        
        if len(motdepass) < 8 or len(motdepass) > 16:
            raise ValidationError('Password must be between 8 and 16 characters.')
        if not re.search(r'[A-Z]', motdepass):
            raise ValidationError('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', motdepass):
            raise ValidationError('Password must contain at least one lowercase letter.')
        if not re.search(r'[0-9]', motdepass):
            raise ValidationError('Password must contain at least one number.')
        if not re.search(r'[\W_]', motdepass):  
            raise ValidationError('Password must contain at least one special character.')
        
        return motdepass


    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not re.match(r'^[a-zA-Z]+$', first_name):
            raise ValidationError('First name can only contain letters.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not re.match(r'^[a-zA-Z]+$', last_name):
            raise ValidationError('Last name can only contain letters.')
        return last_name




    def clean(self):
        cleaned_data = super().clean()
        first_name = cleaned_data.get('first_name')
        last_name = cleaned_data.get('last_name')
        email = cleaned_data.get('email')
        motdepass = cleaned_data.get('motdepass')
        motdepass_confirm = cleaned_data.get('motdepass_confirm')

        if email and Users.objects.filter(email=email).exists() :
            self.add_error('email', 'This email already exists.')

            
            
        if not last_name and not first_name:
            pass    
        
        elif last_name and first_name and Users.objects.filter(first_name=first_name, last_name=last_name).exists():
            self.add_error('first_name', 'This first name already exists.')
            self.add_error('last_name', 'This last name already exists.')
            
        elif first_name == last_name :
            self.add_error('first_name', 'You cant put youre first name the same as youre last name.')
            self.add_error('last_name', 'You cant put youre last name the same as youre first name.')
            
        if motdepass and motdepass_confirm and motdepass != motdepass_confirm:
            self.add_error('motdepass_confirm', 'Passwords do not match.')
            self.add_error('motdepass', 'Passwords do not match.')
        
        return cleaned_data
    
class ExcelUploadForm(forms.Form):
    file = forms.FileField()
    name = forms.CharField(max_length=255, required=True, label='Custom File Name')
    class Meta:
        model = UserExcelFile
        fields = ["name","file"]
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def clean_name(self):
        name = self.cleaned_data.get('name')

        if UserExcelFile.objects.filter(name=name,user=self.user).exists():
            raise ValidationError('This file name already exists for your uploads.')

        return name
