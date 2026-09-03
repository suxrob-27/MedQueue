// =============================================
// MedQueue — main.js
// Django template bilan to'g'irlangan
// =============================================

// ===== LOADER =====
window.addEventListener('load', () => {
    const loader = document.getElementById('loaderOverlay');
    if (loader) {
        setTimeout(() => {
            loader.classList.add('hidden');
        }, 1200);
    }
    initApp();
});

function initApp() {
    initScrollEffects();
    initCounters();
    initIntersectionObserver();
}

// ===== NAVBAR SCROLL =====
window.addEventListener('scroll', () => {
    const navbar = document.getElementById('navbar');
    if (!navbar) return;
    navbar.classList.toggle('scrolled', window.scrollY > 50);
});

// ===== MOBILE MENU =====
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const hamburger = document.getElementById('hamburger');
    if (!menu || !hamburger) return;

    menu.classList.toggle('open');
    const spans = hamburger.querySelectorAll('span');
    if (menu.classList.contains('open')) {
        spans[0].style.transform = 'rotate(45deg) translate(5px, 5px)';
        spans[1].style.opacity = '0';
        spans[2].style.transform = 'rotate(-45deg) translate(5px, -5px)';
    } else {
        spans.forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
    }
}

// Tashqarini bossangiz menyu yopiladi
document.addEventListener('click', (e) => {
    const menu = document.getElementById('mobileMenu');
    const hamburger = document.getElementById('hamburger');
    if (menu && hamburger && menu.classList.contains('open')) {
        if (!menu.contains(e.target) && !hamburger.contains(e.target)) {
            menu.classList.remove('open');
            hamburger.querySelectorAll('span').forEach(s => { s.style.transform = ''; s.style.opacity = ''; });
        }
    }
});

// ===== TOAST NOTIFICATIONS =====
function showToast(title, message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'fas fa-check',
        error: 'fas fa-times',
        warning: 'fas fa-bell',
        info: 'fas fa-info'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <div class="toast-icon"><i class="${icons[type] || icons.info}"></i></div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-desc">${message}</div>
        </div>
        <i class="fas fa-times toast-close" onclick="removeToast(this.parentElement)"></i>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('show')));
    setTimeout(() => removeToast(toast), type === 'warning' ? 6000 : 4000);
    return toast;
}

function removeToast(toast) {
    if (!toast) return;
    toast.classList.add('hiding');
    setTimeout(() => toast.remove(), 400);
}

// ===== COUNTER ANIMATION =====
function initCounters() {
    const counters = document.querySelectorAll('[data-target]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-target'));
        if (isNaN(target)) return;
        animateCounter(counter, target);
    });
}

function animateCounter(el, target) {
    let current = 0;
    const steps = 60;
    const increment = target / steps;
    const interval = 2000 / steps;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        el.textContent = Math.floor(current) + '+';
    }, interval);
}

// ===== INTERSECTION OBSERVER (scroll animatsiyasi) =====
function initIntersectionObserver() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.animate-fade-up').forEach(el => observer.observe(el));
}

// ===== SCROLL EFFECTS =====
function initScrollEffects() {
    // Hero parallax — faqat hero sahifada
    const orbs = document.querySelectorAll('.hero-orb');
    if (orbs.length > 0) {
        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            orbs.forEach((orb, i) => {
                orb.style.transform = `translateY(${scrollY * (i + 1) * 0.2}px)`;
            });
        }, { passive: true });
    }
}

// ===== SMOOTH SCROLL (anchor links) =====
document.addEventListener('click', (e) => {
    const link = e.target.closest('a[href^="#"]');
    if (!link) return;
    const id = link.getAttribute('href').slice(1);
    const el = document.getElementById(id);
    if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
});

// ===== ESC — modal yopish =====
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        // Inline modals (dashboard, appointments)
        document.querySelectorAll('[id$="Modal"]').forEach(m => {
            if (m.style.display === 'flex') m.style.display = 'none';
        });
    }
});

// ===== PASSWORD KO'RSATISH =====
// base.html da inline ishlatiladi, shu yerda ham qoldiramiz
function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
        input.type = 'text';
        if (icon) icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        input.type = 'password';
        if (icon) icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
}

// ===== CARD HOVER (smooth) =====
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.feature-card, .clinic-card, .specialty-item').forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
        });
    });
});

// ===== AJAX NAVBAT BEKOR QILISH =====
// dashboard.html va my_list.html dagi bekor qilish tugmalari
// uchun umumiy funksiya (har sahifada alohida ham yozilgan)

// ===== SHIFOKOR DASHBOARD — Vaqt formatlash =====
// doctor/dashboard.html da ishlatiladigan yordamchi
function formatTime(timeStr) {
    if (!timeStr) return '';
    const parts = timeStr.split(':');
    return `${parts[0]}:${parts[1]}`;
}