# Liceo Fermi — Vincoli attesi (test del solver)

Conflitti inseriti **deliberatamente** nel dataset, da usare come banco di prova del
generatore. Distinti da *come EDT esprime i vincoli* (quello sta in
[docs/edt/vincoli.md](../../docs/edt/vincoli.md)).

- **Docente single-point** — D16 (DIS) e D17 (MOT) coprono da soli tutte le 10
  classi: 20 ore su 30 slot, occupazione 67%. Sono i vincoli più stretti.
- **Risorsa contesa** — la palestra regge 2 classi, ma D17 è uno solo: di fatto
  mono-classe. Idem per AUL-DIS con D16. Il collo di bottiglia è il docente, non la
  capienza dell'aula.
- **Laboratori** — FIS e SCI vanno prenotati, tipicamente 1 h/sett. per classe,
  preferibilmente in blocchi da 2 ore consecutive.
- **Spezzoni** — D06, D09, D15 richiedono giorni di indisponibilità.
- **Blocchi orari** — MAT nel biennio (5 h) va quasi sempre in 2+1+1+1 o 2+2+1.
- **Quadratura per materia, non solo totale** — caso reale capitato nell'inserimento
  EDT (2026-07-09): STO e SCI invertite (3h/2h) nei servizi del triennio; il totale
  classe (30h) e il totale bisogni (288h) tornavano lo stesso. Il validatore del
  nostro schema deve controllare il monte ore **per materia × piano**, non solo le
  somme.
