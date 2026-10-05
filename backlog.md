# backlog.md — OpenPyERP Fikir / Özellik Havuzu

Bu dosya henüz önceliklendirilmemiş, "bir gün yapılabilir" fikirler ve özellik talepleri içindir. Bir fikir somutlaşıp sıraya girdiğinde buradan çıkar, `task.md` → Backlog bölümüne taşınır.

`task.md` ile fark:
- **backlog.md** → uzun vadeli, önceliksiz, henüz kararlaştırılmamış fikirler
- **task.md** → aktif olarak üzerinde çalışılan veya bir sonraki sırada olan görevler

## Fikirler

### CariMatik'ten henüz taşınmamış alanlar

- **Kategori:** yeni özellik · **Addon:** yeni / `finans` / `personel`
- CariMatik (`/root/projects/CariMatik/app.py`, 63 model) ile karşılaştırıldığında OpenPyERP'te **model karşılığı olmayan** alanlar: çek/senet portföyü ve taksit planı, döviz türleri, cari hesap fişi, hesap grubu, il/ilçe/mahalle adresleri, proje & masraf merkezi, hedef, üretim reçetesi, varyant ve fiyat listeleri, belge tasarımı, kullanıcı tanımlı SQL raporları, kullanıcı-şirket/depo/belge yetki tabloları, personel evrak/hakediş; ayrıca muhasebeci erişimi ve POS ekranı. `finans` addon'unda şu an yalnız Kasa/Banka ve hareketleri, `personel`'de Personel/İzin/Puantaj var. Kesin liste için iki model kümesini karşılaştır.
- Her biri ayrı addon (manifest + `KAYITLI_ADDONLAR` + Alembic migration) olarak taşınmalı.

### Diğer fikirler

- e-Fatura / e-Arşiv: Sovos entegrasyon deneyimini (`l10n_tr_sovos_efatura`) bir `efatura` addon'una uyarlamak.
- `eticaret` addon'unu (şu an `extends.py` + migration) README'deki pazaryeri/ödeme hedefleriyle netleştirmek.
- `whatsapp_bi` modülünü (doğal dil → rapor) addon yapısına almak.
- Test kapsamı: şu an yalnız `belge` (hesaplama, servis) ve workflow testleri var — `cari`, `stok`, `finans` servisleri için unit testler.

## Ekleme Şablonu

```markdown
### Başlık

- **Kategori:** yeni özellik / iyileştirme / teknik borç / araştırma
- **Hangi addon'u ilgilendiriyor:** örn. `belge`, `stok`, altyapı
- **Neden istendi:** kısa gerekçe
- **Ön tahmin / notlar:** varsa büyüklük tahmini, bağımlılıklar, riskler
```

## Bilinen Teknik Borç Adayları (dokümantasyondan çıkarılan notlar)

Bunlar henüz görev haline getirilmedi, sadece `GELISTIRME_DOKUMANI.md`'de dikkat çekilen konular:

- Alembic autogenerate migration'ları her zaman doğru tahmin etmeyebiliyor (özellikle index/constraint isimleri) — gözden geçirme sürecini standartlaştırmak faydalı olabilir.
- `KAYITLI_ADDONLAR` listesine eklemeyi unutma hatası sık yaşanıyor — bir CI kontrolü veya `make` hedefi ile otomatik doğrulama eklenebilir (örn. `addons/` altındaki manifestler ile registry listesini karşılaştıran bir script).

