from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Q
from .models import (
    User, PatientProfile, Region, District, MedicalSpecialty,
    Hospital, HospitalProfile, DoctorProfile, DoctorApplication,
    DoctorSchedule, Appointment, Review, Notification,
)
from datetime import date, timedelta
import json


# ═══════════════════════════════════════════════════════
# YORDAMCHI FUNKSIYA — Notifikatsiya yaratish
# ═══════════════════════════════════════════════════════
def create_notification(user, notif_type, message, appointment=None):
    """
    Har qanday hodisada bildirishnoma yaratadi.
    appointment — ixtiyoriy, navbat bilan bog'liq bo'lsa uzatiladi.
    """
    Notification.objects.create(
        user=user,
        type=notif_type,
        message=message,
        appointment=appointment
    )


# ═══════════════════════════════════════════════════════
# 1. ASOSIY SAHIFALAR
# ═══════════════════════════════════════════════════════
def index(request):
    """
    Bosh sahifa — index.html ko'rsatiladi.
    Xaritada ko'rsatish uchun barcha AKTIV shifohonalarni,
    statistika uchun umumiy sonlarni template ga uzatadi.
    """
    hospitals = Hospital.objects.filter(is_active=True).select_related('district__region')
    specialties = MedicalSpecialty.objects.all()
    regions = Region.objects.all()

    context = {
        'hospitals': hospitals,
        'specialties': specialties,
        'regions': regions,
        'total_regions': Region.objects.count(),
        'total_hospitals': Hospital.objects.filter(is_active=True).count(),
        'total_doctors': DoctorProfile.objects.filter(is_available=True).count(),
    }
    return render(request, 'index.html', context)


def hospital_list(request):
    """
    Shifohonalar ro'yxati sahifasi.
    Viloyat, tuman va mutaxassislik bo'yicha filter qilish mumkin.
    """
    hospitals = Hospital.objects.filter(is_active=True).select_related('district__region')

    # URL parametrlar orqali filter: ?region=1&specialty=2
    region_id = request.GET.get('region')
    specialty_id = request.GET.get('specialty')
    search = request.GET.get('q', '')

    if region_id:
        hospitals = hospitals.filter(district__region_id=region_id)
    if specialty_id:
        hospitals = hospitals.filter(specialties__id=specialty_id)
    if search:
        hospitals = hospitals.filter(
            Q(name__icontains=search) | Q(address__icontains=search)
        )

    context = {
        'hospitals': hospitals,
        'regions': Region.objects.all(),
        'specialties': MedicalSpecialty.objects.all(),
        'selected_region': region_id,
        'selected_specialty': specialty_id,
        'search': search,
    }
    return render(request, 'hospitals/list.html', context)


def hospital_detail(request, pk):
    """
    Bitta shifohona sahifasi.
    Shifokorlar ro'yxati, ish grafigi va reyting ko'rsatiladi.
    is_active=False bo'lsa — yopiq xabari chiqadi.
    """
    hospital = get_object_or_404(Hospital, pk=pk)
    doctors = DoctorProfile.objects.filter(
        hospital=hospital
    ).select_related('user', 'specialty')

    context = {
        'hospital': hospital,
        'doctors': doctors,
        'active_doctors': doctors.filter(is_available=True),
    }
    return render(request, 'hospitals/detail.html', context)


# ═══════════════════════════════════════════════════════
# 2. SHIFOKOR
# ═══════════════════════════════════════════════════════
def doctor_detail(request, pk):
    """
    Shifokor profil sahifasi.
    Ish grafigi, reyting va sharhlar ko'rsatiladi.
    """
    doctor = get_object_or_404(DoctorProfile, pk=pk)
    schedules = DoctorSchedule.objects.filter(doctor=doctor, is_active=True)
    reviews = Review.objects.filter(doctor=doctor).select_related('patient').order_by('-created_at')

    context = {
        'doctor': doctor,
        'schedules': schedules,
        'reviews': reviews,
        'review_count': reviews.count(),
    }
    return render(request, 'doctors/detail.html', context)


