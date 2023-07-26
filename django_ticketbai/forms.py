from django import forms


class ConfigForm(forms.ModelForm):
    password = forms.CharField(max_length=200, widget=forms.PasswordInput)
