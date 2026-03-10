from django.shortcuts import render
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, permissions, status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from shared.utilis import send_email, check_phone_number
from user.models import User, NEW, CODE, Confirmation
from user.serializers import SignUpSerializer, ChangeUserInformation, ChangeUserPhotoSerializer, LoginSerializer, \
    LoginRefreshSerializer, LogOutSerializer, ForgetPasswordSerializer, ResetPasswordSerializer, ProfileSerializer


class CreateUserAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = SignUpSerializer


class VerifyUserAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = self.request.user
        code = request.data.get('code')
        self.check_verify(user, code)
        tokens = user.token()
        return Response(
            data={
                'success': True,
                'status': user.auth_status,
                'access': tokens['access'],
                'refresh': tokens['refresh_token'],
            }
        )

    @staticmethod
    def check_verify(user, code):
        try:
            confirm = user.confirmation
        except Confirmation.DoesNotExist:
            raise ValidationError({'message': "Tasdiqlash kodi topilmadi. Qayta kod yuboring."})

        if confirm.is_confirmed:
            return True

        if confirm.code != str(code):
            raise ValidationError({'message': "Tasdiqlash kodingiz xato"})

        if confirm.expiration_time and confirm.expiration_time < timezone.now():
            raise ValidationError({'message': "Tasdiqlash kodingiz eskirgan"})

        confirm.is_confirmed = True
        confirm.save(update_fields=["is_confirmed"])

        if user.auth_status == NEW:
            user.auth_status = CODE
            user.save(update_fields=["auth_status"])

        return True


class GetNewVerificationAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = self.request.user
        self.check_verifiction(user)
        try:
            code = user.create_verify_code()
            send_email(user.email, code)
        except:
            raise ValidationError({
                'message': "Raqam noto'g'ri kiritildi"
            })
        return Response({
            'success': True,
            'message': "Tasdiqlash kodingiz qayta jo'natildi"
        })

    @staticmethod
    def check_verifiction(user):
        try:
            confirm = user.confirmation
        except Confirmation.DoesNotExist:
            return

        if (not confirm.is_confirmed) and confirm.expiration_time and confirm.expiration_time >= timezone.now():
            raise ValidationError({
                'message': "Tasdiqlash kodingiz hali yaroqli. Iltimos biroz kuting"
            })


class ChangeUserInfoAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeUserInformation
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super(ChangeUserInfoAPIView, self).update(request, *args, **kwargs)
        return Response({
            'success': True,
            'message': "Ma'lmotar muvaffaqiyatli yangilandi",
            "status": self.request.user.auth_status
        }, status=status.HTTP_200_OK)

class ChangeUserPhotoAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = ChangeUserPhotoSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            serializer.update(user, serializer.validated_data)
            return Response({
                "message": "Profil rasmi muvaffaqiyatli o'zgartirildi"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=400)


class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LoginRefreshAPIView(TokenRefreshView):
    serializer_class = LoginRefreshSerializer


class LogOutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogOutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()


            return Response({
                'success': True,
                "message": "Siz tizimdan muvaffaqiyatli chiqdingiz"
            })

        except TokenError:
            return Response({
                'success': False,
                'message': 'Token invalid'
            }, status=status.HTTP_400_BAD_REQUEST)

class FrgotPasswordAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email_or_phone = serializer.validated_data['email_or_phone']
        user = serializer.validated_data['user']
        if check_phone_number(email_or_phone):
            code = user.create_verify_code()
            send_email(email_or_phone, code)
        tokens = user.token()
        return Response({
            'success': True,
            'message': "Tasdiqlash kodingiz qayta jo'natildi",
            "access": tokens['access'],
            'refresh': tokens['refresh_token'],
            'status': user.auth_status
        }, status=status.HTTP_200_OK)


class ResetPasswordAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ResetPasswordSerializer

    def get_object(self):
        user = self.request.user
        return user

    def update(self, request, *args, **kwargs):
        response = super(ResetPasswordAPIView, self).update(request, *args, **kwargs)
        try:
            user = User.objects.get(id=response.data['id'])
        except User.DoesNotExist:
            raise NotFound(detail="Foydalanuvchi topilmadi")
        tokens = user.token()
        return Response({
            'success': True,
            'message': "Parolingiz muvaffaqiyatli yangilandi",
            'access': tokens['access'],
            'refresh': tokens['refresh_token'],
        })
class ProfileView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer
    def get_object(self):
        user = self.request.user
        return user