# ═══════════════════════════════════════════════════════
# 3. NAVBAT — yaratish
# ═══════════════════════════════════════════════════════
@login_required
def book_appointment(request):
    """
    Navbat olish sahifasi - faqat bemor (patient) uchun.
    """
    if request.user.role == 'hospital':
        return redirect('hospital_dashboard')
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        hospital_id = request.POST.get('hospital_id')
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        reason = request.POST.get('reason', '')

        # ── Majburiy maydonlar tekshiruvi ──
        if not all([doctor_id, hospital_id, appointment_date, appointment_time]):
            return render(request, 'appointments/book.html', {
                'error': "Barcha maydonlarni to'ldiring.",
                'hospitals': Hospital.objects.filter(is_active=True),
                'today': date.today(),
            })

        doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
        hospital = get_object_or_404(Hospital, pk=hospital_id)

        # ── Shifohona yopiqmi? ──
        if not hospital.is_active:
            return render(request, 'appointments/book.html', {
                'error': f"Shifohona hozir yopiq. Sabab: {hospital.inactive_reason or 'Noma\'lum'}",
                'hospitals': Hospital.objects.filter(is_active=True),
                'today': date.today(),
            })

        # ── Shifokor ishlamayaptimi? ──
        if not doctor.is_available:
            return render(request, 'appointments/book.html', {
                'error': f"Shifokor hozir mavjud emas. Sabab: {doctor.unavailable_reason or 'Noma\'lum'}",
                'hospitals': Hospital.objects.filter(is_active=True),
                'today': date.today(),
            })

        # ── O'sha vaqtda aktiv navbat bormi? ──
        # UniqueConstraint faqat pending va confirmed uchun — shu yerda ham tekshiramiz
        existing = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status__in=['pending', 'confirmed']
        ).exists()

        if existing:
            return render(request, 'appointments/book.html', {
                'error': "Bu vaqt band. Boshqa vaqtni tanlang.",
                'hospitals': Hospital.objects.filter(is_active=True),
                'today': date.today(),
            })

        # ── Navbat yaratish ──
        appointment = Appointment.objects.create(
            patient=request.user,
            doctor=doctor,
            hospital=hospital,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            reason=reason,
            status='pending'
        )

        # ── Bemor uchun bildirishnoma ──
        create_notification(
            user=request.user,
            notif_type='confirmed',
            message=f"Dr. {doctor.user.get_full_name()} bilan navbatingiz yaratildi. "
                    f"Sana: {appointment_date}, Soat: {appointment_time}",
            appointment=appointment
        )

        return redirect('appointment_detail', pk=appointment.pk)

    # GET — bo'sh forma
    hospitals = Hospital.objects.filter(is_active=True).select_related('district__region')
    specialties = MedicalSpecialty.objects.all()

    context = {
        'hospitals': hospitals,
        'specialties': specialties,
        'today': date.today(),
    }
    return render(request, 'appointments/book.html', context)


# ═══════════════════════════════════════════════════════
# 4. NAVBAT — ko'rish va boshqarish
# ═══════════════════════════════════════════════════════
@login_required
def appointment_detail(request, pk):
    """
    Navbat tafsilotlari sahifasi.
    Faqat o'sha navbatga tegishli foydalanuvchi yoki shifokor ko'ra oladi.
    """
    appointment = get_object_or_404(Appointment, pk=pk)

    # Faqat o'z navbatini ko'ra oladi
    if appointment.patient != request.user and not request.user.is_admin():
        if not hasattr(request.user, 'doctor_profile') or \
           request.user.doctor_profile != appointment.doctor:
            return redirect('dashboard')

    context = {'appointment': appointment}
    return render(request, 'appointments/detail.html', context)


@login_required
def my_appointments(request):
    """
    Bemor o'z navbatlarini ko'radigan sahifa.
    status filtri: ?status=pending yoki ?status=completed
    """
    if request.user.role == 'hospital':
        return redirect('hospital_appointments')
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')

    appointments = Appointment.objects.filter(
        patient=request.user
    ).select_related('doctor__user', 'hospital').order_by('-appointment_date', '-appointment_time')

    status_filter = request.GET.get('status')
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    context = {
        'appointments': appointments,
        'status_filter': status_filter,
        'statuses': Appointment.STATUS_CHOICES,
    }
    return render(request, 'appointments/my_list.html', context)


