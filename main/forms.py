from django import forms
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.utils.safestring import mark_safe
from user.models import User, EmailInvitation


PERSONAL_DATA_WIDGETS = {
    "gender": forms.RadioSelect(),
    "date_of_birth": forms.TextInput(attrs={"placeholder": "DD-MM-YYYY"}),
}


class EmailInvitationForm(forms.ModelForm):
    class Meta:
        model = EmailInvitation
        fields = ('email', 'invitation_type', 'inviter_type', 'inviter_id')

    def clean(self):
        cleaned_data = super(EmailInvitationForm, self).clean()
        self._validate_unique = False
        return cleaned_data

    def save(self, *args, **kw):
        try:
            invitation = EmailInvitation.objects.get(
                email=self.cleaned_data.get('email'),
                inviter_type=self.cleaned_data.get('inviter_type'),
                inviter_id=self.cleaned_data.get('inviter_id'),
                invitation_type=self.cleaned_data.get('invitation_type'))
        except ObjectDoesNotExist:
            invitation = super(EmailInvitationForm, self).save(*args, **kw)

        invitation.send()
        return invitation


class BetaSmartzAgreementForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(BetaSmartzAgreementForm, self).clean()

        if not (cleaned_data["betasmartz_agreement"] is True):
            self._errors['betasmartz_agreement'] ='You must accept the BetaSmartz\'s agreement'

        return cleaned_data


class BetaSmartzGenericUserSignupForm(BetaSmartzAgreementForm):
    confirm_password = forms.CharField(max_length=50,
                                       widget=forms.PasswordInput())
    password = forms.CharField(max_length=50, widget=forms.PasswordInput())
    user_profile_type = None

    def clean(self):
        cleaned_data = super(BetaSmartzGenericUserSignupForm, self).clean()
        self._validate_unique = False

        password1 = cleaned_data.get('password')
        password2 = cleaned_data.get('confirm_password')

        if password1 and (password1 != password2):
            self._errors['confirm_password'] = ['Passwords don\'t match',]

        # check if user already exist
        try:
            user = User.objects.get(email=cleaned_data.get('email'))
        except User.DoesNotExist:
            user = None

        if (user is not None) and (not user.prepopulated):
            # confirm password
            if not user.check_password(password1):
                self._errors['email'] = ['User already exists',]
            else:
                if hasattr(user, self.user_profile_type):
                    rupt = self.user_profile_type.replace("_", " ")
                    self._errors['email'] = ['User already has an {0} account'.format(rupt),]

        cleaned_data["password"] = make_password(password1)
        return cleaned_data

    def save(self, *args, **kw):
        # check if user already exist
        try:
            self.instance = User.objects.get(
                email=self.cleaned_data.get('email'))
        except User.DoesNotExist:
            pass
        instance = super(BetaSmartzGenericUserSignupForm, self).save(*args, **kw)
        instance.prepopulated = False
        instance.password = self.cleaned_data["password"]
        instance.save()
        return instance
