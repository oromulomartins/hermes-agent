# Organização, agentes e reaproveitamento

## Papéis, decisões e limites

| Papel | Responsabilidade | Entrega verificável | Não decide sozinho |
|---|---|---|---|
| Responsável humano | Direção, orçamento e aceite reservado | Decisão identificada, com objeto e prazo | Não é substituído por persona AI |
| PM — Product Manager | Problema, descoberta, resultados e prioridade estratégica | Brief, hipótese de valor, métricas | Contratos, gastos ou escopo comercial novo |
| PO — Product Owner | Backlog, fatias, aceite e prioridade operacional | Spec, tickets, aceitação de comportamento | Ignorar falha de segurança/CI |
| TM — Technical Manager | Capacidade, dependências, custo e impedimentos | Alocação, previsão por evidência, gestão de bloqueios | Alterar políticas globais ou acessar outros clientes |
| TL — Tech Lead | Arquitetura, interfaces e coerência técnica | ADR, seams de teste, parecer técnico | Aprovar sozinho código que implementou |
| Backend | APIs, domínio, persistência, integração | API demonstrável e contratos testados | Criar segredo ou recurso produtivo sem grant |
| Frontend | Fluxos web, acessibilidade, desempenho | Fluxo de usuário testado em browser | Declarar aceite visual sem evidência |
| FullStack | Fatia estreita que cruza UI/API/dados | Jornada completa testada | Assumir qualquer stack sem qualificação |
| Android | Kotlin/Java, app e integrações nativas | Build/testes e cenário Android | Publicar na loja ou assinar com chave global |
| iOS | Swift/SwiftUI, app e integrações nativas | Build/testes em macOS e cenário iOS | Alegar compilação iOS numa VPS Linux |
| Flutter | Dart, fluxo multiplataforma | Testes Dart/widget e build de cada alvo | Tratar sucesso Android como prova iOS |
| QA | Validação independente e regressão | Cenários, falhas reproduzíveis e evidências | Corrigir código e autoaprovar a própria correção |
| Security | Revisão de acesso, dados, supply chain e agentes | Achados, severidade, reprodução e gate | Aceitar risco em nome do cliente |
| DevOps/SRE | CI, ambientes, releases e recuperação | Deploy reproduzível, restore e runbook | Produção fora da política aprovada |
| UX/UI, sob demanda | Fluxos e comportamento visual | Critérios visuais e acessibilidade | Acrescentar escopo de produto |

PM, PO, TM e TL são templates com escopo por projeto. Um piloto pode sequenciar papéis no mesmo pool de modelos, preservando artefatos e separação de revisão. Não será necessário um processo residente por cargo. O roteador usa competência, disponibilidade e budget; o título da persona não comprova competência.

## Matriz de candidatos do awesome-copilot

Snapshot `7568a482ce2df38f8965ab5336a3220db796a4ba`. Caminhos abaixo foram encontrados na cópia pesquisada. Links imutáveis por arquivo e SHA256 ficam no [catálogo estruturado](research/catalog.json).

