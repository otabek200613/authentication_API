from datetime import datetime

from django.shortcuts import render
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics, permissions, status
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from shared.utility import send_email, check_email
from user.models import User, NEW, CODE_VERIFIED, UserConfirmation
from user.serializers import SignUpSerializer, ChangeUserSerializer, ChangePhotoSerializer, LoginSerializer, \
    LoginRefreshSerializer, LogOutSerializer, ForgetPasswordSerializer, ResetPasswordSerializer


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
        return Response(
            data={
                'success': True,
                'status': user.status,
                'access': user.token()['access'],
                'refresh': user.token()['refresh'],
            }
        )

    @staticmethod
    def check_verify(user, code):
        try:
            confirm = user.confirmation_code
        except UserConfirmation.DoesNotExist:
            raise ValidationError({'message': "Tasdiqlash kodi topilmadi. Qayta kod yuboring."})

        if confirm.is_confirmed:
            return True

        if confirm.code != str(code):
            raise ValidationError({'message': "Tasdiqlash kodingiz xato"})

        if confirm.expiration_date and confirm.expiration_date < timezone.now():
            raise ValidationError({'message': "Tasdiqlash kodingiz eskirgan"})

        confirm.is_confirmed = True
        confirm.save(update_fields=["is_confirmed"])

        if user.status == NEW:
            user.status = CODE_VERIFIED
            user.save(update_fields=["status"])

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
                'message': "Email noto'g'ri kiritildi"
            })
        return Response({
            'success': True,
            'message': "Tasdiqlash kodingiz qayta jo'natildi"
        })

    @staticmethod
    def check_verifiction(user):
        try:
            confirm = user.confirmation_code
        except UserConfirmation.DoesNotExist:
            return

        if (not confirm.is_confirmed) and confirm.expiration_date and confirm.expiration_date >= timezone.now():
            raise ValidationError({
                'message': "Tasdiqlash kodingiz hali yaroqli. Iltimos biroz kuting"
            })


class ChangeUserInfoAPIView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangeUserSerializer
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super(ChangeUserInfoAPIView, self).update(request, *args, **kwargs)
        return Response({
            'success': True,
            'message': "Ma'lmotar muvaffaqiyatli yangilandi",
            "status": self.request.user.status
        }, status=status.HTTP_200_OK)


class ChangeUserPhotoAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, *args, **kwargs):
        serializer = ChangePhotoSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            serializer.update(user, serializer.validated_data)
            return Response({
                "message": "Profil rasmi muvaffaqiyatli o'zgartirildi"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=400)

class LoginAPIView(TokenObtainPairView):
    serializer_class = LoginSerializer


class LoginRefreshAPIView(APIView):
    serializer_class = LoginRefreshSerializer


class LogOutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LogOutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = self.request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'success': True, "message": "Siz tizimdan muvaffaqiyatli chiqdingiz"})
        except TokenError:
            return Response(status)


class FrgotPasswordAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgetPasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = serializer.validated_data['user']
        if check_email(email):
            code = user.create_verify_code()
            send_email(email, code)
        return Response({
            'success': True,
            'message': "Tasdiqlash kodingiz qayta jo'natildi",
            "access": user.token()['access'],
            'refresh': user.token()['refresh'],
            'status': user.status
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
        return Response({
            'success': True,
            'message': "Parolingiz muvaffaqiyatli yangilandi",
            'access': user.token()['access'],
            'refresh': user.token()['refresh'],
        })