@login_required
@require_POST
def cancel_appointment(request, pk):
    """
    BEMOR navbatni bekor qiladi.
    Faqat pending yoki confirmed navbatni bekor qilsa bo'ladi.
    Bekor qilinganda joy avtomatik bo'shaydi (model constraint orqali).
    """
    appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)

    if appointment.status not in ['pending', 'confirmed']:
        return JsonResponse({
            'success': False,
            'message': "Bu navbatni bekor qilib bo'lmaydi."
        })

    cancel_reason = request.POST.get('cancel_reason', '')
    appointment.status = 'cancelled'
    appointment.cancel_reason = cancel_reason
    appointment.save()

    # Shifokorga bildirishnoma
    create_notification(
        user=appointment.doctor.user,
        notif_type='cancelled',
        message=f"{appointment.patient.get_full_name()} navbatni bekor qildi. "
                f"Sana: {appointment.appointment_date}, Soat: {appointment.appointment_time}. "
                f"Sabab: {cancel_reason or 'Ko\'rsatilmagan'}",
        appointment=appointment
    )

    return JsonResponse({
        'success': True,
        'message': "Navbat bekor qilindi. Vaqt endi bo'sh."
    })


@login_required
@require_POST
def mark_no_show(request, pk):
    """
    SHIFOKOR bemorni "Kelmadi" deb belgilaydi.
    Bu amalni faqat o'sha shifokor bajarishi mumkin.
    no_show bo'lganda joy bo'shaydi — boshqa bemor yozila oladi.
    """
    appointment = get_object_or_404(Appointment, pk=pk)

    # Faqat shu navbatning shifokori bajarishi mumkin
    if not hasattr(request.user, 'doctor_profile') or \
       request.user.doctor_profile != appointment.doctor:
        return JsonResponse({
            'success': False,
            'message': "Ruxsat yo'q."
        })

    if appointment.status not in ['pending', 'confirmed']:
        return JsonResponse({
            'success': False,
            'message': "Bu navbatni o'zgartirib bo'lmaydi."
        })

    appointment.status = 'no_show'
    appointment.save()

    # Bemor uchun bildirishnoma
    create_notification(
        user=appointment.patient,
        notif_type='no_show',
        message=f"Dr. {appointment.doctor.user.get_full_name()} navbatingizni 'Kelmadi' deb belgiladi. "
                f"Sana: {appointment.appointment_date}, Soat: {appointment.appointment_time}",
        appointment=appointment
    )

    return JsonResponse({
        'success': True,
        'message': "Bemor 'Kelmadi' deb belgilandi. Vaqt endi bo'sh."
    })


@login_required
@require_POST
def complete_appointment(request, pk):
    """
    SHIFOKOR qabulni 'Tugallandi' deb belgilaydi.
    Doctor notes ham yozishi mumkin.
    """
    appointment = get_object_or_404(Appointment, pk=pk)

    if not hasattr(request.user, 'doctor_profile') or \
       request.user.doctor_profile != appointment.doctor:
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q."})

    doctor_notes = request.POST.get('doctor_notes', '')
    appointment.status = 'completed'
    appointment.doctor_notes = doctor_notes
    appointment.save()

    create_notification(
        user=appointment.patient,
        notif_type='completed',
        message=f"Dr. {appointment.doctor.user.get_full_name()} bilan qabul yakunlandi.",
        appointment=appointment
    )

    return JsonResponse({'success': True, 'message': "Qabul yakunlandi."})


# ═══════════════════════════════════════════════════════
# 5. SHIFOKOR PANELI
# ═══════════════════════════════════════════════════════
@login_required
def doctor_dashboard(request):
    """
    Shifokor o'z navbatlarini ko'radiganpanel.
    Bugungi va kelgusi navbatlar, statistika.
    """
    if not request.user.is_doctor():
        if request.user.role == 'hospital':
            return redirect('hospital_dashboard')
        return redirect('dashboard')

    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        # role='doctor' bo'lsa-da, DoctorProfile hali yaratilmagan
        # (masalan, rolni to'g'ridan-to'g'ri admin panelda o'zgartirilgan,
        # lekin ariza hali to'liq tasdiqlanish (approve_doctor) jarayonidan o'tmagan holatlar uchun)
        return render(request, 'components/profile_pending.html', {
            'title': "Shifokorlik profilingiz hali tayyor emas",
            'message': (
                "Hisobingiz \"shifokor\" sifatida belgilangan, lekin shifohona "
                "tomonidan to'liq tasdiqlangan profil hali yaratilmagan. "
                "Iltimos, ariza holatini shifohona bilan tekshiring."
            ),
        })

    today = timezone.now().date()

    today_appointments = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=today,
        status__in=['pending', 'confirmed']
    ).select_related('patient').order_by('appointment_time')

    upcoming = Appointment.objects.filter(
        doctor=doctor,
        appointment_date__gt=today,
        status__in=['pending', 'confirmed']
    ).select_related('patient').order_by('appointment_date', 'appointment_time')[:10]

    # Haftaning barcha 7 kuni uchun qator tayyorlaymiz (mavjud bo'lsa DoctorSchedule, bo'lmasa None) —
    # shablon bo'sh kunlarni ham "+ Qo'shish" ko'rinishida ko'rsata olishi uchun.
    existing_schedules = {s.weekday: s for s in doctor.schedules.all()}
    schedule_rows = [
        {'num': num, 'name': name, 'schedule': existing_schedules.get(num)}
        for num, name in DoctorSchedule.WEEKDAY_CHOICES
    ]
    has_active_schedule = any(row['schedule'] and row['schedule'].is_active for row in schedule_rows)

    context = {
        'doctor': doctor,
        'today_appointments': today_appointments,
        'upcoming_appointments': upcoming,
        'today': today,
        'schedule_rows': schedule_rows,
        'has_active_schedule': has_active_schedule,
    }
    return render(request, 'doctors/dashboard.html', context)


