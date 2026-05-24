# com_audit — Audit log pro KLUCON CMS

Zaznamenává administrativní a bezpečnostní události (přihlášení, odhlášení, změny uživatelů, systémové akce) do databáze. Přehled a filtrování záznamů je dostupné v administraci na `/admin/com_audit`.

## Události

| Hook | Kdy |
|------|-----|
| `user.login` | Přihlášení uživatele |
| `user.logout` | Odhlášení uživatele |
| `user.created` | Vytvoření uživatele |
| `user.updated` | Změna uživatele |
| `user.deleted` | Smazání uživatele |
| `app.startup` | Start aplikace (volitelné) |
| `app.shutdown` | Zastavení aplikace (volitelné) |

## Nastavení

| Klíč | Výchozí | Popis |
|------|---------|-------|
| `retention_days` | 90 | Počet dní, po které se záznamy uchovávají |
| `log_app_events` | false | Logovat app.startup / app.shutdown |

## Vývoj a testy

```bash
cd component/com_audit
pip install -e ".[dev]"
pytest -q
```
