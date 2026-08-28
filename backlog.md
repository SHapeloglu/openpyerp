# backlog.md — OpenPyERP Fikir / Özellik Havuzu

Bu dosya henüz önceliklendirilmemiş, "bir gün yapılabilir" fikirler ve özellik talepleri içindir. Bir fikir somutlaşıp sıraya girdiğinde buradan çıkar, `task.md` → Backlog bölümüne taşınır.

`task.md` ile fark:
- **backlog.md** → uzun vadeli, önceliksiz, henüz kararlaştırılmamış fikirler
- **task.md** → aktif olarak üzerinde çalışılan veya bir sonraki sırada olan görevler

## Fikirler

_(henüz boş — yeni bir fikir geldiğinde aşağıdaki şablonla ekle)_

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