@login_required
@require_POST
def save_schedule(request):
    """
    Shifokor o'z haftalik ish grafigini bir yo'la saqlaydi (7 kunga qadar).
    Body (JSON): {"days": [{"weekday":0,"is_active":true,"start_time":"09:00","end_time":"18:00","slot_duration":20}, ...]}
    Har bir hafta kuni uchun bittadan yozuv bo'ladi (DoctorSchedule.unique_together).
    """
    if not request.user.is_doctor():
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q"}, status=403)

    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Shifokor profili topilmadi"}, status=404)

    try:
        payload = json.loads(request.body)
        days = payload.get('days', [])
    except (json.JSONDecodeError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'message': "Noto'g'ri so'rov formati"}, status=400)

    valid_weekdays = {num for num, _ in DoctorSchedule.WEEKDAY_CHOICES}
    skipped = []

    for day in days:
        try:
            weekday = int(day.get('weekday'))
        except (TypeError, ValueError):
            continue
        if weekday not in valid_weekdays:
            continue

        is_active = bool(day.get('is_active'))

        if not is_active:
            # Ish kuni emas deb belgilansa — yozuvni o'chirmaymiz, shunchaki nofaol qilamiz
            # (vaqtlar saqlanib qoladi, keyin qayta yoqish oson bo'lishi uchun)
            DoctorSchedule.objects.filter(doctor=doctor, weekday=weekday).update(is_active=False)
            continue

        start_time = day.get('start_time')
        end_time = day.get('end_time')
        slot_duration = day.get('slot_duration') or 20

        if not start_time or not end_time or start_time >= end_time:
            skipped.append(dict(DoctorSchedule.WEEKDAY_CHOICES).get(weekday))
            continue

        DoctorSchedule.objects.update_or_create(
            doctor=doctor,
            weekday=weekday,
            defaults={
                'start_time': start_time,
                'end_time': end_time,
                'slot_duration': slot_duration,
                'is_active': True,
            }
        )

    if skipped:
        return JsonResponse({
            'success': True,
            'message': "Saqlandi, lekin ba'zi kunlar o'tkazib yuborildi (vaqt noto'g'ri): " + ", ".join(skipped),
        })
    return JsonResponse({'success': True, 'message': "Ish grafigi saqlandi"})


@login_required
@require_POST
def toggle_availability(request):
    """
    Shifokor o'zini vaqtincha 'band/mavjud emas' yoki 'mavjud' deb belgilaydi.
    Band deb belgilaganda sabab (ixtiyoriy) ham saqlanadi.
    """
    if not request.user.is_doctor():
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q"}, status=403)

    try:
        doctor = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        return JsonResponse({'success': False, 'message': "Shifokor profili topilmadi"}, status=404)

    if doctor.is_available:
        doctor.is_available = False
        doctor.unavailable_reason = (request.POST.get('reason') or '').strip()
    else:
        doctor.is_available = True
        doctor.unavailable_reason = ''
    doctor.save(update_fields=['is_available', 'unavailable_reason'])

    return JsonResponse({'success': True, 'is_available': doctor.is_available})


