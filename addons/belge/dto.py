"""
addons/belge/dto.py — Veri Transfer Nesneleri (Data Transfer Objects)

NEDEN BU DOSYA VAR?
    Eski app.py'deki belge_form() route'u, `request.form` (Flask'ın HTTP form
    nesnesi) içindeki alanları doğrudan okuyup model nesnelerine yazıyordu.
    Bu, servis katmanını HTTP'den ayıramamamızın temel sebebiydi: bir servis
    fonksiyonu yazmak istersek, ona "request.form benzeri" bir şey vermek
    zorunda kalırdık.

    Çözüm: routes.py, HTTP isteğini (form verisi, JSON body, query string —
    KAYNAĞI ÖNEMLİ DEĞİL) bu DTO'lara çevirir. services.py SADECE bu DTO'ları
    bilir — Flask'ın var olduğunu bile bilmez. Bu sayede:
    1. Aynı servis, web formundan da, mobil JSON API'den de, ileride bir CLI
       toplu içe aktarma scriptinden de çağrılabilir.
    2. Servis fonksiyonları, sahte bir Flask request kurmadan unit test edilir.

Odoo'da bu role en yakın şey, ORM'in kendi `vals` (values dict) sözleşmesidir
— `self.write({'durum': 'ACIK', ...})`. Burada tip güvenliği için dataclass
kullanıyoruz; daha katı ama daha az hataya açık.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List


@dataclass
class BelgeSatirGirdi:
    """Bir belge satırının ham girdi verisi (henüz hesaplanmamış)."""
    stok_id: Optional[int]
    miktar: float
    birim_fiyat: float
    birim_id: Optional[int] = None
    aciklama: str = ''
    iskonto_oran: float = 0.0
    kdv_orani: float = 20.0
    donusum_carpan: float = 1.0


@dataclass
class BelgeKaydetGirdi:
    """BelgeOlusturServisi.kaydet() için tüm girdi — routes.py bunu request'ten doldurur."""
    belge_tip: str                  # TALEP | SIPARIS | IRSALIYE | FATURA
    cari_tip: str                   # SATIS | ALIS
    tarih: date
    cari_id: Optional[int]
    sirket_id: Optional[int]
    satirlar: List[BelgeSatirGirdi] = field(default_factory=list)
    baslik_id: Optional[int] = None  # None = yeni belge, dolu = güncelleme
    vade_tarihi: Optional[date] = None
    depo_id: Optional[int] = None
    evrak_no: str = ''
    aciklama: str = ''
    durum: str = 'ACIK'
    sevk_durumu: Optional[str] = None


@dataclass
class BelgeKaydetSonuc:
    """Servisin döndürdüğü sonuç — routes.py'nin flash mesajı + redirect üretmesi için yeterli bilgi."""
    basarili: bool
    belge_id: Optional[int] = None
    belge_no: Optional[str] = None
    hata_mesaji: Optional[str] = None
    hata_kodu: Optional[str] = None  # 'DONEM_KILITLI' | 'YETERSIZ_STOK' | 'DB_HATASI' | None
