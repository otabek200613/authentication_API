from django.urls import path

from .views import LoginAPIView, LoginRefreshAPIView, LogOutAPIView, CreateUserAPIView, VerifyUserAPIView, \
    GetNewVerificationAPIView, \
    ChangeUserInfoAPIView, ChangeUserPhotoAPIView, FrgotPasswordAPIView, ResetPasswordAPIView, ProfileView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name="login"),
    path('login-refresh/', LoginRefreshAPIView.as_view(), name="login-refresh"),
    path('logout/', LogOutAPIView.as_view(), name="logout"),
    path("signup/", CreateUserAPIView.as_view(), name="signup"),
    path("verify/", VerifyUserAPIView.as_view(), name="verify"),
    path("new-verify/", GetNewVerificationAPIView.as_view(), name="new-verify"),
    path('change-user/', ChangeUserInfoAPIView.as_view(), name="change-user"),
    path('change-user-photo/', ChangeUserPhotoAPIView.as_view(), name="change-user-photo"),
    path('forgot-password/', FrgotPasswordAPIView.as_view(), name="forgot-password"),
    path('reset-password/', ResetPasswordAPIView.as_view(), name="reset-password"),
    path('profile/', ProfileView.as_view(), name="profile"),
]