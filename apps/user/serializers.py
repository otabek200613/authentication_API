from attr import attrs
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import authentication_classes
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from twilio.jwt.access_token import AccessToken

from shared.utiliy import send_email, check_email_or_phone, check_user_type
from .models import User, UserConfirmation, VIA_PHONE, VIA_EMAIL, CODE_VERIFIED, NEW, DONE, PHOTO_DONE


class SignUpSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(SignUpSerializer, self).__init__(*args, **kwargs)
        self.fields['email_phone_number'] = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ('id', 'auth_type', 'status')
        extra_kwargs = {
            'auth_type': {'read_only': True, 'required': False},
            'status': {'read_only': True, 'required': False},
        }

    def create(self, validated_data):
        user = super(SignUpSerializer, self).create(validated_data)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verify_code(VIA_EMAIL)
            send_email(user.email, code)

        elif user.auth_type == VIA_PHONE:
            code = user.create_verify_code(VIA_PHONE)
            send_email(user.email, code)
        user.save()
        return user

    def validate(self, data):
        super(SignUpSerializer, self).validate(data)
        data = self.auth_validate(data)
        return data

    @staticmethod
    def auth_validate(data):
        user_input = str(data.get('email_phone_number')).lower()
        input_type = check_email_or_phone(user_input)
        if input_type == 'email':
            data = {
                'email': user_input,
                'auth_type': VIA_EMAIL,
            }
        elif input_type == 'phone':
            data = {
                'phone_number': user_input,
                'auth_type': VIA_PHONE,
            }
        else:
            data = {
                'success': False,
                "message": "Telefon raqam yoki emailda xatolik"
            }
            raise ValidationError(data)
        return data

    def validate_email_phone_number(self, value):
        value = value.lower()
        if value and User.objects.filter(email=value).exists():
            data = {
                'success': False,
                "message": "Email bazada mavjud"
            }
            raise ValidationError(data)
        elif value and User.objects.filter(phone=value).exists():
            data = {
                'success': False,
                "message": "Phone bazada mavjud"

            }
            raise ValidationError(data)
        return value

    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)
        data.update(instance.token())
        return data


class ChangeUserInformation(serializers.Serializer):
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    username = serializers.CharField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)
        if password != confirm_password:
            raise ValidationError({
                'message': 'Passwords must match',
            })
        if password:
            validate_password(password)
            validate_password(confirm_password)
        return data

    def validate_username(self, username):
        if len(username) < 6 or len(username) > 20:
            raise ValidationError({
                'message': 'Username must be between 6 and 20 characters',
            })
        if username.isdigit():
            raise ValidationError({
                'message': 'Username must not be number',
            })
        return username

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.password = validated_data.get('password', instance.password)
        if validated_data.get('password'):
            instance.set_password(validated_data.get('password'))
        if instance.status == CODE_VERIFIED:
            instance.status = DONE
        instance.save()
        return instance


class ChangeUserPhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(validators=[FileExtensionValidator(['jpg', 'png', 'jpeg', 'heic', 'heif'])])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo')
        if photo:
            instance.photo = photo
            instance.status = PHOTO_DONE
            instance.save()
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(LoginSerializer, self).__init__(*args, **kwargs)
        self.fields['username'] = serializers.CharField(required=True)
        self.fields['userinput'] = serializers.CharField(required=True)
    def aut_validete(self,data):
        user_input = data.get('userinput')
        if check_user_type(user_input) == 'usernaem':
            username = user_input
        elif check_user_type(user_input) == 'email':
            user= self.get_user(email__iexact=user_input)
            username = user.username
        elif check_user_type(user_input) == 'phone':
            user = self.get_user(phone_number=user_input)
            username = user.username
        else:
            data = {
                'success': False,
                'message' : 'Siz email,username yoki telefon raqam kiritishingiz kerak'
            }
            raise ValidationError(data)
        authentication_kwargs = {
            self.username_field: username,
            'password': data['password'],
        }
        current_user = User.objects.filter(username__iexact=username).first()

        if current_user is not None and current_user.status in [CODE_VERIFIED, NEW]:
            raise ValidationError({
                'success': False,
                'message' : "Siz ro'yxatdan o'tmagansiz"
            })
        user = authenticate(**authentication_kwargs)
        if user is not None:
            self.user = user

        else:
            raise ValidationError({
                'success': False,
                'message' : "Ma'lumotlar to'gri emas"
            })
    def validate(self, data):
        self.aut_validete(data)
        if self.user.status not in [DONE,PHOTO_DONE]:
            raise PermissionDenied("Siz login qila olmaysiz ruxsatingiz yo'q")
        data = self.user.token()
        data['status'] = self.user.status
        data['full_name'] = self.user.full_name
        return data
    def get_user(self, **kwargs):
        users = User.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError({
                'success': False,
                'message':'Akount active emas'
            })
        return users.first()
class LoginRefreshSerializer(TokenRefreshSerializer):
    def validate(self, data):
        data = super().validate(attrs)
        access_token_instance = AccessToken(data['access'])
        user_id = access_token_instance['user_id']
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data
class LogOutSerializer(serializers.Serializer):
    refresh = serializers.CharField()





class ForgetPasswordSerializer(serializers.Serializer):
    email_or_phone_number = serializers.CharField(write_only=True,required=True)
    def validate(self, attrs):
        email_or_phone_number = attrs.get('email_or_phone_number')
        if email_or_phone_number is None:
            raise ValidationError({
                'success': False,
                'message': 'Email or phone number required'
            })
        user = User.objects.filter(Q(phone_number = email_or_phone_number) | Q(email = email_or_phone_number))
        if not user.exists():
            raise NotFound({
                'success': False,
                'message': 'User not found'
            })
        attrs['user'] = user.first()
        return attrs
class ResetPasswordSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(min_length=8,write_only=True,required=True)
    confirm_password = serializers.CharField(min_length=8,write_only=True,required=True)
    class Meta:
        model = User
        fields = ('id','password','confirm_password')

    def validate(self, data):
        password = data.get('password',None)
        confirm_password = data.get('confirm_password',None)
        if password != confirm_password:
            raise ValidationError({
                'success': False,
                'message': "Passwords don't match",
            })
        if password:
            validate_password(password)
        return data
    def update(self, instance, validated_data):
        password = self.validated_data.pop('password')
        instance.set_password(password)
        return super(ResetPasswordSerializer, self).update(instance, validated_data)
