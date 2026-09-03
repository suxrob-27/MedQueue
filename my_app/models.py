from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator


# ═══════════════════════════════════════════════════════
# 1. FOYDALANUVCHI (Custom User)
# ═══════════════════════════════════════════════════════
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin',    'Admin'),
        ('hospital', 'Shifohona'),
        ('doctor',   'Shifokor'),
        ('patient',  'Bemor'),
    ]

    role   = models.CharField(max_length=10, choices=ROLE_CHOICES, default='patient')
    phone  = models.CharField(max_length=13, unique=True, null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    def is_doctor(self):
        return self.role == 'doctor'

    def is_patient(self):
        return self.role == 'patient'

    def is_hospital(self):
        return self.role == 'hospital'

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


# ═══════════════════════════════════════════════════════
# 2. BEMOR PROFILI
# ═══════════════════════════════════════════════════════
class PatientProfile(models.Model):
    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    user             = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    birth_date       = models.DateField(null=True, blank=True)
    blood_type       = models.CharField(max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True)
    address          = models.CharField(max_length=300, blank=True)
    allergies        = models.TextField(blank=True, help_text="Allergiyalar")
    chronic_diseases = models.TextField(blank=True, help_text="Surunkali kasalliklar")

    def __str__(self):
        return f"Bemor: {self.user.get_full_name()}"


# ═══════════════════════════════════════════════════════
# 3. VILOYAT VA TUMAN
# ═══════════════════════════════════════════════════════
class Region(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Viloyat"
        verbose_name_plural = "Viloyatlar"


class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='districts')
    name   = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.name}, {self.region}"

    class Meta:
        verbose_name        = "Tuman"
        verbose_name_plural = "Tumanlar"


# ═══════════════════════════════════════════════════════
# 4. MUTAXASSISLIK
# ═══════════════════════════════════════════════════════
class MedicalSpecialty(models.Model):
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True, help_text="Emoji yoki icon nomi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name        = "Mutaxassislik"
        verbose_name_plural = "Mutaxassisliklar"


# ═══════════════════════════════════════════════════════
# 5. SHIFOHONA
# ═══════════════════════════════════════════════════════
class Hospital(models.Model):
    TYPE_CHOICES = [
        ('state',   'Davlat'),
        ('private', 'Xususiy'),
        ('clinic',  'Klinika'),
    ]

    name            = models.CharField(max_length=200)
    type            = models.CharField(max_length=10, choices=TYPE_CHOICES, default='state')
    district        = models.ForeignKey(District, on_delete=models.SET_NULL, null=True)
    address         = models.CharField(max_length=300)
    latitude        = models.DecimalField(max_digits=9, decimal_places=6)
    longitude       = models.DecimalField(max_digits=9, decimal_places=6)
    phone           = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    website         = models.URLField(blank=True)
    description     = models.TextField(blank=True)
    image           = models.ImageField(upload_to='hospitals/', null=True, blank=True)
    open_time       = models.TimeField(default='08:00')
    close_time      = models.TimeField(default='18:00')
    works_weekend   = models.BooleanField(default=False)
    specialties     = models.ManyToManyField(MedicalSpecialty, related_name='hospitals', blank=True)
    is_active       = models.BooleanField(
        default=True,
        help_text="False qilinsa saytda ko'rinmaydi va navbat yozib bo'lmaydi"
    )
    inactive_reason = models.CharField(
        max_length=300, blank=True,
        help_text="Masalan: 'Ta'mirda', 'Vaqtincha yopiq'"
    )
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "" if self.is_active else " [YOPIQ]"
        return f"{self.name}{status}"

    class Meta:
        ordering        = ['name']
        verbose_name    = "Shifohona"
        verbose_name_plural = "Shifohonalar"


# ═══════════════════════════════════════════════════════
# 6. SHIFOHONA PANELI PROFILI
# ═══════════════════════════════════════════════════════
class HospitalProfile(models.Model):
    """
    Shifohona login qila oladigan account.
    Admin shifohona yaratganda bu profil ham yaratiladi.
    role='hospital' bo'lgan User bilan bog'langan.
    """
    user       = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='hospital_profile'
    )
    hospital   = models.OneToOneField(
        Hospital, on_delete=models.CASCADE,
        related_name='profile'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.hospital.name} (panel)"

    class Meta:
        verbose_name        = "Shifohona profili"
        verbose_name_plural = "Shifohona profillari"


# ═══════════════════════════════════════════════════════
# 7. SHIFOKOR PROFILI
# ═══════════════════════════════════════════════════════
class DoctorProfile(models.Model):
    user      = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    hospital  = models.ForeignKey(
        Hospital, on_delete=models.SET_NULL,
        null=True, related_name='doctors'
    )
    specialty = models.ForeignKey(
        MedicalSpecialty, on_delete=models.SET_NULL,
        null=True, related_name='doctors'
    )
    birth_date         = models.DateField(null=True, blank=True)
    bio                = models.TextField(blank=True, help_text="Shifokor haqida qisqacha")
    experience_years   = models.PositiveIntegerField(default=0, help_text="Tajriba (yil)")
    education          = models.CharField(max_length=300, blank=True, help_text="Oliy ta'lim muassasasi")
    consultation_fee   = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Qabul narxi (so'm)"
    )
    rating             = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)]
    )
    is_available       = models.BooleanField(
        default=True,
        help_text="False qilinsa navbat yozib bo'lmaydi"
    )
    unavailable_reason = models.CharField(
        max_length=300, blank=True,
        help_text="Masalan: 'Ta'tilda', 'Kasal', 'Konferensiyada'"
    )

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.specialty}"

    class Meta:
        ordering        = ['-rating']
        verbose_name    = "Shifokor profili"
        verbose_name_plural = "Shifokor profillari"


