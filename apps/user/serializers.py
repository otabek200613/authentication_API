from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework.generics import get_object_or_404
from django.contrib.auth.models import update_last_login

from shared.utility import send_email, check_email, check_user_type
from user.models import User, CODE_VERIFIED, DONE, PHOTO_DONE, NEW


class SignUpSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(write_only=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'status')
        read_only_fields = ('id', 'status')

    def create(self, validated_data):
        email = validated_data['email'].lower()
        user = User.objects.create(email=email, username=email)
        code = user.create_verify_code()
        send_email(user.email, code)
        return user

    def validate(self, data):
        super(SignUpSerializer, self).validate(data)
        data = self.auth_validate(data)
        return data

    @staticmethod
    def auth_validate(data):
        user_input = str(data.get('email', '')).strip().lower()
        input_type = check_email(user_input)
        if not input_type:
            raise serializers.ValidationError({
                'success': False,
                'message': "Email noto'g'ri formatda!"
            })

        data['email'] = user_input
        return data

    def validate_email(self, data):
        data = data.lower()
        if User.objects.filter(email=data).exists():
            raise serializers.ValidationError({
                'success': False,
                'message': "Bu email allaqachon ma'lumotlar bazasida mavjud"
            })
        return data

    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)
        data.update(instance.token())
        return data


class ChangeUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)
        if password != confirm_password:
            raise serializers.ValidationError({
                'success': False,
                'message': "Parollar bor biriga mos emas!"
            })
        if password:
            validate_password(password)
            validate_password(confirm_password)

        return data

    def validate_username(self, username):
        if len(username) < 5 or len(username) > 30:
            raise serializers.ValidationError({
                'message': "Bu username noto'g'ri formatda!"
            })
        if username.isdigit():
            raise serializers.ValidationError({
                'message': "Usernameda raqamdan foydalanish mumkinmas!"
            })
        return username

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.password = validated_data.get('password', instance.password)
        instance.username = validated_data.get('username', instance.username)
        if validated_data.get('password'):
            instance.set_password(validated_data.get('password'))
        if instance.status == CODE_VERIFIED:
            instance.status = DONE
        instance.save()
        return instance


class ChangePhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(validators=[FileExtensionValidator(['jpg', 'jpeg', 'heic', 'heif','png'])])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo')
        if photo:
            instance.photo = photo
            instance.status = PHOTO_DONE
            instance.save()
        return instance


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.pop(self.username_field, None)

        self.fields["userinput"] = serializers.CharField(write_only=True, required=True)
        self.fields["password"] = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        user_input = data.get("userinput")
        password = data.get("password")

        if not user_input:
            raise ValidationError({"success": False, "message": "userinput kiritilishi shart"})
        if not password:
            raise ValidationError({"success": False, "message": "password kiritilishi shart"})

        user_type = check_user_type(user_input)

        if user_type == "username":
            username = user_input
        else:
            user_obj = User.objects.filter(email__iexact=user_input).first()
            if not user_obj:
                raise ValidationError({"success": False, "message": "Bunday email topilmadi"})
            username = user_obj.username

        current_user = User.objects.filter(username__iexact=username).first()
        if not current_user:
            raise ValidationError({"success": False, "message": "Bunday foydalanuvchi topilmadi"})

        if current_user.status == NEW:
            raise ValidationError({"success": False, "message": "Avval emailingizni tasdiqlang"})

        user = authenticate(username=username, password=password)
        if user is None:
            raise ValidationError({"success": False, "message": "Login yoki parol noto'g'ri"})

        if user.status not in [DONE, PHOTO_DONE]:
            raise ValidationError({"success": False, "message": "Ro'yxatdan o'tishni yakunlang"})

        tokens = user.token()
        tokens["status"] = user.status
        tokens["full_name"] = user.full_name
        return tokens

class LoginRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access_token_instance = AccessToken(data['access'])
        user_id = access_token_instance['user_id']
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data
class LogOutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True,required=True)
    def validate(self, attrs):
        email = attrs.get('email',None)
        if email is None:
            raise serializers.ValidationError({
                'message': 'Email kiritilishi shart'
            })
        user = User.objects.filter(Q(email=email))
        if not user.exists():
            raise NotFound(detail="Foydalanuvhci topilmadi!")
        attrs['user'] = user.first()
        return attrs
class ResetPasswordSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)
    class Meta:
        model = User
        fields = ('id', 'password', 'confirm_password')
    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)
        if password != confirm_password:
            raise serializers.ValidationError({
                'message': 'Parollar bir-biriga mos emas!'
            })
        if password:
            validate_password(password)
        return data
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance.set_password(password)
        return super(ResetPasswordSerializer, self).update(instance, validated_data)