# ═══════════════════════════════════════════════════════
# 6. FOYDALANUVCHI DASHBOARD
# ═══════════════════════════════════════════════════════
@login_required
def dashboard(request):
    """
    Bemor dashboard sahifasi.
    Faqat patient rolida bo'lgan foydalanuvchilar kirishi mumkin.
    """
    # Shifokor va shifohona o'z dashboardlariga yo'naltiriladi
    if request.user.role == 'hospital':
        return redirect('hospital_dashboard')
    if request.user.role == 'doctor':
        return redirect('doctor_dashboard')

    upcoming = Appointment.objects.filter(
        patient=request.user,
        status__in=['pending', 'confirmed']
    ).select_related('doctor__user', 'hospital').order_by('appointment_date', 'appointment_time')[:5]

    # ✅ TO'G'RI — avval count, keyin slice
    notifications = Notification.objects.filter(
        user=request.user
    ).order_by('-created_at')

    unread_count = notifications.filter(is_read=False).count()  # slice dan OLDIN

    notifications = notifications[:10]  # count dan KEYIN slice

    context = {
        'upcoming_appointments': upcoming,
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'dashboard.html', context)


# ═══════════════════════════════════════════════════════
# 7. API — Bo'sh vaqt slotlarini qaytaradi (JSON)
# ═══════════════════════════════════════════════════════
def get_available_slots(request):
    """
    AJAX so'rov: ?doctor_id=1&date=2025-01-25
    Band va bo'sh vaqtlarni JSON da qaytaradi.
    Frontend kalendarida band (booked) va bo'sh (available) slotlarni ajratib ko'rsatadi.
    """
    doctor_id = request.GET.get('doctor_id')
    date_str = request.GET.get('date')

    if not doctor_id or not date_str:
        return JsonResponse({'error': 'doctor_id va date kerak'}, status=400)

    doctor = get_object_or_404(DoctorProfile, pk=doctor_id)

    # Band navbatlar (faqat pending va confirmed)
    booked_times = list(
        Appointment.objects.filter(
            doctor=doctor,
            appointment_date=date_str,
            status__in=['pending', 'confirmed']
        ).values_list('appointment_time', flat=True)
    )

    # Band vaqtlarni string ga o'tkazish
    booked_str = [t.strftime('%H:%M') for t in booked_times]

    # Ish grafigidan slotlarni hisoblash
    from datetime import date, datetime, timedelta
    try:
        selected_date = date.fromisoformat(date_str)
    except ValueError:
        return JsonResponse({'error': 'Noto\'g\'ri sana formati'}, status=400)

    weekday = selected_date.weekday()  # 0=Monday

    try:
        schedule = DoctorSchedule.objects.get(doctor=doctor, weekday=weekday, is_active=True)
    except DoctorSchedule.DoesNotExist:
        return JsonResponse({'slots': [], 'message': 'Bu kunda shifokor ishlamaydi'})

    # Slotlarni generate qilish
    slots = []
    current = datetime.combine(selected_date, schedule.start_time)
    end = datetime.combine(selected_date, schedule.end_time)
    delta = timedelta(minutes=schedule.slot_duration)

    while current < end:
        time_str = current.strftime('%H:%M')
        slots.append({
            'time': time_str,
            'available': time_str not in booked_str
        })
        current += delta

    return JsonResponse({
        'slots': slots,
        'doctor': doctor.user.get_full_name(),
        'date': date_str
    })


