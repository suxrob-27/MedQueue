from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django import forms
from django.utils.crypto import get_random_string
from .models import (
    User, PatientProfile, Region, District, MedicalSpecialty,
    Hospital, HospitalProfile, DoctorProfile, DoctorApplication,
    DoctorSchedule, Appointment, Review, Notification,
)


# ═══════════════════════════════════════════════════════
# 1. USER ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Djangoning standart UserAdmin ni kengaytiramiz.
    Qo'shimcha fieldlar: role, phone, avatar.
    """
    # Ro'yxatda ko'rinadigan ustunlar
    list_display  = ('username', 'get_full_name', 'role', 'phone', 'email', 'is_active')
    list_editable = ('role', 'is_active')
    list_filter   = ('role', 'is_active', 'is_staff')
    search_fields = ('username', 'first_name', 'last_name', 'phone', 'email')
    ordering      = ('username',)

    # Mavjud foydalanuvchini tahrirlash sahifasi
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {
            'fields': ('role', 'phone', 'avatar')
        }),
    )

    # Yangi foydalanuvchi yaratish sahifasi
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Qo\'shimcha ma\'lumotlar', {
            'fields': ('role', 'phone', 'email', 'first_name', 'last_name')
        }),
    )


# ═══════════════════════════════════════════════════════
# 2. PATIENT PROFILE ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display  = ('get_full_name', 'get_phone', 'blood_type', 'birth_date')
    search_fields = ('user__first_name', 'user__last_name', 'user__phone')
    list_filter   = ('blood_type',)

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Ism Familiya'

    def get_phone(self, obj):
        return obj.user.phone
    get_phone.short_description = 'Telefon'


# ═══════════════════════════════════════════════════════
# 3. REGION VA DISTRICT ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display  = ('name', 'get_district_count')
    search_fields = ('name',)

    def get_district_count(self, obj):
        return obj.districts.count()
    get_district_count.short_description = 'Tumanlar soni'


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display  = ('name', 'region')
    list_filter   = ('region',)
    search_fields = ('name', 'region__name')


# ═══════════════════════════════════════════════════════
# 4. MEDICAL SPECIALTY ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(MedicalSpecialty)
class MedicalSpecialtyAdmin(admin.ModelAdmin):
    list_display  = ('name', 'icon', 'get_doctor_count')
    search_fields = ('name',)

    def get_doctor_count(self, obj):
        return obj.doctors.count()
    get_doctor_count.short_description = 'Shifokorlar soni'


# ═══════════════════════════════════════════════════════
# 5. HOSPITAL ADMIN
# ═══════════════════════════════════════════════════════
class DoctorInline(admin.TabularInline):
    """
    Shifohona sahifasida pastda shifokorlar ro'yxati ko'rinadi.
    Inline — boshqa modelni shu sahifada ko'rsatish.
    """
    model  = DoctorProfile
    extra  = 0   # Bo'sh qo'shimcha qator ko'rsatma
    fields = ('user', 'specialty', 'is_available', 'consultation_fee', 'rating')
    readonly_fields = ('rating',)
    show_change_link = True   # Shifokor profiliga o'tish linki


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display  = (
        'name', 'type', 'district', 'phone',
        'is_active_badge',     # Rangli badge
        'get_doctor_count',
        'get_active_appointments'
    )
    list_filter   = ('type', 'is_active', 'district__region', 'works_weekend')
    search_fields = ('name', 'address', 'phone')
    filter_horizontal = ('specialties',)   # Chiroyli many-to-many widget
    inlines       = [DoctorInline]

    # Ko'p fieldlarni guruhlab ko'rsatish
    fieldsets = (
        ('Asosiy ma\'lumotlar', {
            'fields': ('name', 'type', 'district', 'address', 'image', 'description')
        }),
        ('Aloqa', {
            'fields': ('phone', 'email', 'website')
        }),
        ('Xarita koordinatalari', {
            'fields': ('latitude', 'longitude')
        }),
        ('Ish vaqti', {
            'fields': ('open_time', 'close_time', 'works_weekend')
        }),
        ('Mutaxassisliklar', {
            'fields': ('specialties',)
        }),
        ('Holat', {
            'fields': ('is_active', 'inactive_reason'),
            'classes': ('collapse',)   # Bosmasangiz yopiq turadi
        }),
    )

    # Rangli status badge
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:green; font-weight:bold;">✔ Ochiq</span>')
        return format_html(
            '<span style="color:red; font-weight:bold;">✘ Yopiq</span>'
            '<br><small style="color:gray;">{}</small>',
            obj.inactive_reason or ''
        )
    is_active_badge.short_description = 'Holat'

    def get_doctor_count(self, obj):
        total    = obj.doctors.count()
        active   = obj.doctors.filter(is_available=True).count()
        return format_html('{} / <span style="color:green">{}</span>', total, active)
    get_doctor_count.short_description = 'Shifokorlar (jami/aktiv)'

    def get_active_appointments(self, obj):
        count = obj.appointments.filter(status__in=['pending', 'confirmed']).count()
        return count
    get_active_appointments.short_description = 'Aktiv navbatlar'


# ═══════════════════════════════════════════════════════
# 6. DOCTOR PROFILE ADMIN
# ═══════════════════════════════════════════════════════
class DoctorScheduleInline(admin.TabularInline):
    """Shifokor sahifasida ish grafigi ko'rinadi."""
    model  = DoctorSchedule
    extra  = 0
    fields = ('weekday', 'start_time', 'end_time', 'slot_duration', 'is_active')


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display  = (
        'get_full_name', 'specialty', 'hospital',
        'experience_years', 'consultation_fee',
        'rating_stars',
        'is_available_badge'
    )
    list_filter   = ('specialty', 'hospital', 'is_available')
    search_fields = ('user__first_name', 'user__last_name', 'user__phone')
    inlines       = [DoctorScheduleInline]

    fieldsets = (
        ('Foydalanuvchi', {
            'fields': ('user', 'hospital', 'specialty')
        }),
        ('Shaxsiy ma\'lumotlar', {
            'fields': ('birth_date',)
        }),
        ('Kasbiy ma\'lumotlar', {
            'fields': ('bio', 'experience_years', 'education', 'consultation_fee')
        }),
        ('Reyting', {
            'fields': ('rating',),
            'description': 'Reyting avtomatik hisoblanadi, qo\'lda o\'zgartirmang.'
        }),
        ('Holat', {
            'fields': ('is_available', 'unavailable_reason'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('rating',)

    def get_full_name(self, obj):
        return f"Dr. {obj.user.get_full_name()}"
    get_full_name.short_description = 'Shifokor'

    def rating_stars(self, obj):
        # 0-5 reytingni yulduzcha bilan ko'rsatish
        filled = int(obj.rating)
        empty  = 5 - filled
        return format_html(
            '<span style="color:orange">{}</span><span style="color:lightgray">{}</span> ({})',
            '★' * filled, '★' * empty, obj.rating
        )
    rating_stars.short_description = 'Reyting'

    def is_available_badge(self, obj):
        if obj.is_available:
            return format_html('<span style="color:green; font-weight:bold;">✔ Ishlaydi</span>')
        return format_html(
            '<span style="color:red; font-weight:bold;">✘ Ishlamaydi</span>'
            '<br><small style="color:gray;">{}</small>',
            obj.unavailable_reason or ''
        )
    is_available_badge.short_description = 'Holat'


# ═══════════════════════════════════════════════════════
# 7. DOCTOR SCHEDULE ADMIN (alohida ham ko'rinadi)
# ═══════════════════════════════════════════════════════
@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display  = ('doctor', 'get_weekday_display', 'start_time', 'end_time', 'slot_duration', 'is_active')
    list_filter   = ('weekday', 'is_active')
    search_fields = ('doctor__user__first_name', 'doctor__user__last_name')

    def get_weekday_display(self, obj):
        return obj.get_weekday_display()
    get_weekday_display.short_description = 'Kun'


# ═══════════════════════════════════════════════════════
# 8. APPOINTMENT ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display  = (
        'get_patient', 'get_doctor', 'hospital',
        'appointment_date', 'appointment_time',
        'status_badge', 'reminder_sent'
    )
    list_filter   = ('status', 'appointment_date', 'hospital', 'reminder_sent')
    search_fields = (
        'patient__first_name', 'patient__last_name',
        'doctor__user__first_name', 'doctor__user__last_name'
    )
    date_hierarchy = 'appointment_date'   # Yuqorida sana bo'yicha filter
    readonly_fields = ('created_at', 'updated_at', 'reminder_sent')

    fieldsets = (
        ('Navbat ma\'lumotlari', {
            'fields': ('patient', 'doctor', 'hospital', 'appointment_date', 'appointment_time')
        }),
        ('Holat', {
            'fields': ('status', 'cancel_reason')
        }),
        ('Izohlar', {
            'fields': ('reason', 'doctor_notes')
        }),
        ('Tizim', {
            'fields': ('reminder_sent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_patient(self, obj):
        return obj.patient.get_full_name()
    get_patient.short_description = 'Bemor'

    def get_doctor(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor.short_description = 'Shifokor'

    def status_badge(self, obj):
        colors = {
            'pending':   ('orange',     'Kutilmoqda'),
            'confirmed': ('blue',       'Tasdiqlangan'),
            'cancelled': ('red',        'Bekor qilindi'),
            'completed': ('green',      'Tugallandi'),
            'no_show':   ('darkred',    'Kelmadi'),
        }
        color, label = colors.get(obj.status, ('gray', obj.status))
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', color, label
        )
    status_badge.short_description = 'Status'

    # Admin paneldan to'g'ridan-to'g'ri statusni o'zgartirish
    actions = ['mark_confirmed', 'mark_completed', 'mark_no_show', 'mark_cancelled']

    @admin.action(description="✔ Tasdiqlash")
    def mark_confirmed(self, request, queryset):
        queryset.update(status='confirmed')

    @admin.action(description="✔ Tugallandi deb belgilash")
    def mark_completed(self, request, queryset):
        queryset.update(status='completed')

    @admin.action(description="✘ Kelmadi deb belgilash")
    def mark_no_show(self, request, queryset):
        queryset.update(status='no_show')

    @admin.action(description="✘ Bekor qilish")
    def mark_cancelled(self, request, queryset):
        queryset.update(status='cancelled')


# ═══════════════════════════════════════════════════════
# 9. REVIEW ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display  = ('patient', 'get_doctor', 'rating_stars', 'created_at')
    list_filter   = ('rating',)
    search_fields = ('patient__first_name', 'doctor__user__first_name')
    readonly_fields = ('created_at',)

    def get_doctor(self, obj):
        return f"Dr. {obj.doctor.user.get_full_name()}"
    get_doctor.short_description = 'Shifokor'

    def rating_stars(self, obj):
        return format_html(
            '<span style="color:orange">{}</span>',
            '★' * obj.rating + '☆' * (5 - obj.rating)
        )
    rating_stars.short_description = 'Baho'


# ═══════════════════════════════════════════════════════
# 10. NOTIFICATION ADMIN
# ═══════════════════════════════════════════════════════
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ('user', 'type', 'is_read', 'created_at')
    list_filter   = ('type', 'is_read')
    search_fields = ('user__first_name', 'user__last_name', 'message')
    readonly_fields = ('created_at',)

    actions = ['mark_as_read']

    @admin.action(description="O'qildi deb belgilash")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)


# ═══════════════════════════════════════════════════════
# admin.py ga QO'SHISH kerak — DoctorApplicationAdmin
# ═══════════════════════════════════════════════════════


@admin.register(DoctorApplication)
class DoctorApplicationAdmin(admin.ModelAdmin):
    """
    Admin shifohona nomidan so'rovlarni tasdiqlaydi yoki rad etadi.
    Tasdiqlanganida:
      - User.role = 'doctor' bo'ladi
      - DoctorProfile avtomatik yaratiladi
      - Mutaxassislik belgilanadi
    """
    list_display  = (
        'get_full_name', 'hospital', 'specialty',
        'experience_years', 'status_badge', 'created_at'
    )
    list_filter   = ('status', 'hospital', 'specialty')
    search_fields = ('user__first_name', 'user__last_name', 'user__phone')
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ("Shifokor ma'lumotlari", {
            'fields': ('user', 'hospital', 'specialty', 'experience_years', 'education')
        }),
        ('So\'rov holati', {
            'fields': ('status', 'reject_reason')
        }),
        ('Tizim', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['approve_applications', 'reject_applications']

    def get_full_name(self, obj):
        return obj.user.get_full_name()
    get_full_name.short_description = 'Shifokor'

    def status_badge(self, obj):
        colors = {
            'pending':  ('orange', '⏳ Kutilmoqda'),
            'approved': ('green',  '✅ Tasdiqlandi'),
            'rejected': ('red',    '❌ Rad etildi'),
        }
        color, label = colors.get(obj.status, ('gray', obj.status))
        return format_html(
            '<span style="color:{};font-weight:bold;">{}</span>', color, label
        )
    status_badge.short_description = 'Holat'

    @admin.action(description="✅ Tanlangan so'rovlarni tasdiqlash")
    def approve_applications(self, request, queryset):
        approved_count = 0
        for application in queryset.filter(status='pending'):
            self._approve(application)
            approved_count += 1
        self.message_user(
            request,
            f"{approved_count} ta shifokor tasdiqlandi va profil yaratildi."
        )

    @admin.action(description="❌ Tanlangan so'rovlarni rad etish")
    def reject_applications(self, request, queryset):
        queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, "So'rovlar rad etildi.")

    def save_model(self, request, obj, form, change):
        """
        Admin bitta so'rovni 'approved' ga o'zgartirsa
        avtomatik DoctorProfile yaratiladi.
        """
        old_status = None
        if obj.pk:
            old_status = DoctorApplication.objects.get(pk=obj.pk).status

        super().save_model(request, obj, form, change)

        # Yangi approved bo'lsa profil yaratamiz
        if obj.status == 'approved' and old_status != 'approved':
            self._approve(obj)

    def _approve(self, application):
        """
        Tasdiqlash logikasi:
        1. User.role = 'doctor'
        2. DoctorProfile yaratish (specialty bilan)
        3. Application status = 'approved'
        """
        user = application.user
        user.role = 'doctor'
        user.save(update_fields=['role'])
        user.is_staff = False
        user.is_superuser = False

        # DoctorProfile mavjudligini tekshir
        if not hasattr(user, 'doctor_profile'):
            DoctorProfile.objects.create(
                user=user,
                hospital=application.hospital,
                specialty=application.specialty,       # Avtomatik belgilanadi
                experience_years=application.experience_years,
                education=application.education,
                is_available=True,
            )

        application.status = 'approved'
        application.save(update_fields=['status'])

        # Shifokorga bildirishnoma
        Notification.objects.create(
            user=user,
            type='confirmed',
            message=(
                f"Tabriklaymiz! '{application.hospital.name}' shifohonasi "
                f"so'rovingizni tasdiqladi. Endi shifokor sifatida kirishingiz mumkin."
            )
        )

# ═══════════════════════════════════════════════════════
# admin.py ga QO'SHISH — HospitalProfile admin
# Admin shifohona accountini yaratadi
# ═══════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════
# HospitalProfile admin — Admin shifohona accountini yaratadi
# Login va parolni admin o'zi kiritadi (yoki bo'sh qoldirsa avtomatik yaratiladi)
# ═══════════════════════════════════════════════════════
class HospitalProfileAdminForm(forms.ModelForm):
    username = forms.CharField(
        label="Login (username)",
        required=False,
        max_length=150,
        help_text="Shifohona shu login bilan /kirish/ sahifasidan kiradi. "
                   "Bo'sh qoldirilsa, shifohona nomidan avtomatik yaratiladi.",
    )
    password = forms.CharField(
        label="Parol",
        required=False,
        max_length=128,
        widget=forms.TextInput(attrs={'placeholder': "Bo'sh qoldirilsa, tasodifiy parol yaratiladi"}),
        help_text="Shifohona aynan shu parolni kiritib tizimga kiradi.",
    )

    class Meta:
        model = HospitalProfile
        fields = ('hospital',)

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if username and User.objects.filter(username=username).exists():
            raise forms.ValidationError("Bu login band. Boshqa login kiriting.")
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '').strip()
        if password and len(password) < 6:
            raise forms.ValidationError("Parol kamida 6 belgidan iborat bo'lishi kerak.")
        return password


@admin.register(HospitalProfile)
class HospitalProfileAdmin(admin.ModelAdmin):
    """
    Admin bu yerdan shifohona account yaratadi.
    Login va parolni admin o'zi kiritishi mumkin (yoki bo'sh qoldirsa avtomatik yaratiladi).
    Shifohona keyin shu login/parol bilan oddiy /kirish/ sahifasidan kiradi.
    """
    form = HospitalProfileAdminForm
    list_display = ('hospital', 'get_username', 'get_email', 'created_at')
    search_fields = ('hospital__name', 'user__username', 'user__email')

    def get_username(self, obj):
        return obj.user.username
    get_username.short_description = 'Login'

    def get_email(self, obj):
        return obj.user.email
    get_email.short_description = 'Email'

    def get_fields(self, request, obj=None):
        if obj is None:
            # Yangi shifohona account yaratish — login/parol kiritish maydonlari ko'rinadi
            return ('hospital', 'username', 'password')
        # Mavjud accountni faqat ko'rish — o'zgartirib bo'lmaydi
        return ('hospital', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ('hospital', 'created_at')
        return ()

    def save_model(self, request, obj, form, change):
        """
        Yangi HospitalProfile saqlanayotganda avtomatik User yaratiladi.
        Login/parol admin tomonidan kiritilgan bo'lsa — aynan shulardan foydalaniladi.
        Bo'sh qoldirilgan bo'lsa — avtomatik generatsiya qilinadi.
        """
        if not change:  # Yangi yaratilayotgan bo'lsa
            hospital = obj.hospital
            username = form.cleaned_data.get('username', '').strip()
            password = form.cleaned_data.get('password', '').strip()
            auto_password = False
            auto_username = False

            # Login — admin kiritmagan bo'lsa, shifohona nomidan generatsiya qilinadi
            if not username:
                import re
                auto_username = True
                base_username = re.sub(r'[^a-z0-9]', '_', hospital.name.lower())[:20] or 'shifohona'
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

            # Parol — admin kiritmagan bo'lsa, tasodifiy xavfsiz parol yaratiladi
            if not password:
                password = get_random_string(10)
                auto_password = True

            user = User.objects.create_user(
                username=username,
                password=password,
                email=hospital.email or f"{username}@medqueue.uz",
                first_name=hospital.name,
                role='hospital',
                is_staff=False,
                is_superuser=False,
            )
            obj.user = user

            # Admin ga yaratilgan login/parolni ko'rsatish
            from django.contrib import messages
            details = []
            if auto_username:
                details.append("login avtomatik yaratildi")
            if auto_password:
                details.append("parol avtomatik yaratildi")
            note = f" ({', '.join(details)})" if details else " (siz kiritgan login/parol bilan)"

            messages.success(
                request,
                f"✅ Shifohona account yaratildi!{note} "
                f"Login: {username} | Parol: {password} — "
                f"buni shifohonaga yetkazing, ular shu bilan /kirish/ orqali kiradi."
            )

        super().save_model(request, obj, form, change)

