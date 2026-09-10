# Backlog de implementação

8 releases e 42 entregas propostas. IDs MP são locais; nenhum ticket Jira foi criado.
Fonte editável: [backlog.json](backlog.json). Regenerar com `python3 docs/morpheus-plan/scripts/export_backlog.py`.
Todos começam em draft/Backlog. Refinar itens L antes de Ready. Critérios de release em [releases](../05-releases.md).

## R0 — Demanda compreendida (0.1.0)

Transformar demanda sintética em proposta e backlog rastreáveis.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-001 — Publicar o plano numa branch descendente do Hermes](items/MP-001-bootstrap-fork.md) | Operador/TL | S | Nenhuma |
| [MP-002 — Habilitar a extensão e verificar sua compatibilidade](items/MP-002-plugin-opt-in.md) | TL/Backend | M | MP-001 |
| [MP-003 — Receber uma demanda e produzir brief com dúvidas explícitas](items/MP-003-intake-brief.md) | PM/Backend | M | MP-002 |
| [MP-004 — Converter brief aprovado em spec e fatias verticais](items/MP-004-spec-tickets.md) | PO/TL | M | MP-003 |
| [MP-005 — Publicar backlog rastreável no Jira sem duplicações](items/MP-005-jira-backlog.md) | PO/Backend | M | MP-001, MP-004 |

## R1 — Projetos protegidos (0.2.0)

Atender dois clientes em ambientes separados sem compartilhar contexto.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-006 — Provisionar projeto com identidade e ambiente exclusivos](items/MP-006-project-binding.md) | Backend/SRE | M | MP-002, MP-005 |
| [MP-007 — Executar tarefa em worker isolado e descartável](items/MP-007-isolated-worker.md) | SRE/Security | M | MP-006 |
| [MP-008 — Manter memória e handoffs privados por projeto](items/MP-008-private-memory.md) | Backend/Security | M | MP-006, MP-007 |
| [MP-009 — Conceder ferramentas GitHub e Jira com escopo limitado](items/MP-009-tool-broker.md) | Backend/Security | M | MP-005, MP-007 |
| [MP-010 — Onboardar repo recebido sem executar extensões não curadas](items/MP-010-quarantine-repo.md) | Security/TL | M | MP-007, MP-009 |
| [MP-011 — Demonstrar separação de dois clientes e resposta a incidente](items/MP-011-tenant-proof.md) | QA/Security | M | MP-008, MP-009, MP-010 |

## R2 — Primeira entrega web (0.3.0)

Entregar uma jornada web/API com testes, PR e staging.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-012 — Executar uma fatia com claim e checkpoint duráveis](items/MP-012-durable-run.md) | Backend | M | MP-011 |
| [MP-013 — Qualificar especialistas web com um catálogo curado](items/MP-013-web-roles.md) | TL/QA | M | MP-010, MP-012 |
| [MP-014 — Entregar uma jornada web e API a partir de ticket](items/MP-014-web-vertical-slice.md) | FullStack | M | MP-004, MP-012, MP-013 |
| [MP-015 — Publicar commit e PR com evidências verificadas](items/MP-015-publish-pr.md) | Backend/TL | M | MP-009, MP-014 |
| [MP-016 — Revisar spec e padrões e aplicar o gate de aceite](items/MP-016-review-gates.md) | QA/TL/PO | M | MP-015 |
| [MP-017 — Demonstrar a primeira entrega em staging na Hostinger](items/MP-017-staging-delivery.md) | SRE/PO | M | MP-016 |

## R3 — Evolução de legado (0.4.0)

Evoluir software existente com baseline e regressão controlados.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-018 — Mapear sistema existente com evidência e lacunas](items/MP-018-brownfield-intake.md) | TL/Backend | M | MP-010, MP-017 |
| [MP-019 — Fixar baseline de comportamento do legado](items/MP-019-legacy-baseline.md) | QA/Backend | M | MP-018 |
| [MP-020 — Corrigir um defeito do legado com regressão](items/MP-020-legacy-fix.md) | Backend | M | MP-019 |
| [MP-021 — Evoluir contrato do legado com migração compatível](items/MP-021-legacy-expand-contract.md) | TL/Backend | L | MP-019, MP-020 |
| [MP-022 — Entregar relatório e aceite de evolução do sistema existente](items/MP-022-legacy-acceptance.md) | PO/QA | S | MP-020, MP-021 |

