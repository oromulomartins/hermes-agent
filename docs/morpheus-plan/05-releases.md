# Releases orientadas a valor

As releases são sequenciais por capacidade, com trabalho independente permitido pelas dependências do backlog. Não há datas prometidas antes de saber capacidade, budget e tempo de resposta humano. Os tamanhos são estimativas iniciais de complexidade; rever após o piloto. Uma release termina com demonstração, evidências, release notes e tag `morpheus-vX.Y.Z`.

| Release | Versão | Valor de negócio demonstrável | Demonstração de saída |
|---|---|---|---|
| R0 — Demanda compreendida | 0.1.0 | Transformar uma demanda sintética em proposta e backlog rastreáveis | Habilitar módulo → intake → spec/tickets → exportação Jira; desligar preserva Hermes |
| R1 — Projetos protegidos | 0.2.0 | Operar dois clientes sem compartilhar contexto ou credenciais | A e B executam intake em ambientes distintos; ataques cruzados negados |
| R2 — Primeira entrega web | 0.3.0 | Entregar uma jornada web/API pequena com supervisão e evidência | Ticket → branch → código/testes → PR → aceite → staging |
| R3 — Evolução de legado | 0.4.0 | Corrigir ou ampliar software existente com risco controlado | Onboarding read-only → caracterização → mudança → regressão → entrega |
| R4 — Entrega mobile | 0.5.0 | Atender Android, iOS e Flutter com evidência nativa | Mesmo fluxo de ticket, com build e testes por plataforma em CI adequada |
| R5 — Aprendizado reutilizável | 0.6.0 | Reduzir esforço com soluções genéricas sem revelar clientes | Candidato privado → sanitização → aprovação → uso em fixture diferente |
| R6 — Continuidade operacional | 0.7.0 | Avançar backlog por agendamento e incorporar melhorias do Hermes | Retomada após falha, limites de custo, sync upstream validado e rollback |
| R7 — Serviço na Hostinger | 1.0.0 | Operação comercial assistida, recuperável e acompanhável | Piloto autorizado na VPS, monitoramento, restore ensaiado e aceite operacional |

R0 é uma entrega interna de validação de demanda, não uma empresa pronta. R1 é pré-requisito para inserir dados reais. R2 já implanta staging na Hostinger; R7 conclui operação de produção. R2 introduz execução limitada retomável; R6 amplia a resiliência e rotina agendada. Não adiamos todo valor até a última release.

## Gates por release

| Release | Entrada | Saída obrigatória | Reversão |
|---|---|---|---|
| R0 | Repo/visibilidade e fluxo inicial definidos | Contrato de plugin aprovado; spec/tickets sintéticos revisados; CI de módulo ativado/desativado | Desabilitar módulo; voltar imagem/commit |
| R1 | R0 e topologia de isolamento escolhida | Credenciais escopadas; suíte cruzada; homes/VMs separados; sem conteúdo privado no controle | Suspender tenants, revogar grants e preservar auditoria |
| R2 | R1 e stack demonstradora definida | Jornada aprovada, PR/checks no SHA atual, staging e recibo; smoke de reinício | Reverter release do app, checkpoint de tarefa, sem reescrever histórico |
| R3 | R2 e repo de teste legado | Inventário, teste de caracterização, mudança aceita; migração compatível | Rollback testado ou forward fix documentado |
| R4 | R2/R3, runners e contas móveis | Evidências Android, iOS e Flutter; credenciais de assinatura separadas | Reverter candidato; distribuição interna; loja fora do gate padrão |
| R5 | R1/R3 e política de reuso | Catálogo sanitizado, teste com canaries, provenance privada, revogação | Remover versão e invalidar consumidores |
| R6 | R2/R5 e budgets reais definidos | Idempotência sob falha; budget; tarefas agendadas; upstream candidato validado | Pausar scheduler e restaurar combinação fixada |
| R7 | Releases anteriores; acesso Hostinger e contrato piloto | Restore, observabilidade, SLOs aceitos, runbooks, autorização operacional | Rollback de artefato; restore somente sob runbook e necessidade |

R4 pode desenvolver cada plataforma em branches independentes depois de sua entrada; o gate da release exige as três capacidades solicitadas. Se o primeiro cliente precisar somente de web, R4 pode ser reordenada mediante decisão de produto registrada, mantendo o compromisso de cobertura mobile no roadmap.

## Planejamento de capacidade

Cada história visa uma fatia que caiba em uma sessão fresca; tarefas grandes devem ser novamente divididas ao refinamento. O backlog usa S/M/L e um teto inicial de 45 minutos por execução, não estimativa de horas de entrega. Uma história pode exigir várias execuções e espera humana. Itens L precisam de refinamento adicional antes de `Ready`.

Planejar inicialmente um writer por repo e até dois workers por projeto, incluindo review, sujeito à memória disponível. O kanban limita WIP; PM/TM não inicia trabalho novo se revisão ou decisão bloqueia a capacidade. Release não coincide necessariamente com sprint: sprints organizam cadência, versões organizam valor entregue.

## Saída visível ao usuário em toda entrega significativa

Ticket com benefício → branch com nome legível → commits focados → push confirmado → PR com problema/comportamento/testes → checks e review → publicação no ambiente do contrato → comentário Jira com links e resumo. No final da release, lista de benefícios, mudanças incompatíveis, limitações e rollback. Ver [padrão Git](07-git-upstream.md).
