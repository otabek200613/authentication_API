import uuid
from datetime import timedelta
import random
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from shared.models import BaseModel
from django.db import models

NEW, CODE, DONE, PHOTO_DONE = ('new', 'code', 'done', 'photo_done')
ORDINARY, MANAGER, ADMIN = ('ordinary', 'manager', 'admin')


class User(AbstractUser, BaseModel):
    AUTH_STATUS_CHOICES = (
        (NEW, NEW),
        (CODE, CODE),
        (DONE, DONE),
        (PHOTO_DONE, PHOTO_DONE),
    )
    USER_ROLES = (
        (ORDINARY, ORDINARY),
        (MANAGER, MANAGER),
        (ADMIN, ADMIN),
    )
    auth_status = models.CharField(max_length=10, choices=AUTH_STATUS_CHOICES, default=NEW)
    user_role = models.CharField(max_length=10, choices=USER_ROLES, default=ORDINARY)
    phone_number = models.CharField(max_length=15, unique=True)
    photo = models.ImageField(upload_to='user/photos', null=True, blank=True)

    def __str__(self):
        return f'{self.phone_number}-{self.username or "Mavjud emas"}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def create_verify_code(self):
        code = "".join([str(random.randint(0, 10000) % 10) for _ in range(4)])
        Confirmation.objects.update_or_create(
            user_id=self.id,
            defaults={'code': code, 'is_confirmed': False}
        )
        return code

    def check_username(self):
        if not self.username:
            temp_username = f'username-{uuid.uuid4().__str__().split("-")[-1]}'  # instagram-23324fsdf
            while User.objects.filter(username=temp_username):
                temp_username = f"{temp_username}{random.randint(0, 9)}"
            self.username = temp_username

    def check_pass(self):
        if not self.password:
            temp_password = f'password-{uuid.uuid4().__str__().split("-")[-1]}'  # 123456mfdsjfkd
            self.password = temp_password

    def hashing_password(self):
        from django.contrib.auth.hashers import identify_hasher
        try:
            identify_hasher(self.password)
        except ValueError:
            self.set_password(self.password)

    def token(self):
        refresh = RefreshToken.for_user(self)
        return {
            "access": str(refresh.access_token),
            "refresh_token": str(refresh)
        }


    def save(self, *args, **kwargs):
        self.clean()
        super(User, self).save(*args, **kwargs)


    def clean(self):
        self.check_username()
        self.check_pass()
        self.hashing_password()


class Confirmation(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=4)
    expiration_time = models.DateTimeField(null=True, blank=True)
    is_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.phone_number}-{self.code}'

    def save(self, *args, **kwargs):
        self.expiration_time = timezone.now() + timedelta(minutes=2)
        super(Confirmation, self).save(*args, **kwargs)