# Email-Agent Skill

Automatischer E-Mail-Agent für mastenluisalfonso.academy@gmail.com.

Liest alle ungelesenen E-Mails, kategorisiert sie anhand der Erkennungsmerkmale aus `context/email-vorlagen.md` und antwortet entsprechend.

## Ablauf

1. **Vorlagen laden**: Lies `context/email-vorlagen.md` um die Kategorien und Vorlagen zu kennen.

2. **E-Mails abrufen**: Nutze das Tool `list_unread_emails` (max_results: 50) um alle ungelesenen E-Mails zu holen.

3. **Ignorieren**: Überspringe E-Mails von Absendern wie `noreply@`, `no-reply@`, `donotreply@`, sowie bekannte System-Mails (ThriveCart, SamCart, Stripe, PayPal, Rechnungen, Quittungen, Newsletter). Diese werden NICHT bearbeitet und auch NICHT als gelesen markiert.

4. **Jede E-Mail verarbeiten**:
   - Lade den vollständigen Inhalt mit `get_email`
   - Analysiere Betreff + Body auf Kategorie-Schlüsselwörter
   - Ersetze `{Name}` in der Vorlage durch den extrahierten Vornamen des Absenders

5. **Je nach Kategorie handeln**:

   | Kategorie | Erkennungsmerkmale | Aktion |
   |-----------|-------------------|--------|
   | Kündigung / Widerruf | kündigen, stornieren, Widerruf, Rückerstattung, Geld zurück, abmelden | `send_reply` (sofort senden) |
   | Login / Zugang fehlt | Zugang, Login, Passwort, einloggen, kann nicht, Zugriff, Link funktioniert nicht, Konto | `send_reply` (sofort senden) |
   | ARIA-Fragen | ARIA, KI, künstliche Intelligenz, wie funktioniert, was kann, erklär mir, Assistent | `create_draft` (Entwurf) |
   | Webinar / Termine | Webinar, Termin, wann, Link, Aufzeichnung, verpasst, nächste Session | `create_draft` (Entwurf) |
   | Unbekannt / Sonstiges | Alles andere | `create_draft` mit `[PRÜFEN]` im Betreff |

6. **Nach Bearbeitung**: Markiere jede bearbeitete E-Mail mit `mark_as_read` als gelesen.

7. **Abschlussbericht**: Gib eine übersichtliche Zusammenfassung aus:
   ```
   ✅ E-Mail-Agent Durchlauf — [Datum]
   
   Verarbeitet: X E-Mails
   ├── Gesendet (Kündigung): X
   ├── Gesendet (Login): X
   ├── Entwurf erstellt (ARIA): X
   ├── Entwurf erstellt (Webinar): X
   ├── Entwurf erstellt (Sonstiges/[PRÜFEN]): X
   └── Ignoriert (System/Spam): X
   ```

## Wichtige Regeln

- **Nur menschliche Absender bearbeiten** — keine automatischen Mails
- **{Name}** immer durch den echten Vornamen ersetzen, nie als `{Name}` lassen
- **Betreff für Entwürfe** mit `[PRÜFEN]` bei unbekannter Kategorie
- **Niemals raten** — wenn unklar, lieber Entwurf als automatisch senden
- **Immer als gelesen markieren** nach der Bearbeitung, nie bei ignorierten Mails
