---
title: "SearXNG lokal via Docker Compose"
status: draft
---

# SearXNG lokal via Docker Compose

Diese Notiz fasst die für T-003 validierten Punkte aus der offiziellen SearXNG-Doku zusammen.

## Gültige Fakten

- Die Container-Installation per Compose ist der empfohlene Weg.
- `settings.yml` liegt im Container unter `/etc/searxng/settings.yml`.
- `search.formats` unterstützt `html` und `json`.
- `server.bind_address: "0.0.0.0"` ist im Container okay; die Host-Bindung regelt den Zugriff.
- `plugins:` ist der aktuelle Konfigurationsbereich; `enabled_plugins:` wird nicht mehr verwendet.
- Der Limiter benötigt Valkey. Für ein rein lokales Setup ist es einfacher, `server.limiter: false` zu lassen.

## Empfohlene Ablage

```text
searxng/
├── docker-compose.yml
├── settings.yml
└── limiter.toml
scripts/
└── start-searxng.sh
```

Wichtig: Wenn `docker compose -f searxng/docker-compose.yml ...` verwendet wird, sollten die Mounts in der Compose-Datei auf `./settings.yml` und `./limiter.toml` zeigen.

## Beispiel: `searxng/docker-compose.yml`

```yaml
services:
  searxng:
    image: searxng/searxng:latest
    ports:
      - "127.0.0.1:8080:8080"
    restart: unless-stopped
    environment:
      SEARXNG_BASE_URL: http://localhost:8080/
    volumes:
      - ./settings.yml:/etc/searxng/settings.yml:ro
      - ./limiter.toml:/etc/searxng/limiter.toml:ro
```

## Beispiel: `searxng/settings.yml`

```yaml
use_default_settings:
  engines:
    keep_only:
      - duckduckgo
      - wikipedia
      - wikidata

server:
  bind_address: "0.0.0.0"
  port: 8080
  base_url: "http://localhost:8080/"
  limiter: false

search:
  safe_search: 0
  formats:
    - html
    - json

ui:
  static_use_hash: true

plugins: {}
```

Hinweis: `google` und `bing` sind offizielle Engines und können später ergänzt werden. Für den minimalen lokalen Betrieb reichen `duckduckgo`, `wikipedia` und `wikidata`.

## Beispiel: `searxng/limiter.toml`

Die offizielle Vorlage kennt keine numerischen Grenzwerte wie `ip_limit = 999`.

```toml
[botdetection]
ipv4_prefix = 32
ipv6_prefix = 48
trusted_proxies = [
  '127.0.0.0/8',
  '::1',
]

[botdetection.ip_limit]
filter_link_local = false
link_token = false

[botdetection.ip_lists]
pass_ip = [
  '127.0.0.0/8',
  '::1',
]
pass_searxng_org = true
```

Wenn `server.limiter: false` gesetzt ist, bleibt diese Datei nur vorbereitend.

## Beispiel: `scripts/start-searxng.sh`

```bash
#!/bin/bash
# Startet SearXNG-Docker-Container
docker compose -f searxng/docker-compose.yml up -d
echo "SearXNG läuft auf http://127.0.0.1:8080"
echo "Test: curl 'http://127.0.0.1:8080/search?q=test&format=json'"
```

## Test

```bash
curl "http://localhost:8080/search?q=test&format=json"
```

Erwartung: gültiges JSON mit Suchtreffern.

## Quellen

- https://docs.searxng.org/admin/installation-docker.html
- https://docs.searxng.org/admin/settings/settings.html
- https://docs.searxng.org/admin/settings/settings_search.html
- https://docs.searxng.org/admin/settings/settings_server.html
- https://docs.searxng.org/admin/settings/settings_ui.html
- https://docs.searxng.org/admin/settings/settings_plugins.html
- https://docs.searxng.org/admin/searx.limiter.html
