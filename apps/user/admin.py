from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Confirmation



@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('full_name', 'phone_number', 'email', 'username', 'auth_status', 'user_role', 'is_active', 'date_joined')
    list_display_links = ('full_name', 'username')
    list_filter = ('auth_status', 'user_role', 'is_active', 'is_staff')
    search_fields = ('username', 'phone_number', 'email', 'first_name', 'last_name')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined', 'last_login')
    list_per_page = 20

    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('username', 'password')
        }),
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'photo')
        }),
        ('Status', {
            'fields': ('auth_status', 'user_role', 'is_active', 'is_staff', 'is_superuser')
        }),
        ('Vaqt', {
            'fields': ('date_joined', 'last_login'),
            'classes': ('collapse',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'username', 'password1', 'password2', 'auth_status', 'user_role'),
        }),
    )


@admin.register(Confirmation)
class ConfirmationAdmin(admin.ModelAdmin):
    list_display = ('user', 'code', 'expiration_time', 'is_confirmed')
    list_filter = ('is_confirmed',)
    search_fields = ('user__username', 'user__phone_number', 'code')
    readonly_fields = ('expiration_time',)
    list_per_page = 20