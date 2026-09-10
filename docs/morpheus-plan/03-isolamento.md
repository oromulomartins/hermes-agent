# Isolamento de clientes, projetos e memória

## Modelo de ameaça e fronteira

Assumir que código recebido, dependências de build, páginas web, tickets e arquivos de instrução do cliente podem executar ações inesperadas ou conter prompt injection. O agente pode errar e tentar ler outro caminho. A proteção deve sobreviver à troca do prompt ou a um comando de shell arbitrário dentro do worker.

Profiles Hermes separam estado, **não são sandbox**. Clone de profile pode copiar chaves; OAuth pode compartilhar autenticação de raiz. Não usar clone de profile entre clientes nem montar o home pessoal do operador. [Documentação de profiles no snapshot](https://github.com/NousResearch/hermes-agent/blob/8e85b276f1dba5a92f74125127f5dc7841bf24a8/website/docs/user-guide/profiles.md).

**Produção recomendada:** uma VM por cliente; projetos do cliente com identidades, volumes, repositórios e contexto separados. Se o contrato exige que projetos do mesmo cliente também não se conheçam, usar VM por projeto. Containers efêmeros por execução dentro da VM reduzem persistência; compartilhar kernel entre clientes permanece risco residual e não satisfaz a recomendação para código não confiável.

**Uma VPS única:** adequada ao controle e à demonstração com clientes sintéticos. Containers rootless, namespaces e políticas ajudam, mas não tornam o host uma fronteira independente por cliente. R1 precisa de ambientes separados antes de autorizar dados reais. Não há promessa de “isolamento absoluto” em um host compartilhado.

## Matriz de acesso

| Recurso | Worker do projeto A | Worker do projeto B | Controle determinístico | Operador autorizado |
|---|---|---|---|---|
| Código/brief/memória A | Somente recursos concedidos | Negado | Ponteiros/IDs; sem enviar conteúdo a LLM global | Mediante ACL |
| Código/brief/memória B | Negado | Somente recursos concedidos | Ponteiros/IDs | Mediante ACL |
| Catálogo genérico aprovado | Leitura | Leitura | Versiona distribuição | Promove/revoga |
| Segredos de runtime | Referência de curta duração da execução | Referência própria | Broker emite grant | Rotação e auditoria |
| Jira | Projeto e operações allowlisted | Projeto próprio | Integração segmentada | Administração separada |
| PR/checks | Repo e branch autorizados | Repo próprio | Publisher controlado | Merge conforme política |
| Banco do scheduler | Sem acesso direto | Sem acesso direto | Transações | Operação |
| Métricas globais | Sem listagem | Sem listagem | Agregados sem conteúdo | Visão autorizada |

Papéis não possuem credenciais globais. Nem PM nem TM recebe automaticamente visibilidade de clientes distintos. A instância de um papel pertence a `tenant_id + project_id + purpose`, com `agent_instance_id` próprio.

## Controles obrigatórios

1. Binding imutável do tenant/projeto vindo de principal autenticado; ignorar IDs conflitantes sugeridos pelo modelo.
2. Validação de repo, Jira project, branch, artifact prefix e rede no broker antes de cada ação externa. Negação sem revelar existência do recurso de outro cliente.
3. Um home de runtime por processo escritor: Hermes, Codex e Claude com estado próprio, sem montagem do home do host. `HERMES_HOME` é definido no lançamento; políticas equivalentes para estados de Codex/Claude são verificadas no adapter e na imagem fixada.
4. Worktree/clone exclusivo por execução, sem caminho para outros repos. Reuso de worktree somente com identidade e hashes correspondentes. Worktrees do mesmo repo compartilham objetos Git; nunca usados como separação entre clientes.
5. Worker sem root, sem socket Docker/Podman do host, sem dispositivos, sem privilégios, sem mounts globais, limites CPU/RAM/PIDs/disco e saída de rede controlada.
6. Rede entre clientes bloqueada; bloquear metadata services, redes administrativas e acesso ao banco do controle. DNS/egress via política; web/research por proxy não recebe segredos.
7. Credenciais de publicação e deploy ficam fora do processo que roda testes/builds. PR não confiável não roda com token de merge ou segredo de produção. CI por cliente e runner descartável.
8. Caches de dependências privadas, browsers, cookies, emuladores, embeddings, tracing, logs, uploads e backups segmentados. Não compartilhar artefatos de CI entre clientes.
9. Skills, plugins, hooks e MCP de repos recebidos ficam em quarentena. Avaliar configs antes do primeiro lançamento de CLI, pois podem carregar código antes da primeira mensagem.
10. Se identidade, escopo, componente de política ou backend obrigatório falhar, negar execução. Hooks ajudam na UX/auditoria, mas supervisor e broker precisam impor o limite mesmo se plugin falhar.

## Três camadas de conhecimento

**Memória operacional privada:** conversas, decisões, histórico e preferências do projeto. Acesso exclusivo daquele projeto; retenção acordada. Cada processo mantém memória local própria; compartilhamento entre papéis via artefatos aprovados ou serviço privado do projeto, não dois escritores no mesmo Hermes home.

**Conhecimento técnico privado:** soluções, ADRs, runbooks, incidentes, índices e embeddings do cliente. Mesmo classificadas como “técnicas”, podem revelar produto e estratégia. Permanecem privadas por padrão. Embeddings não são anonimização.

**Biblioteca genérica da empresa:** padrões aprovados, templates sem dados reais, exemplos sintéticos e skills revisadas. Catálogo separado e read-only para consumidores; não contém nomes, URLs, tickets, IDs internos ou linhagem visível de clientes.

## Promoção de aprendizado

```text
Aprendizado privado → candidato em quarentena no cliente → reescrita abstrata
→ revisão de confidencialidade e direito de reuso → exemplo sintético
→ testes de utilidade e detecção de vazamento → aprovação → catálogo genérico
```

Não copiar um módulo do cliente só porque o código “parece genérico”. Verificar direito de reutilizar; quando ausente, implementar uma solução independente a partir de requisitos abstratos permitidos. Verificação por LLM não é aprovação suficiente. O vínculo reverso para a origem fica em registro privado acessível somente a quem promove, separado do catálogo distribuído.

Revogação: publicar versão revogada → bloquear novas montagens → invalidar índices/caches → identificar versões consumidoras pelo registro privado → corrigir material já distribuído quando necessário. Offline workers não usam catálogo vencido. O processo não permite que outro cliente descubra a origem da solução.

## Provedores de IA e retenção

Escolher por projeto quais provedores podem receber código/dados, região/retention aplicáveis, limites e mecanismo de autenticação. Essas propriedades ainda precisam ser verificadas para os planos contratados. Não presumir que uma assinatura de chat cobre uso operacional ilimitado nem que todo provider possui as mesmas políticas. Acesso externo é parte do contrato de isolamento, incluindo observabilidade e suporte.

Política provisória a negociar: logs operacionais sem conteúdo por 30 dias; recibos e artefatos pelo prazo do contrato; backups cifrados com expiração; índices derivados excluídos junto da origem. Uma solicitação de exclusão inclui memórias, sessões, embeddings, caches, backups conforme ciclo de retenção e registros externos permitidos. Preservar apenas auditoria mínima autorizada.

## Provas mínimas antes do primeiro cliente real

- A tenta ler arquivo, symlink, sessão, memória, Git remote, DB, bucket e Jira de B: negado e auditado.
- A altera `tenant_id`, board ou caminho em argumentos: principal continua vinculado a A; sem resposta que revele B.
- A tenta rede lateral, socket do host, metadata e segredos do publisher: negado.
- Prompt injetado em README pede upload de outro repo: não há recurso nem credencial para cumprir.
- Retry após lease expirar não publica com grant antigo.
- Catálogo rejeita candidato com canary privada; busca de A não encontra canary de B.
- Reset de runtime não reutiliza home, cache autenticado, browser ou conversa de B.
- Backup/restauração e telemetria preservam ACL e chaves por cliente.

Esses ensaios são obrigatórios em R1 e repetidos quando mudar isolamento, memória, credenciais, plugins, runners ou upstream relacionado.
