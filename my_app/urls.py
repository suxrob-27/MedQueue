# my_app/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # ═══════════════════════════════
    # ASOSIY SAHIFALAR
    # ═══════════════════════════════
    path('', views.index, name='index'),
    # Misol: http://127.0.0.1:8000/

    path('shifohonalar/', views.hospital_list, name='hospital_list'),
    # Misol: http://127.0.0.1:8000/shifohonalar/
    # Filterlar: ?region=1&specialty=2&q=nur

    path('shifohonalar/<int:pk>/', views.hospital_detail, name='hospital_detail'),
    # Misol: http://127.0.0.1:8000/shifohonalar/1/

    path('shifokorlar/<int:pk>/', views.doctor_detail, name='doctor_detail'),
    # Misol: http://127.0.0.1:8000/shifokorlar/1/

    # ═══════════════════════════════
    # NAVBAT
    # ═══════════════════════════════
    path('navbat/olish/', views.book_appointment, name='book_appointment'),
    # GET  → forma
    # POST → navbat yaratish

    path('navbat/<int:pk>/', views.appointment_detail, name='appointment_detail'),
    # Navbat tafsilotlari

    path('navbatlarim/', views.my_appointments, name='my_appointments'),
    # Bemor o'z navbatlarini ko'radi
    # ?status=pending yoki ?status=completed

    path('navbat/<int:pk>/bekor/', views.cancel_appointment, name='cancel_appointment'),
    # BEMOR bekor qiladi (POST)

    path('navbat/<int:pk>/kelmadi/', views.mark_no_show, name='mark_no_show'),
    # SHIFOKOR "Kelmadi" belgilaydi (POST)

    path('navbat/<int:pk>/tugallandi/', views.complete_appointment, name='complete_appointment'),
    # SHIFOKOR "Tugallandi" belgilaydi (POST)

    # ═══════════════════════════════
    # DASHBOARD
    # ═══════════════════════════════
    path('dashboard/', views.dashboard, name='dashboard'),
    # Bemor dashboard

    path('shifokor/panel/', views.doctor_dashboard, name='doctor_dashboard'),
    # Shifokor paneli

    path('shifokor/grafik/saqlash/', views.save_schedule, name='save_schedule'),
    # Shifokor haftalik ish grafigini saqlaydi (POST, JSON)

    path('shifokor/holat/almashtirish/', views.toggle_availability, name='toggle_availability'),
    # Shifokor o'zini band/mavjud deb belgilaydi (POST)

    # ═══════════════════════════════
    # API (AJAX uchun)
    # ═══════════════════════════════
    path('api/bosh-vaqtlar/', views.get_available_slots, name='get_available_slots'),
    # GET: ?doctor_id=1&date=2025-01-25
    # JSON qaytaradi: bo'sh va band vaqtlar

    # ═══════════════════════════════
    # BILDIRISHNOMALAR
    # ═══════════════════════════════
    path('bildirishnomalar/', views.notifications_list, name='notifications_list'),
    path('bildirishnoma/<int:pk>/oqildi/', views.mark_notification_read, name='mark_notification_read'),
    path('bildirishnomalar/barchasi-oqildi/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # ═══════════════════════════════
    # AUTH
    # ═══════════════════════════════
    path('kirish/', views.login_view, name='login'),
    path('chiqish/', views.logout_view, name='logout'),
    path('royxatdan-otish/', views.register_view, name='register'),
    path('shifohona/panel/',            views.hospital_dashboard,    name='hospital_dashboard'),
    path('shifohona/shifokorlar/',      views.hospital_doctors,      name='hospital_doctors'),
    path('shifohona/navbatlar/',        views.hospital_appointments, name='hospital_appointments'),
    path('shifohona/tasdiqlash/<int:application_id>/', views.approve_doctor, name='approve_doctor'),
    path('shifohona/rad-etish/<int:application_id>/',  views.reject_doctor,  name='reject_doctor'),
    path('shifohona/olib-tashlash/<int:doctor_id>/',   views.remove_doctor,  name='remove_doctor'),
]