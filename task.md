# task.md — OpenPyERP Görev Takibi

Bu dosya, projedeki güncel görevleri takip etmek için kullanılır. Yeni bir göreve başlarken "Devam Eden"e taşı, bitirince "Tamamlanan"a taşı ve tarih ekle.

## 🔜 Sıradaki (Aktif Backlog)

- [ ] GitHub'a ilk push öncesi güvenlik taraması: `whatsapp_bi/env` içinde gerçek secret var mı kontrol et
- [ ] `.gitignore` dosyasını gözden geçir / oluştur (`venv/`, `__pycache__/`, `*.pyc`, `*.env`, `htmlcov/`)
- [ ] GitHub uzak repo bağlantısını doğrula (`git remote -v`)

> Uzun vadeli / önceliklendirilmemiş fikirler için bkz. `backlog.md`. Bir fikir buraya taşındığında somut bir göreve dönüşmüş demektir.

## 🚧 Devam Eden

_(şu anda boş — bir göreve başladığında buraya taşı)_

## ✅ Tamamlanan

_(şu anda boş)_

---

### Görev Ekleme Şablonu

```markdown
- [ ] Kısa görev başlığı
  - Bağlam: neden yapılıyor / hangi addon'u ilgilendiriyor
  - Kabul kriteri: ne zaman "bitti" sayılır
  - İlgili dosyalar: addons/xxx/services.py, ...
```