## R4 — Entrega mobile (0.5.0)

Entregar Android, iOS e Flutter com evidências por plataforma.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-023 — Entregar fluxo Android em CI isolada](items/MP-023-android-delivery.md) | Android/QA | M | MP-013, MP-017, MP-022 |
| [MP-024 — Entregar fluxo iOS via runner macOS](items/MP-024-ios-delivery.md) | iOS/QA | M | MP-013, MP-017, MP-022 |
| [MP-025 — Entregar fluxo Flutter nos alvos aprovados](items/MP-025-flutter-delivery.md) | Flutter/QA | M | MP-023, MP-024 |
| [MP-026 — Validar UX e ciclo de vida dos apps móveis](items/MP-026-mobile-quality.md) | QA/UX | M | MP-023, MP-024, MP-025 |
| [MP-027 — Distribuir candidatos móveis para aceite interno](items/MP-027-mobile-release.md) | SRE/PO | M | MP-026 |

## R5 — Aprendizado reutilizável (0.6.0)

Reusar conhecimento genérico aprovado sem expor clientes.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-028 — Registrar aprendizado privado como candidato de reuso](items/MP-028-knowledge-candidate.md) | TL/Backend | M | MP-008, MP-022 |
| [MP-029 — Reescrever e aprovar solução genérica sanitizada](items/MP-029-knowledge-promotion.md) | Security/Curador | M | MP-028 |
| [MP-030 — Consumir catálogo aprovado em outro projeto sintético](items/MP-030-knowledge-consume.md) | Backend/QA | M | MP-029 |
| [MP-031 — Revogar conhecimento e invalidar versões consumidoras](items/MP-031-knowledge-revoke.md) | Backend/Security | M | MP-030 |
| [MP-032 — Medir utilidade e risco do aprendizado compartilhado](items/MP-032-knowledge-eval.md) | QA/TM | S | MP-030, MP-031 |

## R6 — Continuidade operacional (0.7.0)

Avançar backlog por schedule e atualizar Hermes de forma recuperável.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-033 — Executar a mesma tarefa por Codex e Claude com retomada](items/MP-033-portable-runners.md) | Backend/QA | M | MP-012, MP-016, MP-032 |
| [MP-034 — Avançar backlog por schedule com limites de custo](items/MP-034-scheduled-work.md) | TM/Backend | M | MP-033, MP-027 |
| [MP-035 — Recuperar falhas sem duplicar efeitos externos](items/MP-035-failure-reconciliation.md) | Backend/QA | M | MP-034 |
| [MP-036 — Incorporar uma atualização do Hermes por PR validado](items/MP-036-upstream-sync.md) | TL/SRE | M | MP-002, MP-035 |
| [MP-037 — Exibir progresso, custo e bloqueios por projeto](items/MP-037-operations-report.md) | TM/PO | M | MP-035, MP-036 |

## R7 — Serviço na Hostinger (1.0.0)

Operar piloto autorizado com recuperação, monitoramento e aceite.

| Ticket | Papel | Tamanho | Dependências |
|---|---|---|---|
| [MP-038 — Provisionar ambiente produtivo reproduzível na Hostinger](items/MP-038-hostinger-production.md) | SRE | M | MP-017, MP-037 |
| [MP-039 — Restaurar controle e dados privados dentro das metas](items/MP-039-backup-restore.md) | SRE/QA | M | MP-038 |
| [MP-040 — Ensaiar rollout, rollback e resposta operacional](items/MP-040-release-operations.md) | SRE/Security | M | MP-038, MP-039 |
| [MP-041 — Operar um cliente piloto com aceite e capacidade medida](items/MP-041-commercial-pilot.md) | PM/PO/TM | M | MP-011, MP-027, MP-032, MP-040 |
| [MP-042 — Publicar release 1.0 e entregar operação documentada](items/MP-042-release-one.md) | PO/SRE | S | MP-041 |