| Papel/capacidade | Arquivo candidato | Reuso e adaptação necessária |
|---|---|---|
| PM | `agents/se-product-manager-advisor.agent.md` | Perguntas de valor e métricas; trocar obrigação de GitHub Issues por Jira e remover modelo fixo |
| PO | PM acima + `skills/ai-team-orchestration/SKILL.md` | Criar perfil próprio; delimitar aceite/backlog, sem assumir equivalência pronta |
| TM | `agents/ai-team-producer.agent.md` | Coordenação e impedimentos; remover autoridade automática de merge, acrescentar capacidade/orçamento |
| TL | `agents/se-system-architecture-reviewer.agent.md` | Revisão de arquitetura; adaptar perguntas ao contrato já aprovado |
| Backend | `agents/api-architect.agent.md` | Contratos e resiliência; remover gatilho textual “generate” e camadas obrigatórias genéricas; complementar pela stack |
| Backend .NET | `agents/CSharpExpert.agent.md` | Perfil condicional ao repo .NET, avaliar e fixar versão de stack |
| Backend Kotlin/Spring | `skills/kotlin-springboot/SKILL.md` | Conhecimento de servidor; não é especialista Android |
| Frontend React | `agents/expert-react-frontend-engineer.agent.md` | Adaptar versões à aplicação e mapear ferramentas VS Code para runtime |
| FullStack | `agents/ai-team-dev.agent.md` + catálogo da stack | Compor competência de Backend/Frontend; testar fatia integral |
| FullStack .NET | `agents/dotnet-fullstack-mentor.agent.md` | Extrair engenharia; remover foco em mentoria de carreira |
| Android | Perfil Morpheus novo | Não foi encontrado agente Android completo nos candidatos examinados; usar documentação oficial e eval próprio |
| iOS | Perfil Morpheus novo | `swift-mcp-expert` ensina MCP em Swift, não substitui engenheiro de app iOS |
| Flutter | `instructions/dart-n-flutter.instructions.md` | Adaptar instruções `applyTo` para skill/perfil e alinhar testes às seams acordadas |
| QA mobile | `agents/gem-mobile-tester.agent.md` | Cenários e evidência de device; mapear ferramentas e output para nosso contrato |
| QA geral | `agents/qa-subagent.agent.md` e `agents/ai-team-qa.agent.md` | Independência e casos de borda; retirar permissões de alteração do produto durante review |
| Security | `agents/se-security-reviewer.agent.md`, `skills/security-review/SKILL.md` | Curar verificações por risco; complementar com controles executáveis |
| DevOps | `agents/devops-expert.agent.md`, `agents/se-gitops-ci-specialist.agent.md` | CI/CD e operação; adaptar para Hostinger e brokers por projeto |
| UX | `agents/se-ux-ui-designer.agent.md` | Critérios de experiência quando houver UI |
| Brownfield | `skills/acquire-codebase-knowledge/SKILL.md` | Inventário com evidência, lacunas e perguntas explícitas |
| Modernização | `agents/modernization.agent.md` | Somente ideias selecionadas; exigência de ler todos os arquivos é inadequada a grandes repos/limite de execução |
| Teste web | `skills/webapp-testing/SKILL.md` | Playwright; dependências instaladas em imagem fixada, sem instalação automática surpresa |
| ADRs | `skills/create-architectural-decision-record/SKILL.md` | Compatibilizar com formato `domain-modeling` de Matt |

**Não importar a orquestração inteira do awesome-copilot.** `ai-team-orchestration` usa um time leve Producer/Dev/QA e oferece ideias úteis, mas a fundação do processo será Matt Pocock + state machine Morpheus. Evitar dois orquestradores com regras concorrentes.

## Conversão e qualificação

Um `.agent.md` de Copilot não é automaticamente um agente Hermes. Frontmatter de modelo, permissões, aliases de ferramenta, MCPs e handoffs precisa de tradução explícita. Um arquivo `instructions/*.instructions.md` também não vira uma skill apenas por mudar a extensão.

Pipeline proposto: selecionar arquivo → ler referências transitivas e scripts → registrar licença, SHA e digest → extrair disciplina → adapter declarativo de papel → lista mínima de ferramentas reais → teste de contrato de saída → avaliação em tarefa sintética → revisão → versão aprovada do catálogo.

Não executar instaladores do material pesquisado no host de produção. Scripts de skills rodam como código de terceiros no sandbox do projeto. Versões de frameworks citadas nos prompts devem seguir o lockfile do cliente; não migrar React, .NET ou Flutter incidentalmente.

Cada papel recebe: objetivo, ações permitidas, entradas obrigatórias, outputs, limites de custo/turnos, política de dúvidas e evidência. `model` é configuração avaliada, sem manter `GPT-5` ou qualquer versão fixa copiada do frontmatter por conveniência.

## Matriz resumida de responsabilidade

| Decisão | Responsável por preparar | Autoridade final proposta | Consultados |
|---|---|---|---|
| Problema e valor | PM | Humano/cliente | PO |
| Aceite e prioridade | PO | PO dentro do escopo delegado | PM, TL |
| Arquitetura | TL | TL dentro das restrições aprovadas | Engenheiro, Security |
| Alocação/budget | TM | Humano para aumento de teto | TL |
| Código | Engenheiro | Revisor + gates | QA, TL |
| Merge | Publisher | Humano inicialmente | TL, PO, CI |
| Produção | DevOps | Humano inicialmente | PO, Security |
| Compartilhar aprendizado | Curador | Humano autorizado | Security, dono do conhecimento |

Com aprovação de autonomia maior, mudar a política e os grants; não editar personas para contornar gates. QA e Security são acréscimos necessários ao desenho de revisão e confidencialidade, não uma contratação automática de novos serviços.
