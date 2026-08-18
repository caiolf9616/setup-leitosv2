# Integração entre Setup de Leitos e Kanbam

## 1. Objetivo

Este documento apresenta uma proposta para integrar o **Setup de Leitos** ao
**Kanbam**, permitindo que os dois sistemas compartilhem informações sem
acessar diretamente o banco de dados um do outro.

O Setup de Leitos continuará sendo a fonte oficial da situação operacional de
cada leito. O Kanbam poderá controlar tarefas, pendências, responsáveis, prazos e
motivos que impedem o avanço do leito para a próxima etapa.

Um dos principais casos de uso é identificar por que um leito permanece muito
tempo em **Alta/Transferência** ou **Desocupado**.

## 2. Responsabilidade de cada sistema

### Setup de Leitos

- manter o cadastro institucional de unidades, enfermarias e leitos;
- registrar o status oficial do leito;
- controlar bloqueios;
- preservar o histórico das movimentações;
- calcular tempos e indicadores assistenciais;
- exibir o painel operacional e o painel de chamadas.

### Kanbam

- cadastrar pendências relacionadas à liberação do leito;
- criar e distribuir tarefas;
- identificar o setor e o profissional responsável;
- controlar prioridade, prazo e previsão de conclusão;
- registrar observações operacionais;
- informar quando uma pendência for iniciada, atualizada ou concluída.

Os bancos de dados não devem ser compartilhados. A comunicação deve ocorrer
por APIs autenticadas e, preferencialmente, por eventos enviados por webhook.

## 3. Fluxo operacional sugerido

```text
Ocupado
   |
   v
Alta/Transferência
   |
   +-- Sem pendência ---------> Desocupado
   |
   +-- Com pendência
          |
          v
       Kanbam cria tarefa
          |
          +-- aguardando transporte
          +-- aguardando documentação
          +-- aguardando familiar
          +-- aguardando retirada de equipamento
          +-- outra pendência operacional
          |
          v
       Pendência concluída
          |
          v
Desocupado
   |
   v
Kanbam acompanha higienização ou manutenção
   |
   v
Apto
   |
   v
Ocupado
```

Inicialmente, a conclusão de uma tarefa no Kanbam deve apenas informar ao Setup
que a pendência foi resolvida. A confirmação da mudança do status do leito
deve continuar sendo realizada por um profissional autorizado. Uma automação
completa poderá ser avaliada futuramente.

## 4. Formas de comunicação

### 4.1. Consulta periódica

O Kanbam consulta a API do Setup em intervalos regulares para identificar
alterações. É simples de implementar, mas pode gerar consultas desnecessárias
e atrasos na atualização.

### 4.2. Webhook

Esta é a opção recomendada para a primeira integração. Quando um leito muda
de status ou de bloqueio, o Setup envia um evento ao Kanbam. A informação chega
rapidamente e os sistemas permanecem independentes.

### 4.3. Fila de mensagens

Uma fila como RabbitMQ ou Redis Streams pode ser adotada quando houver vários
sistemas consumidores ou grande volume de integrações. Essa abordagem oferece
maior resiliência, mas exige infraestrutura e operação adicionais.

Para a etapa inicial, recomenda-se usar webhook com tentativas automáticas de
reenvio e uma consulta periódica apenas como mecanismo de reconciliação.

## 5. Eventos enviados pelo Setup

Eventos sugeridos:

- `bed.status_changed`: mudança do status do leito;
- `bed.blocked`: leito bloqueado;
- `bed.unblocked`: leito desbloqueado;
- `bed.status_overdue`: tempo no status ultrapassou o limite configurado.

Exemplo de evento:

```json
{
  "event_id": "setup-1834",
  "event": "bed.status_changed",
  "occurred_at": "2026-08-06T17:30:00Z",
  "bed": {
    "id": 45,
    "unit_group": "A",
    "ward": "403",
    "number": "11"
  },
  "previous_status": "ocupado",
  "current_status": "alta"
}
```

