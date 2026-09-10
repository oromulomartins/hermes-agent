# Processo de engenharia baseado em Matt Pocock

## Leitura do repositório atual

Snapshot: `3cca18b368ae95cdbdebbff572ccafa662551015`. As skills são disciplinas pequenas e combináveis, não um motor de workflow pronto. O Morpheus precisa implementar estado, permissões e persistência ao redor delas. A seleção abaixo corresponde aos caminhos atuais; não pressupõe que nomes históricos como `write-a-prd`, `prd-to-plan` ou `prd-to-issues` ainda existam.

O [README](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/README.md) diferencia skills invocadas pelo usuário e pelo modelo. O frontmatter `disable-model-invocation: true` aparece em várias orquestradoras. Copiar seus arquivos não transforma o processo em operação autônoma.

## Fluxo adotado

| Etapa | Base pesquisada | Dono | Artefato e saída |
|---|---|---|---|
| Configurar projeto | `setup-matt-pocock-skills` | TL/operador | Tracker, labels, glossário e ADRs locais |
| Esclarecer demanda | `grill-with-docs`, `grilling`, `domain-modeling` | PM + PO | Problema, usuários, restrições, decisões pendentes |
| Navegar incerteza grande | `wayfinder` | TM + TL | Mapa de decisões e fronteira desbloqueada |
| Reduzir risco técnico | `research`, `prototype` | TL/especialista | Evidência com fonte ou protótipo descartável |
| Especificar | `to-spec` | PO + TL | Problema, solução, histórias, decisões e seams de teste |
| Fatiar | `to-tickets` | PO + TL | Entregas verticais demonstráveis e dependências |
| Executar | `implement`, `tdd`, `codebase-design` | Engenheiro | Comportamento testado, diff pequeno e evidência |
| Diagnosticar defeito | `diagnosing-bugs` | Engenheiro | Reprodução, hipótese, correção e regressão |
| Revisar | `code-review` | Revisores de spec e padrões | Dois pareceres independentes sobre o mesmo diff |
| Evoluir desenho | `improve-codebase-architecture` | TL | Candidatos priorizados, sem refactor automático indiscriminado |
| Retomar | `handoff` adaptada | Papel que encerra execução | Checkpoint durável com referências e próximo passo |

## O que essas skills realmente fazem

**Wayfinder:** planeja um esforço maior que uma sessão como mapa de decisões. Um ticket resolve uma pergunta, não necessariamente entrega software. A fronteira são decisões cujos blockers já terminaram. O que ainda não pode ser formulado fica registrado como incerteza; não se inventa precisão. Aplicação: visibilidade do fork, estratégia de workers, seleção de stack de um cliente e restrições de implantação. Não usar o mapa de decisões como substituto do backlog de entregas.

**Grill-with-docs/domain-modeling:** esclarecer termos enquanto se discute o produto, manter `CONTEXT.md` e ADRs. Aplicação: “cliente”, “projeto”, “aprovação”, “concluído” e “publicado” precisam ter significado estável entre papéis. Glossário de cliente fica no projeto privado.

**To-spec:** sintetiza conversa e código já conhecidos, com histórias e decisões de teste. Apesar de se descrever como síntese sem entrevista, contém confirmação de seams. No Morpheus isso vira um gate rastreável de especificação; informação ausente produz decisão pendente.

**To-tickets:** fatias verticais completas, cada uma demonstrável e pequena o suficiente para uma sessão. Dependências são explícitas. Para refactor amplo admite expandir → migrar em lotes → remover forma antiga, mantendo compatibilidade. Aplicação: “gerar PR com aceite e testes” é entrega; “criar tabelas” isoladamente não é release de negócio. O backlog deste plano aplica essa lógica e identifica trabalho habilitador quando inevitável.

**TDD:** o corpo atual da skill enfatiza um teste de comportamento por vez, no limite público previamente combinado, seguido da implementação mínima. Refactor é deslocado à revisão no texto atual, embora existam referências mais gerais a red/green/refactor no README. Seguimos o conteúdo fixado da skill, com testes de contrato e comportamento; mudanças simples de documentação não exigem teste artificial.

