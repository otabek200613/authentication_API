import random
import uuid
from datetime import  timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models

from shared.models import BaseModel

ORDINARY_USER,MANAGER,ADMIN = ("ordinary_user","manager","admin")
VIA_EMAIL = ("via_email",)
NEW,CODE_VERIFIED,DONE,PHOTO_DONE = ('new','code_verified','done','photo_done')




class User(AbstractUser,BaseModel):
    ROLES = (
        (ORDINARY_USER,ORDINARY_USER),
        (MANAGER,MANAGER),
        (ADMIN,ADMIN),
    )
    STATUS_CHOICES = (
        (NEW,NEW),
        (CODE_VERIFIED,CODE_VERIFIED),
        (DONE,DONE),
        (PHOTO_DONE,PHOTO_DONE),
    )
    roles = models.CharField(max_length=20,choices=ROLES,default=ORDINARY_USER)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default=NEW)
    email = models.EmailField(unique=True)
    photo = models.ImageField(upload_to='users/%Y/%m',blank=True,null=True,
                              validators=[FileExtensionValidator(['jpg','png','jpeg','heic','heif','png'])])
    def __str__(self):
        return self.username
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def create_verify_code(self):
        code = "".join([str(random.randint(0, 10000) % 10) for _ in range(4)])

        UserConfirmation.objects.update_or_create(
            user=self,
            defaults={
                "code": code,
                "is_confirmed": False,
            }
        )
        return code
    def check_username(self):
        if not self.username:
            temporary_username = f"username-{uuid.uuid4().__str__().split('-')[-1]}"
            while User.objects.filter(username=temporary_username).exists():
                temporary_username = (f""
                                       f"{temporary_username}{random.randint(0,9)}")
            self.username = temporary_username

    def check_email(self):
        if self.email:
            self.email=self.email.lower()

    def check_pass(self):
        if not self.password:
            temporary_password = f"password-{uuid.uuid4().__str__().split('-')[-1]}"
            self.password = temporary_password

    def hashing_password(self):
        if not self.password.startswith('pbkdf2_sha256'):
            self.set_password(self.password)

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }


    def clean(self):
        self.check_email()
        self.check_username()
        self.check_pass()
        self.hashing_password()

    def save(self,*args, **kwargs):
        self.clean()
        super(User,self).save(*args,**kwargs)

class UserConfirmation(BaseModel):
    code = models.CharField(max_length=4)
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='confirmation_code')
    expiration_date = models.DateTimeField(null=True)
    is_confirmed = models.BooleanField(default=False)
    def __str__(self):
        return str(self.user.__str__())

    def save(self, *args, **kwargs):
        if not self.expiration_date:
            self.expiration_date = timezone.now() + timedelta(minutes=5)
        super().save(*args, **kwargs)