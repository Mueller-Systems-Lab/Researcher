# Researcher — Onion Discovery Engine
# Seed-basierte Onion Discovery gemäß ADR-007.
# Komponenten:
#   seed_queue.SeedQueue      — Seed-Verwaltung mit Prioritäten
#   policy_gateway.PolicyGateway — Blocklist, Allowlist, Opt-out
#   link_extractor.LinkExtractor — Onion-Link-Extraktion
#   classifier.Classifier      — Themen-/Risiko-Klassifikation
#   human_review.ReviewQueue   — Manuelle Freigabe-Warteschlange
#   engine.DiscoveryPipeline   — Haupt-Pipeline-Orchestrator