# ═══════════════════════════════════════════════════════
# 8. SHIFOKOR SO'ROVI (ro'yxatdan o'tish)
# ═══════════════════════════════════════════════════════
class DoctorApplication(models.Model):
    """
    Shifokor ro'yxatdan o'tganda yaratiladi.
    Shifohona tasdiqlasa DoctorProfile avtomatik yaratiladi.
    """
    STATUS_CHOICES = [
        ('pending',  'Kutilmoqda'),
        ('approved', 'Tasdiqlandi'),
        ('rejected', 'Rad etildi'),
    ]

    user             = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='doctor_application'
    )
    hospital         = models.ForeignKey(
        Hospital, on_delete=models.CASCADE,
        related_name='applications'
    )
    specialty        = models.ForeignKey(
        MedicalSpecialty, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='applications'
    )
    experience_years = models.PositiveIntegerField(default=0)
    education        = models.CharField(max_length=300, blank=True)
    status           = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending'
    )
    reject_reason    = models.CharField(max_length=300, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} → {self.hospital.name} [{self.get_status_display()}]"

    class Meta:
        verbose_name        = "Shifokor so'rovi"
        verbose_name_plural = "Shifokor so'rovlari"
        ordering            = ['-created_at']


# ═══════════════════════════════════════════════════════
# 9. SHIFOKOR ISH GRAFIGI
# ═══════════════════════════════════════════════════════
class DoctorSchedule(models.Model):
    WEEKDAY_CHOICES = [
        (0, 'Dushanba'),
        (1, 'Seshanba'),
        (2, 'Chorshanba'),
        (3, 'Payshanba'),
        (4, 'Juma'),
        (5, 'Shanba'),
        (6, 'Yakshanba'),
    ]

    doctor        = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='schedules')
    weekday       = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time    = models.TimeField()
    end_time      = models.TimeField()
    slot_duration = models.PositiveIntegerField(default=20, help_text="Daqiqada")
    is_active     = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.doctor} — {self.get_weekday_display()} {self.start_time}-{self.end_time}"

    class Meta:
        unique_together     = ('doctor', 'weekday')
        verbose_name        = "Ish grafigi"
        verbose_name_plural = "Ish grafiklari"


# ═══════════════════════════════════════════════════════
# 10. NAVBAT
# ═══════════════════════════════════════════════════════
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending',   'Kutilmoqda'),
        ('confirmed', 'Tasdiqlangan'),
        ('cancelled', 'Bekor qilindi'),
        ('completed', 'Tugallandi'),
        ('no_show',   'Kelmadi'),
    ]

    patient          = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='appointments',
        limit_choices_to={'role': 'patient'}
    )
    doctor           = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='appointments')
    hospital         = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    reason           = models.TextField(null=True, blank=True, help_text="Murojaat sababi")
    doctor_notes     = models.TextField(null=True, blank=True, help_text="Shifokor xulosasi")
    cancel_reason    = models.CharField(max_length=300, null=True, blank=True)
    reminder_sent    = models.BooleanField(default=False)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    def __str__(self):
        return (
            f"{self.patient.get_full_name()} → "
            f"Dr.{self.doctor.user.get_full_name()} | "
            f"{self.appointment_date} {self.appointment_time} | "
            f"{self.get_status_display()}"
        )

    class Meta:
        ordering        = ['appointment_date', 'appointment_time']
        verbose_name    = "Navbat"
        verbose_name_plural = "Navbatlar"
        constraints     = [
            models.UniqueConstraint(
                fields=['doctor', 'appointment_date', 'appointment_time'],
                condition=models.Q(status__in=['pending', 'confirmed']),
                name='unique_active_appointment'
            )
        ]


# ═══════════════════════════════════════════════════════
# 11. REYTING VA SHARH
# ═══════════════════════════════════════════════════════
class Review(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='review')
    patient     = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor      = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='reviews')
    rating      = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment     = models.TextField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        doctor = self.doctor
        avg = doctor.reviews.aggregate(models.Avg('rating'))['rating__avg']
        doctor.rating = round(avg or 0.0, 1)
        doctor.save(update_fields=['rating'])

    def __str__(self):
        return f"{self.patient} → {self.doctor} | {self.rating}⭐"

    class Meta:
        verbose_name = "Sharh"
        verbose_name_plural = "Sharhlar"


# ═══════════════════════════════════════════════════════
# 12. BILDIRISHNOMA
# ═══════════════════════════════════════════════════════
class Notification(models.Model):
    TYPE_CHOICES = [
        ('reminder',        '1 soat qoldi'),
        ('confirmed',       'Navbat tasdiqlandi'),
        ('cancelled',       'Navbat bekor qilindi'),
        ('completed',       'Qabul tugadi'),
        ('no_show',         'Bemor kelmadi'),
        ('new_application', "Yangi shifokor so'rovi"),
    ]

    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True)
    type        = models.CharField(max_length=15, choices=TYPE_CHOICES)
    message     = models.TextField()
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.get_type_display()} ({'O\'qildi' if self.is_read else 'Yangi'})"

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"