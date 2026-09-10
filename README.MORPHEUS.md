# Morpheus — plano de uma empresa de software operada por agentes

Versão do plano: **0.1, proposta para decisão**, pesquisada em **9–10 de setembro de 2026**.

A proposta é estender um fork do Hermes com um módulo opcional, **Morpheus Company**, para conduzir demandas de clientes desde descoberta até entrega e operação. O processo de engenharia deriva das skills de Matt Pocock; agentes e conhecimentos especializados são selecionados do awesome-copilot. A separação entre clientes é imposta por identidade, credenciais e ambientes de execução, além da separação de memória.

**Este diretório contém planejamento, contratos e backlog; a plataforma ainda não foi implementada.** Não foram criados fork, projeto Jira, PR, agendamento ou implantação. O diretório estava vazio e sem Git. Preservamos essa condição para importar estes arquivos em uma branch descendente do Hermes, sem criar um histórico Git desconectado.

## Comece aqui

1. [Visão, escopo e critérios de sucesso](docs/morpheus-plan/00-visao.md).
2. [Releases e demonstrações de valor](docs/morpheus-plan/05-releases.md).
3. [Decisões e perguntas pendentes](docs/morpheus-plan/11-decisoes.md).
4. [Backlog navegável](docs/morpheus-plan/backlog/INDEX.md), com um arquivo por entrega.
5. [Estado atual e validação](docs/morpheus-plan/STATUS.md), para retomar o trabalho em outra execução.

## Projeto técnico e operacional

| Artefato | Finalidade |
|---|---|
| [Arquitetura e extensão do Hermes](docs/morpheus-plan/01-arquitetura.md) | Limites dos módulos, contratos e reaproveitamento nativo |
| [Processo Matt Pocock](docs/morpheus-plan/02-processo.md) | Funcionamento das skills e adaptação para Jira e execução agendada |
| [Isolamento e memória](docs/morpheus-plan/03-isolamento.md) | Separação entre clientes, projetos, processos e conhecimento reutilizável |
| [Papéis e catálogo](docs/morpheus-plan/04-agentes-skills.md) | Responsabilidades, candidatos reais, lacunas e adaptações |
| [Jira](docs/morpheus-plan/06-jira.md) | Hierarquia, campos, workflow, importação e sincronização |
| [Git e upstream](docs/morpheus-plan/07-git-upstream.md) | Fork, branches, commits, PRs e atualização do Hermes |
| [Execução agendada](docs/morpheus-plan/08-execucao-agendada.md) | Codex, Claude, retomada, limites e idempotência |
| [Implantação Hostinger](docs/morpheus-plan/09-operacao-vps.md) | Topologia, capacidade, backup, rollout e recuperação |
| [Qualidade e riscos](docs/morpheus-plan/10-qualidade-riscos.md) | Gates, avaliações de agentes e critérios de aceite |
| [Fontes e evidências](docs/morpheus-plan/12-fontes.md) | Código examinado, documentação primária e limitações |

## Artefatos estruturados

- `backlog/backlog.json`: fonte local do backlog antes da importação; IDs `MP-*` são identificadores locais, **não chaves Jira reais**.
- `backlog/jira-import.csv`: epics e histórias, com descrições, valores, critérios e Parent; requer mapeamento no importador administrativo.
- `backlog/jira-dependencies.csv`: dependências a reconciliar após obtenção das chaves reais.
- `contracts/`: exemplos de configuração, execução e recibo; **contratos propostos**, não APIs prontas.
- `templates/`: prompts e modelos para futuras execuções.
- `research/sources.lock.json` e `research/catalog.json`: commits e arquivos das fontes selecionadas.
- `scripts/validate_plan.py`: valida integridade estrutural do plano sem acesso à rede.

Validar: `python3 docs/morpheus-plan/scripts/validate_plan.py`.

**Próximo passo concreto:** resolver a estrutura/visibilidade do repositório e os limites iniciais de autonomia; então executar as primeiras entregas de R0 em branch própria. As perguntas não impedem a revisão deste plano, mas impedem transformar valores provisórios em configuração de produção.
