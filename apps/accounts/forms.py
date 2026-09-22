from django import forms

INPUT_CLASSES = (
    "w-full rounded-xl border border-slate-300 px-4 py-3 text-slate-900 "
    "outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
)


class RegisterForm(forms.Form):
    full_name = forms.CharField(
        label="Full Name",
        max_length=200,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "autocomplete": "name"}),
    )
    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "autocomplete": "username"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": INPUT_CLASSES, "autocomplete": "email"}),
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={"class": INPUT_CLASSES, "autocomplete": "tel"}),
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"class": INPUT_CLASSES, "autocomplete": "new-password"}),
    )
