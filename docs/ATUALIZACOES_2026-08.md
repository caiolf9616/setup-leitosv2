# Atualizações do Setup de Leitos — Agosto de 2026

## Objetivo

Este documento registra as principais alterações funcionais, visuais e
operacionais realizadas no Setup de Leitos em agosto de 2026.

## 1. Catálogo de leitos

- A unidade **Estabilização** foi retirada do catálogo oficial.
- O sincronizador foi corrigido para remover enfermarias antigas que ficaram
  sem leitos.
- Enfermarias antigas vazias deixaram de aparecer nos seletores de unidade.
- O processo de sincronização preserva registros com histórico quando isso for
  necessário para auditoria.

## 2. Permissões de usuários

- A visualização e o gerenciamento de contas ficaram restritos ao perfil
  **Administrador**.
- Coordenação Geral e Coordenação de Unidade não visualizam mais o item
  **Usuários** no sidebar.
- A restrição também é aplicada pela API, não apenas pela interface.
- Foi corrigido o estilo do sidebar para impedir que o `display: flex`
  reexibisse links marcados como ocultos.
- A Coordenação Geral continua autorizada a consultar todas as unidades e
  alterar o status dos leitos.

## 3. Fluxo obrigatório dos status

As movimentações passaram a seguir o fluxo:

```text
Ocupado -> Alta/Transferência -> Desocupado -> Apto -> Ocupado
```

- A interface permite selecionar somente a próxima etapa válida.
- As demais opções permanecem visíveis com efeito fosco e desabilitadas.
- Uma mensagem informa qual é a próxima etapa obrigatória.
- A API também impede saltos de status.
- A validação considera inserções retroativas para não criar uma sequência
  cronológica inválida.
- Leitos sem histórico continuam permitindo a definição do status inicial.

## 4. Bloqueio de leitos

O bloqueio passou a ser permitido quando o leito estiver:

- sem status;
- Apto;
- Desocupado.

Leitos em `Ocupado` ou `Alta/Transferência` não podem ser bloqueados. Um leito
bloqueado continua sem aceitar novas movimentações até ser desbloqueado.

## 5. Relatórios

- Leitos bloqueados passaram a aparecer nos relatórios.
- Foi incluído o filtro **Bloqueado**.
- Leitos bloqueados sem status também podem ser apresentados.
- As contagens e os tempos acumulados foram revisados por testes automatizados.
- O relatório limita o período ao tempo efetivamente transcorrido, sem
  projetar o status até o final de um dia futuro.
- O PDF passou a apresentar:
  - logo do Hospital de Messejana no canto superior esquerdo;
  - logo do Governo do Estado do Ceará no canto superior direito.

## 6. Dashboard

- As últimas atualizações passaram a mostrar **Unidade e Leito**.
- A enfermaria foi retirada dessa apresentação resumida.
- A API de eventos recentes passou a devolver também o grupo da unidade.

## 7. Painel de chamadas

A lateral do painel foi dividida em duas colunas:

### Leitos disponíveis

- apresenta somente leitos em `Apto`.

### Alta e desocupados

- apresenta somente leitos em `Alta/Transferência` ou `Desocupado`.

As colunas funcionam de maneira independente.

### Rotação circular

A antiga rolagem vertical de ida e volta foi substituída por uma rotação
circular em blocos:

- a coluna mostra a quantidade de cartões que cabe na área disponível;
- o grupo permanece parado por cinco segundos para facilitar a leitura;
- uma transição suave apresenta o próximo grupo;
- depois do último grupo, a exibição retorna ao primeiro;
- quando todos os cartões couberem, não ocorre animação desnecessária;
- cada coluna possui sua própria rotação.

O painel continua recebendo as mudanças do Setup em tempo real por WebSocket.

## 8. Nova tela de Pendências

O item **Indicadores** foi substituído por **Pendências** no sidebar.

- Nova rota: `/pendencias`.
- A rota antiga `/indicadores` foi mantida temporariamente para
  compatibilidade, mas não aparece mais no menu.
- A nova tela utiliza dados reais do Setup para apresentar:
  - unidade e leito;
  - status atual;
  - tempo no status;
  - criticidade conforme o tempo;
  - filtros por unidade, status e criticidade.

### Limites iniciais de visualização

- Alta/Transferência: alerta depois de 60 minutos.
- Desocupado: alerta depois de 60 minutos.
- Apto: alerta depois de 360 minutos.

Esses limites são iniciais e deverão ser revisados com a gestão conforme o
fluxo real do hospital.

### Campos reservados ao Kanbam

A tela já permite visualizar onde aparecerão:

- resumo da pendência;
- setor responsável;
- prioridade;
- previsão de resolução;
- botão **Ver no Kanbam**.

Enquanto a API não estiver conectada, os campos aparecem explicitamente como
**Aguardando integração** e o botão permanece desabilitado. Nenhuma pendência
fictícia é criada.

## 9. Integração planejada com o Kanbam

Foi documentada a proposta de integração em
`docs/INTEGRACAO_SETUP_LEITOS_KANBAM.md`.

Diretrizes definidas:

- o Setup permanece como fonte oficial do status do leito;
- o Kanbam permanece responsável pelas tarefas e pendências;
- os sistemas devem conversar por API e webhook;
- um sistema não deve acessar diretamente o banco do outro;
- o Setup mostrará apenas um resumo operacional da pendência;
- detalhes, comentários e execução da tarefa permanecem no Kanbam;
- uma falha no Kanbam não pode impedir a movimentação dos leitos nem a
  atualização do painel.

## 10. Investigação da migração do sistema antigo

Foi criada e validada uma cópia consistente do banco SQLite do sistema antigo.
A análise identificou:

- 4 usuários;
- 100 enfermarias;
- 347 leitos;
- 2.740 eventos;
- histórico entre novembro de 2025 e agosto de 2026;
- relacionamentos íntegros no banco antigo.

Também foi identificado que:

- 12 leitos pertencem à antiga Estabilização;
- 28 leitos pertencem a uma estrutura antiga/duplicada da Unidade B;
- os eventos das enfermarias antigas `201` a `203` podem ser consolidados nos
  leitos correspondentes `B-201` a `B-203`;
- os períodos analisados permitem a consolidação sem sobreposição relevante.

A migração ainda não foi executada. Antes disso, deverá ser criado um
importador com modo de simulação (`dry-run`), relatório de conferência e uma
janela de transição para produzir o backup final do sistema antigo.

## 11. Validação e publicação

- As alterações foram acompanhadas por testes automatizados de API, regras de
  permissão, relatórios e contratos do frontend.
- A versão que introduziu a tela de Pendências foi validada com **82 testes
  aprovados**.
- A nova rota respondeu corretamente com HTTP 200 no ambiente local.
- Os pacotes de produção foram gerados com SHA-256 e publicados somente após
  backup, conferência de hash, reconstrução da imagem e verificação de saúde.

## 12. Próximas etapas

1. Validar visualmente a tela de Pendências com os profissionais.
2. Confirmar os limites de tempo para cada status.
3. Definir o contrato JSON entre Setup e Kanbam.
4. Definir URLs, tokens e regras de autenticação.
5. Implementar envio de eventos do Setup ao Kanbam.
6. Implementar recebimento do resumo das pendências.
7. Implementar reenvio, idempotência e monitoramento da integração.
8. Criar e testar o importador do banco antigo em modo de simulação.
9. Planejar a migração definitiva sem perda de movimentações.
