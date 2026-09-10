# MP-001 — Publicar o plano numa branch descendente do Hermes

**Release:** R0 / 0.1.0 · **Epic local:** MP-E0
**Status:** draft · **Tipo:** Task · **Papel:** Operador/TL
**Tamanho:** S · **Risco:** medium · **Prioridade:** High

## Valor e entrega

Ter um ponto de partida rastreável e atualizável sem histórico desconectado.

## Dependências

- Tickets: Nenhuma.
- Decisões: D01, D03.
- Gate de entrada da release correspondente; dependência não é hierarquia Parent.

## Critérios de aceite

- [ ] Fork ou derivado criado na conta/visibilidade decididas, preservando ancestral Hermes e remote upstream de leitura.
- [ ] Plano importado sem sobrescrever README/AGENTS upstream, em branch própria com commit e SHA remoto confirmado.
- [ ] PR descreve escopo e validação do plano; nenhum dado privado ou segredo incluído.

## Contrato de execução

- Interface de teste: Histórico Git e PR de documentação.
- Comandos concretos: definir no refinamento conforme o repo e registrar antes de Ready.
- Tempo máximo por execução: 45 minutos; budget monetário pendente (sem execução autônoma enquanto indefinido).
- Ready: Refinar, resolver decisões, fixar comandos e budget, registrar política e liberar explicitamente para Ready.
- Fora do escopo: Outros clientes, outras histórias e ampliação automática de permissões ou budget.

## Branch e fechamento

Branch proposta: `docs/MP-001-bootstrap-fork`.
Após importação, usar chave Jira real nas novas branches e preservar o mapeamento do ID local.

Commit sugerido: `docs(company): MP-001 publicar o plano numa branch descendente do Hermes`.

Aceite comprovado; commit/push confirmados; PR/review/checks e publicação conforme contrato; Jira reconciliado. Ver 02-processo.md e 07-git-upstream.md.

## Evidências exigidas

- Critérios de aceite vinculados a demonstração ou teste.
- Base/head SHA e revisão da spec.
- Commit remoto e PR quando parte do contrato.
- Recibo de execução e atualização do tracker.

## Refinamento e retomada

Ao liberar, registrar spec revision, comandos, budget, policy e dono. Na execução, registrar run ID, SHA, PR, checks, checkpoint e próxima ação. Não marcar concluído apenas porque um commit local existe.