# ═══════════════════════════════════════════════════════
# 8. BILDIRISHNOMALAR
# ═══════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════
# 8. BILDIRISHNOMALAR
# ═══════════════════════════════════════════════════════
@login_required
def notifications_list(request):
    """
    Foydalanuvchining barcha bildirishnomalari — rolidan qat'iy nazar
    (bemor, shifokor, shifohona hammasi shu bitta sahifadan foydalanadi).
    """
    notifications = request.user.notifications.select_related('appointment').all()
    return render(request, 'notifications/list.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, pk):
    """Bildirishnomani o'qildi deb belgilaydi."""
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save()
    return JsonResponse({'success': True})


@login_required
def mark_all_notifications_read(request):
    """Barcha bildirishnomalarni o'qildi deb belgilaydi."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'success': True})


# ═══════════════════════════════════════════════════════
# 9. AUTH — kirish va chiqish
# ═══════════════════════════════════════════════════════
def login_view(request):
    """
    Kirish sahifasi.
    GET  → forma.
    POST → foydalanuvchini tekshiradi va dashboard ga yo'naltiradi.
    """
    if request.user.is_authenticated:
        if request.user.role == 'hospital':
            return redirect('hospital_dashboard')
        elif request.user.role == 'doctor':
            return redirect('doctor_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            # next= parametri bo'lsa — o'sha sahifaga
            # (login.html da bu qiymat yashirin POST maydonida keladi)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url:
                return redirect(next_url)
            # Rolga qarab to'g'ri dashboardga yo'naltirish
            if user.role == 'hospital':
                return redirect('hospital_dashboard')
            elif user.role == 'doctor':
                return redirect('doctor_dashboard')
            else:
                return redirect('dashboard')
        else:
            return render(request, 'auth/login.html', {
                'error': "Login yoki parol noto'g'ri."
            })

    return render(request, 'auth/login.html')


def logout_view(request):
    """Hisobdan chiqish."""
    logout(request)
    return redirect('index')

# ═══════════════════════════════════════════════════════
# views.py da register_view funksiyasini SHU bilan almashtiring
# ═══════════════════════════════════════════════════════

def register_view(request):
    hospitals   = Hospital.objects.filter(is_active=True).select_related('district__region')
    specialties = MedicalSpecialty.objects.all()

    if request.user.is_authenticated:
        if request.user.role == 'hospital':
            return redirect('hospital_dashboard')
        elif request.user.role == 'doctor':
            return redirect('doctor_dashboard')
        return redirect('dashboard')

    if request.method == 'POST':
        # --- Umumiy maydonlar ---
        role       = request.POST.get('role', 'patient')
        username   = request.POST.get('username', '').strip()
        phone      = request.POST.get('phone', '').strip()
        email      = request.POST.get('email', '').strip()
        password   = request.POST.get('password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name  = request.POST.get('last_name', '').strip()

        # --- Validatsiya ---
        if not all([username, password, first_name, last_name]):
            return render(request, 'auth/register.html', {
                'error': "Ism, familiya, username va parol majburiy.",
                'hospitals': hospitals, 'specialties': specialties,
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'auth/register.html', {
                'error': "Bu username band. Boshqa username tanlang.",
                'hospitals': hospitals, 'specialties': specialties,
            })

        if phone and User.objects.filter(phone=phone).exists():
            return render(request, 'auth/register.html', {
                'error': "Bu telefon raqam allaqachon ro'yxatdan o'tgan.",
                'hospitals': hospitals, 'specialties': specialties,
            })

        # ── BEMOR ──────────────────────────────────────
        if role == 'patient':
            user = User.objects.create_user(
                username=username, password=password,
                email=email, first_name=first_name,
                last_name=last_name, phone=phone or None,
                role='patient',
                is_staff = False,
                is_superuser = False,
            )
            PatientProfile.objects.create(user=user)
            login(request, user)
            return redirect('dashboard')

        # ── SHIFOKOR ───────────────────────────────────
        elif role == 'doctor':
            hospital_id      = request.POST.get('hospital_id')
            specialty_id     = request.POST.get('specialty_id')
            experience_years = request.POST.get('experience_years', 0)
            education        = request.POST.get('education', '').strip()

            if not hospital_id:
                return render(request, 'auth/register.html', {
                    'error': "Shifohonani tanlang.",
                    'hospitals': hospitals, 'specialties': specialties,
                })

            try:
                hospital = Hospital.objects.get(pk=hospital_id, is_active=True)
            except Hospital.DoesNotExist:
                return render(request, 'auth/register.html', {
                    'error': "Tanlangan shifohona topilmadi.",
                    'hospitals': hospitals, 'specialties': specialties,
                })

            specialty = None
            if specialty_id:
                try:
                    specialty = MedicalSpecialty.objects.get(pk=specialty_id)
                except MedicalSpecialty.DoesNotExist:
                    pass

            # User yaratiladi lekin role='patient' — tasdiqlanmaguncha
            # (tasdiqlanganida role='doctor' ga o'zgaradi)
            user = User.objects.create_user(
                username=username, password=password,
                email=email, first_name=first_name,
                last_name=last_name, phone=phone or None,
                role='patient',        # Hali doctor emas
                is_active=True,         # Login qila oladi, lekin dashboard cheklangan
                is_staff=False,
                is_superuser=False,
            )

            # So'rov yaratish
            DoctorApplication.objects.create(
                user=user,
                hospital=hospital,
                specialty=specialty,
                experience_years=int(experience_years) if experience_years else 0,
                education=education,
                status='pending'
            )

            # Shifohona adminga bildirishnoma
            if hasattr(hospital, 'profile'):
                specialty_name = specialty.name if specialty else "mutaxassislik ko'rsatilmagan"
                create_notification(
                    user=hospital.profile.user,
                    notif_type='new_application',
                    message=(
                        f"Yangi shifokor so'rovi: {user.get_full_name()} "
                        f"({specialty_name}). Panelda ko'rib chiqing."
                    )
                )

            return render(request, 'auth/register.html', {
                'success': (
                    f"So'rovingiz '{hospital.name}' ga yuborildi! "
                    f"Shifohona tasdiqlaganidan keyin hisobingiz faollashadi. "
                    f"Tez orada siz bilan bog'lanishadi."
                ),
                'hospitals': hospitals, 'specialties': specialties,
            })

    return render(request, 'auth/register.html', {
        'hospitals': hospitals,
        'specialties': specialties,
    })


# ═══════════════════════════════════════════════════════
# views.py ga QO'SHISH — Shifohona panel views
# ═══════════════════════════════════════════════════════


# ── YORDAMCHI DECORATOR ──────────────────────────────
from functools import wraps
from django.http import HttpResponseForbidden

def hospital_required(view_func):
    """Faqat hospital role uchun."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_hospital():
            return HttpResponseForbidden("Ruxsat yo'q.")
        return view_func(request, *args, **kwargs)
    return wrapper


# ── SHIFOHONA BOSH PANEL ─────────────────────────────
@login_required
def hospital_dashboard(request):
    """
    Shifohona paneli — bosh sahifa.
    Bugungi barcha navbatlar soat bo'yicha, statistika.
    """
    if not request.user.is_hospital():
        if request.user.role == 'doctor':
            return redirect('doctor_dashboard')
        return redirect('dashboard')

    try:
        hospital = Hospital.objects.get(profile__user=request.user)
    except Hospital.DoesNotExist:
        # role='hospital' bo'lsa-da, unga bog'langan Hospital/HospitalProfile yo'q
        return render(request, 'components/profile_pending.html', {
            'title': "Shifohona profili hali bog'lanmagan",
            'message': (
                "Hisobingiz \"shifohona\" sifatida belgilangan, lekin unga "
                "bog'langan shifohona profili topilmadi. Iltimos, administrator "
                "bilan bog'laning."
            ),
        })

    today    = date.today()

    # Bugungi navbatlar — soat bo'yicha
    today_appointments = Appointment.objects.filter(
        hospital=hospital,
        appointment_date=today,
        status__in=['pending', 'confirmed']
    ).select_related(
        'patient', 'doctor__user', 'doctor__specialty'
    ).order_by('appointment_time')

    # Kutayotgan shifokor so'rovlari
    pending_applications = DoctorApplication.objects.filter(
        hospital=hospital,
        status='pending'
    ).select_related('user', 'specialty')

    # Statistika
    total_doctors    = DoctorProfile.objects.filter(hospital=hospital).count()
    active_doctors   = DoctorProfile.objects.filter(hospital=hospital, is_available=True).count()
    total_today      = today_appointments.count()
    total_this_month = Appointment.objects.filter(
        hospital=hospital,
        appointment_date__month=today.month,
        appointment_date__year=today.year,
        status__in=['pending', 'confirmed', 'completed']
    ).count()

    context = {
        'hospital':             hospital,
        'today_appointments':   today_appointments,
        'pending_applications': pending_applications,
        'total_doctors':        total_doctors,
        'active_doctors':       active_doctors,
        'total_today':          total_today,
        'total_this_month':     total_this_month,
        'today':                today,
    }
    return render(request, 'hospital/dashboard.html', context)


# ── SHIFOKORLAR RO'YXATI ─────────────────────────────
@login_required
def hospital_doctors(request):
    """Shifohona o'z shifokorlarini boshqaradi."""
    if not request.user.is_hospital():
        return redirect('dashboard')

    hospital = get_object_or_404(Hospital, profile__user=request.user)
    doctors  = DoctorProfile.objects.filter(
        hospital=hospital
    ).select_related('user', 'specialty').order_by('-is_available', '-rating')

    # Kutayotgan so'rovlar
    pending_applications = DoctorApplication.objects.filter(
        hospital=hospital, status='pending'
    ).select_related('user', 'specialty')

    context = {
        'hospital':             hospital,
        'doctors':              doctors,
        'pending_applications': pending_applications,
    }
    return render(request, 'hospital/doctors.html', context)


# ── SHIFOKOR SO'ROVINI TASDIQLASH ────────────────────
@login_required
@require_POST
def approve_doctor(request, application_id):
    """Shifohona shifokor so'rovini tasdiqlaydi."""
    if not request.user.is_hospital():
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q."})

    hospital    = get_object_or_404(Hospital, profile__user=request.user)
    application = get_object_or_404(
        DoctorApplication, pk=application_id,
        hospital=hospital, status='pending'
    )

    # User ni doctor ga o'tkazish
    application.user.role     = 'doctor'
    application.user.is_staff = False
    application.user.save(update_fields=['role', 'is_staff'])

    # DoctorProfile yaratish
    DoctorProfile.objects.get_or_create(
        user=application.user,
        defaults={
            'hospital':         hospital,
            'specialty':        application.specialty,
            'experience_years': application.experience_years,
            'education':        application.education,
            'is_available':     True,
        }
    )

    application.status = 'approved'
    application.save(update_fields=['status'])

    # Shifokorga bildirishnoma
    Notification.objects.create(
        user=application.user,
        type='confirmed',
        message=(
            f"Tabriklaymiz! '{hospital.name}' shifohonasi "
            f"so'rovingizni tasdiqladi. Endi shifokor sifatida kirishingiz mumkin."
        )
    )

    return JsonResponse({
        'success': True,
        'message': f"{application.user.get_full_name()} tasdiqlandi!"
    })


# ── SHIFOKOR SO'ROVINI RAD ETISH ─────────────────────
@login_required
@require_POST
def reject_doctor(request, application_id):
    """Shifohona shifokor so'rovini rad etadi."""
    if not request.user.is_hospital():
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q."})

    hospital    = get_object_or_404(Hospital, profile__user=request.user)
    application = get_object_or_404(
        DoctorApplication, pk=application_id,
        hospital=hospital, status='pending'
    )

    reject_reason = request.POST.get('reason', '')
    application.status        = 'rejected'
    application.reject_reason = reject_reason
    application.save(update_fields=['status', 'reject_reason'])

    # Shifokorga bildirishnoma
    Notification.objects.create(
        user=application.user,
        type='cancelled',
        message=(
            f"'{hospital.name}' shifohonasi so'rovingizni rad etdi."
            + (f" Sabab: {reject_reason}" if reject_reason else "")
        )
    )

    return JsonResponse({'success': True, 'message': "So'rov rad etildi."})


# ── SHIFOKORNI O'CHIRISH ─────────────────────────────
@login_required
@require_POST
def remove_doctor(request, doctor_id):
    """Shifohona shifokorni ro'yxatdan chiqaradi."""
    if not request.user.is_hospital():
        return JsonResponse({'success': False, 'message': "Ruxsat yo'q."})

    hospital = get_object_or_404(Hospital, profile__user=request.user)
    doctor   = get_object_or_404(DoctorProfile, pk=doctor_id, hospital=hospital)

    doctor_name = doctor.user.get_full_name()

    # Kelgusi navbatlarni bekor qilish
    Appointment.objects.filter(
        doctor=doctor,
        appointment_date__gte=date.today(),
        status__in=['pending', 'confirmed']
    ).update(
        status='cancelled',
        cancel_reason=f"{hospital.name} shifohonasidan chiqarildi"
    )

    # Shifokor profilini o'chirish (user qoladi)
    doctor.user.role = 'patient'
    doctor.user.save(update_fields=['role'])
    doctor.delete()

    return JsonResponse({
        'success': True,
        'message': f"Dr. {doctor_name} ro'yxatdan chiqarildi."
    })


# ── NAVBATLAR (SOAT BO'YICHA) ───────────────────────
@login_required
def hospital_appointments(request):
    """
    Shifohona barcha navbatlarni ko'radi.
    Filter: sana, shifokor, status
    """
    if not request.user.is_hospital():
        return redirect('dashboard')

    hospital = get_object_or_404(Hospital, profile__user=request.user)

    # Filterlar
    selected_date   = request.GET.get('date', str(date.today()))
    selected_doctor = request.GET.get('doctor_id')
    selected_status = request.GET.get('status')

    appointments = Appointment.objects.filter(
        hospital=hospital,
        appointment_date=selected_date
    ).select_related(
        'patient', 'doctor__user', 'doctor__specialty'
    ).order_by('appointment_time')

    if selected_doctor:
        appointments = appointments.filter(doctor_id=selected_doctor)
    if selected_status:
        appointments = appointments.filter(status=selected_status)

    doctors = DoctorProfile.objects.filter(
        hospital=hospital
    ).select_related('user', 'specialty')

    context = {
        'hospital':        hospital,
        'appointments':    appointments,
        'doctors':         doctors,
        'selected_date':   selected_date,
        'selected_doctor': selected_doctor,
        'selected_status': selected_status,
        'status_choices':  Appointment.STATUS_CHOICES,
    }
    return render(request, 'hospital/appointments.html', context)