**Code-review:** separa conformidade com padrões da conformidade com spec, usando contextos de revisão independentes. O commit base é fixado; achados devem apontar consequência verificável. Isso reduz contaminação entre pareceres, mas não prova ausência de bugs. O gate efetivo usa CI e aprovação com identidade, não somente a fala do revisor.

**Handoff:** a original salva em temporário do sistema. Para agendamento isso não basta: nossa adaptação guarda checkpoint e referências duráveis no armazenamento privado do projeto. O documento portátil contém IDs, hashes, decisões e próximos passos; não uma cópia integral da conversa.

## Adaptação para Jira

`setup-matt-pocock-skills` permite tracker “Other” descrito em texto; não contém um adapter operacional completo de Jira. Criar contrato em `docs/agents/issue-tracker.md` dentro de cada repo privado: instância, projeto permitido, campos, consultas, operações de mapa de decisões, relações `blocks` e protocolo de idempotência.

O Morpheus executa essas operações com credenciais controladas. Substituir exigências GitHub Issues de agentes reaproveitados por Jira; não duplicar gestão em dois trackers. Preservar GitHub para PR, checks, releases e referências de commits. `ready-for-agent` é label de triagem; **não substitui** state/gates de execução.

## Adaptação para execução sem humano presente

Não remover silenciosamente os gates dos originais nem depender de invocar `/implement` ou `/to-spec` pelo nome em um cron. Criar versões Morpheus namespaced, com origem e diff registradas, que recebem entradas já aprovadas e produzem um resultado tipado:

- `completed`: a etapa local está comprovada; não significa entrega publicada.
- `needs_input`: falta decisão que afeta escopo, custo, permissões ou interface de teste.
- `blocked`: falta externa, conflito ou gate que não pode resolver nesta execução.
- `retryable`: falha transitória dentro da política de tentativas.
- `no_work`: não há item elegível.

Durante uma execução agendada, o agente usa decisões já registradas; uma dúvida nova é salva com alternativas, recomendação, impacto e dono. A execução libera sua lease e outra tarefa **independente e autorizada** pode avançar. Não há “aprovação por silêncio”. Mudanças em requisitos invalidam os descendentes afetados.

## Passagem entre papéis e gates

```text
Intake → Discovery → Spec Review → Ready → In Progress → Review → Awaiting Approval
                                                       ↑         ↓
                                                       └ Changes Requested
Awaiting Approval → Ready to Release → Done
Qualquer etapa não terminal → Needs Input / Blocked
```

Definition of Ready: objetivo e benefício; tenant/projeto verificados; spec revision; aceite observável; seams de teste; ambiente e comandos conhecidos; blockers concluídos; orçamento; nível de autonomia; papel e revisores; critérios de conclusão.

Definition of Done de uma história de software: aceite satisfeito, CI obrigatório válido no SHA atual, revisões requeridas, PR merged quando fizer parte do contrato, artefato publicado no ambiente previsto e Jira reconciliado. Para uma entrega apenas documental, o contrato pode ser artefato revisado e commit publicado. O estado `done` do kanban local não é mapeado cegamente para `Done` no Jira.

## Exemplos de interação

**Projeto novo:** PM esclarece “reduzir trabalho manual de atendimento”; PO define cenário e aceite; TL decide stack e contrato; FullStack entrega caminho mínimo utilizável; QA testa cenários aprovados; PO verifica benefício; humano libera produção conforme política.

**Sistema existente:** engenheiro faz inventário read-only e identifica comandos; QA fixa testes de caracterização; TL delimita dependências; PO seleciona mudança de valor; engenheiro corrige mantendo contrato; revisão exige regressões e estratégia de migração. Falta de cobertura vira risco explícito, não justificativa para reescrever tudo.

## Curadoria, licença e precedência

As fontes pesquisadas exibem MIT nos arquivos de licença. Ao incorporar conteúdo, preservar licença/atribuição e fixar SHA+digest. Não instalar tudo com atualização automática. Processo Morpheus e regras explícitas do cliente prevalecem sobre estilos e ferramentas específicas do candidato; toda adaptação fica registrada. As skills remotas foram analisadas como material de pesquisa neste plano, não instaladas nem executadas como procedimentos nesta sessão.