O campo `event_id` deve ser único. O Kanbam deve armazená-lo para que o mesmo
evento, caso seja reenviado, não crie tarefas duplicadas.

## 6. Informações devolvidas pelo Kanbam

O Kanbam poderá disponibilizar ou enviar ao Setup:

- identificador da tarefa;
- tipo e motivo da pendência;
- situação da tarefa;
- prioridade;
- setor responsável;
- nome operacional do responsável, quando necessário;
- data e hora de criação;
- prazo e previsão de conclusão;
- data e hora da conclusão;
- observação curta;
- link para abertura da tarefa no Kanbam.

Situações sugeridas para uma pendência:

```text
aberta -> atribuida -> em_andamento -> concluida
                             |
                             +-> cancelada
```

## 7. Tipos de pendência sugeridos

- transporte interno;
- ambulância ou transferência externa;
- documentação de alta;
- liberação médica;
- familiar ou acompanhante;
- retirada de medicamentos ou materiais;
- retirada de equipamentos;
- higienização;
- manutenção predial;
- manutenção de equipamento;
- isolamento;
- falta de material para preparação;
- divergência administrativa;
- outro motivo operacional.

Os motivos devem ser preferencialmente padronizados. Um campo de observação
livre pode complementar o motivo sem substituir a classificação.

## 8. Apresentação no Setup de Leitos

Quando houver integração, o Setup poderá mostrar no leito:

```text
Leito 12 - Alta há 1h35
Pendência: aguardando transporte
Setor responsável: Transporte
Prioridade: alta
Previsão: 20 minutos
```

Sugestão de classificação visual configurável:

- até 30 minutos: situação normal;
- de 30 a 60 minutos: atenção;
- acima de 60 minutos: situação crítica.

Esses limites devem ser definidos e ajustados pela gestão conforme o fluxo
real do hospital. Não devem ficar permanentemente fixos no código.

Possíveis elementos na interface:

- cronômetro do status atual;
- cor de criticidade;
- ícone indicando pendência aberta;
- motivo resumido;
- setor responsável;
- previsão de solução;
- botão **Abrir no Kanbam**;
- aviso quando o prazo for ultrapassado.

## 9. Indicadores conjuntos

A integração pode produzir indicadores como:

- quantidade de leitos em alta;
- quantidade de leitos com pendência;
- leitos acima do prazo esperado;
- tempo médio entre `Alta` e `Desocupado`;
- tempo médio entre `Desocupado` e `Apto`;
- pendências mais frequentes;
- tempo médio por tipo de pendência;
- setores com maior volume de solicitações;
- percentual de tarefas concluídas dentro do prazo;
- leitos parados por mais tempo;
- tempo total economizado após a implantação da integração.

Os indicadores devem ser interpretados como apoio à melhoria do processo, e
não isoladamente como avaliação individual de profissionais.

## 10. Segurança e privacidade

- utilizar HTTPS ou restringir a comunicação à rede interna autorizada;
- criar uma credencial técnica exclusiva para cada integração;
- utilizar token ou chave de API com rotação periódica;
- nunca incluir segredos no código-fonte ou nos eventos;
- validar a assinatura dos webhooks;
- limitar os endereços de origem autorizados;
- registrar acessos, envios, respostas e falhas;
- enviar somente os dados estritamente necessários;
- evitar nome, prontuário, diagnóstico ou outros dados do paciente;
- definir prazo de retenção para logs e informações de integração.

Para os fluxos propostos, unidade, enfermaria, leito, status, horário,
pendência e setor responsável normalmente são suficientes.

## 11. Confiabilidade e tratamento de falhas

- o sistema emissor deve registrar o evento antes de tentar enviá-lo;
- falhas temporárias devem gerar novas tentativas com intervalos crescentes;
- o receptor deve processar cada `event_id` uma única vez;
- deve existir uma tela ou relatório de integrações pendentes e com erro;
- uma indisponibilidade do Kanbam não pode impedir o registro do leito;
- uma indisponibilidade do Setup não deve apagar tarefas do Kanbam;
- os sistemas devem realizar reconciliação periódica;
- eventos com falha permanente devem ficar disponíveis para reprocessamento;
- os relógios dos servidores devem estar sincronizados.

