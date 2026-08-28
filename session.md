# session.md — OpenPyERP Oturum Günlüğü

Her çalışma oturumunda buraya kısa bir kayıt düşülür: ne yapıldı, hangi kararlar alındı, sıradaki adım ne. Amaç, bir sonraki oturuma (veya başka bir geliştiriciye/Claude örneğine) hızlıca bağlam aktarmak.

---

## Şablon

```markdown
## YYYY-AA-GG

**Yapılanlar:**
- ...

**Alınan kararlar / neden:**
- ...

**Açık sorunlar / bilinen eksikler:**
- ...

**Sıradaki adım:**
- ...
```

---

## 2026-08-28

**Yapılanlar:**
- Proje dokümantasyonu gözden geçirildi (README.md, GELISTIRME_DOKUMANI.md).
- Claude Code iş akışı için `CLAUDE.md`, `architect.md`, `task.md`, `session.md` dosyaları oluşturuldu.
- `backlog.md` fikir/özellik havuzu dosyası oluşturuldu.

**Alınan kararlar / neden:**
- Bu 5 dosya repo köküne konulacak (CLAUDE.md Claude Code tarafından otomatik okunur).
- `whatsapp_bi/env` hiç commit edilmemiş — güvenlik riski yok, push'a hazır.

**Açık sorunlar / bilinen eksikler:**
- Hiçbiri.

**Sıradaki adım:**
- `git add .` → `git status` → `git commit` → `git push origin main` ile GitHub'a yolla.

