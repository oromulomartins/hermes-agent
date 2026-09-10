# Visão e contrato de produto

## Resultado esperado

Uma operação de software em que o responsável humano consegue registrar uma necessidade, obter proposta e critérios de aceite, acompanhar execução por especialistas, revisar evidências e receber software utilizável. Deve atender projetos novos e evolução de sistemas existentes de diferentes clientes. O mesmo mecanismo governa a construção da própria plataforma Morpheus, em um tenant interno sem acesso aos clientes.

O produto inicial é uma operação via CLI, Jira e GitHub. Um portal próprio não é pré-requisito para entregar valor. PM, PO, TM e TL são responsabilidades diferentes, mesmo quando o piloto usar um modelo ou um operador para mais de um papel. Especialistas são instanciados conforme a demanda, sem manter dezenas de agentes consumindo tokens em reuniões artificiais.

## Requisitos invariantes do usuário

- Partir do Hermes e continuar incorporando melhorias upstream.
- Customização agregadora e opcional; desligada, não deve alterar o funcionamento normal do Hermes.
- Processo de engenharia fundamentado no repositório de Matt Pocock.
- Aproveitar agentes/skills do awesome-copilot mediante curadoria.
- PM, PO, TM, TL, Backend, Frontend, FullStack, Android, iOS e Flutter.
- Planejamento em releases com resultados de negócio e branches por entrega significativa.
- Jira para backlog e acompanhamento, com commits e pushes descritivos.
- Execuções retomáveis por Codex ou Claude agendados.
- Implantação da plataforma em VPS Hostinger.
- Nenhum agente de um cliente deve conhecer escopo, dados ou projeto de outro cliente.
- Reuso somente de conhecimento genérico autorizado e higienizado.

## Premissas propostas, ainda não confirmadas

| Tema | Base de planejamento | Efeito de uma resposta diferente |
|---|---|---|
| Nome | Morpheus | Apenas namespaces/documentação |
| Conta GitHub | `oromulomartins`, identificada pelo conector | Provisionar na organização indicada |
| TM | Technical Manager | Redefinir responsabilidade se for outro cargo |
| Aprovação | Agentes abrem branches/commits/pushes/PRs; humano aprova merge e produção | Ajustar política por classe de risco |
| Piloto | Um projeto sintético, depois dois clientes sintéticos, antes de dados reais | Antecipar controles se houver projeto contratado |
| Modelos | APIs externas; modelos escolhidos por avaliação e orçamento | Replanejar hardware se houver inferência local |
| Infraestrutura | Hostinger para controle; workers de clientes em VMs separadas | Uma única VPS serve apenas ao piloto sintético até aceite de risco |
| Jira | Cloud, projeto gerenciado pela empresa | Adaptar API/importador para Data Center ou team-managed |
| Stack demonstradora | Python para módulo Hermes; app exemplo pequeno web/API | Especializações respeitam a stack real de cada cliente |

## Dois planos de trabalho que não se misturam

**Construção da plataforma:** repo do fork/módulo, Jira da plataforma, tenant interno `platform`. Aqui entram agentes, isolamento, scheduler, integração Jira e infraestrutura genérica.

**Entrega aos clientes:** um ou mais repositórios privados e projetos Jira autorizados por cliente/projeto, além de ambientes e credenciais próprios. Briefs, contratos, decisões, dados de teste reais e incidentes ficam nesses espaços. Um bug de plataforma descoberto em cliente vira reprodução sintética no backlog da plataforma.

## Indicadores propostos

Medir baseline no piloto e recalibrar após 10 entregas; estes números são metas de engenharia, não desempenho já observado.

- 100% das entregas com ticket → branch → commits → PR → evidências → release rastreáveis.
- Zero acesso cruzado bem-sucedido na suíte adversarial obrigatória; isso não equivale a prova absoluta de segurança.
- Pelo menos 8 de 10 tarefas pequenas aprovadas sem correção humana de código; rejeição corretamente fundamentada conta como evidência, não como entrega.
- Reinício não duplica PR, commit publicado, deploy ou transição de negócio.
- Custo por entrega aprovada, retrabalho, tempo até primeiro PR, tempo aguardando humano e idade dos bloqueios visíveis.
- Capacidade e metas de disponibilidade definidas após ensaio; metas iniciais de recuperação constam no runbook.

## Fora do primeiro ciclo

Venda automática, contratos com clientes assinados por agentes, faturamento fiscal, RH, compras autônomas, Kubernetes obrigatório, treinamento com dados dos clientes e publicação automática em lojas móveis. Essas capacidades precisam de escopo próprio. A plataforma constrói software que pode conter agentes AI e também software convencional; o fluxo prevê avaliações específicas quando o produto entregue contém LLMs.