## 12. Prevenção de ciclos

Deve ficar definido qual sistema é responsável por cada informação. Por
exemplo, o Setup é responsável pelo status do leito e o Kanbam é responsável
pela situação da tarefa.

Quando o Kanbam informar que uma tarefa foi concluída, o Setup não deve enviar
de volta um evento que recrie a mesma tarefa. Identificadores de correlação e
origem devem acompanhar as mensagens para prevenir esse ciclo.

## 13. Implantação por etapas

### Etapa 1 - Consulta

- disponibilizar uma API de consulta dos leitos;
- permitir que o Kanbam associe tarefas a um identificador de leito;
- exibir no Setup a existência de uma pendência, sem automação de status.

### Etapa 2 - Eventos

- enviar mudanças de status por webhook;
- criar tarefas automáticas para `Alta`, `Desocupado` e `Bloqueado`;
- implementar reenvio e proteção contra duplicidade.

### Etapa 3 - Retorno do Kanbam

- receber atualizações das tarefas;
- mostrar responsável, prazo, previsão e conclusão no Setup;
- notificar a coordenação quando o prazo for ultrapassado.

### Etapa 4 - Indicadores e automação

- criar indicadores conjuntos;
- revisar limites de tempo com base nos dados reais;
- avaliar, com aprovação da gestão, quais mudanças podem ser automáticas.

## 14. Decisões necessárias antes do desenvolvimento

- qual problema e quais tarefas o Kanbam controlará inicialmente;
- qual sistema criará cada tipo de informação;
- quais status e eventos serão compartilhados;
- quais são os limites de tempo esperados;
- quais setores receberão as tarefas;
- quem pode concluir ou cancelar uma pendência;
- se a conclusão apenas notifica ou também altera o status do leito;
- quais dados podem ser enviados conforme as regras institucionais;
- endereços, autenticação e disponibilidade das APIs;
- procedimento de contingência quando um sistema estiver indisponível.

## 15. Recomendação inicial

Começar com um piloto pequeno:

1. o Setup envia eventos de `Alta`, `Desocupado`, `Apto` e `Bloqueado`;
2. o Kanbam cria ou movimenta tarefas automaticamente;
3. o Kanbam devolve `aberta`, `em andamento`, `concluída` ou `com pendência`;
4. o Setup mostra o motivo, o responsável e o tempo da pendência;
5. o profissional continua confirmando manualmente o status oficial do leito;
6. após o piloto, os tempos e resultados são avaliados antes de ampliar a
   automação.

Essa abordagem entrega valor rapidamente, preserva a autonomia dos sistemas e
reduz o risco de inconsistência operacional.

## 16. Situação atual da pré-implementação

O Setup já possui uma tela inicial em `/pendencias`, acessível pelo item
**Pendências** do sidebar. Ela substituiu o item **Indicadores** no menu, pois
os indicadores históricos continuam disponíveis nos relatórios.

A tela utiliza somente informações reais que já pertencem ao Setup:

- unidade e leito;
- status atual;
- data e hora do último evento;
- tempo transcorrido no status;
- indicação de tempo acima do limite inicial;
- filtros por unidade, status e criticidade.

Os campos `Pendência`, `Setor`, `Prioridade`, `Previsão` e o botão
**Ver no Kanbam** já possuem espaço reservado. Até que o contrato da API seja
implementado, eles aparecem como **Aguardando integração** e não permitem
ações.

Essa pré-implementação tem dois objetivos:

1. permitir que as equipes avaliem previamente a organização visual;
2. conectar os dados do Kanbam futuramente sem redesenhar toda a tela.

Nenhum dado fictício do Kanbam é exibido e nenhuma comunicação externa está
ativa nesta etapa.
