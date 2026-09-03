"""
Loyiha bo'ylab ishlatiladigan context processor'lar.
"""


def notifications(request):
    """
    Navbardagi qo'ng'iroq belgisi uchun o'qilmagan bildirishnomalar sonini
    HAR BIR sahifada (rolidan qat'iy nazar — bemor, shifokor, shifohona)
    avtomatik taqdim etadi.

    Avval bu faqat bemor dashboard view'ida qo'lda hisoblanardi, shu sababli
    boshqa barcha sahifalarda (jumladan shifohona va shifokor panellarida)
    'unread_count' aniqlanmagan bo'lib, qo'ng'iroq belgisi ishlamas edi.
    """
    if request.user.is_authenticated:
        return {
            'unread_count': request.user.notifications.filter(is_read=False).count(),
        }
    return {}