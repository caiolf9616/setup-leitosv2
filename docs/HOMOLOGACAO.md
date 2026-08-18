# Checklist de homologação

Use um banco descartável e uma configuração própria. Nunca habilite dados de
homologação no ambiente de produção.

## Preparação

1. Configure `ENVIRONMENT=test` e `ALLOW_HOMOLOGATION_DATA=true`.
2. Defina `DATABASE_URL`, `SECRET_KEY`, `SEED_COORDINATOR_PASSWORD` e
   `SEED_ADMIN_PASSWORD`.
3. Execute:

```bash
cd backend
python -m alembic upgrade head
python -m scripts.seed_data
python -m scripts.seed_homologation
python -m scripts.verify_homologation
python -m pytest -q
```

## Aceite funcional

## Roteiro manual recomendado

Execute os testes nesta ordem, usando uma janela normal para o sistema e outra
janela para `/painel`. Anote responsável, data, navegador e resultado de cada
bloco.

### 1. Preparar os quatro perfis

Entre como Administrador e crie contas temporárias identificadas com o prefixo
`HOMO-`:

| Login sugerido | Perfil | Unidade |
|---|---|---|
| `HOMO-USUARIO-A` | Diarista | A |
| `HOMO-COORD-A` | Coordenador de unidade | A |
| `HOMO-GERAL` | Coordenação geral | COORDENAÇÃO |

Use senhas temporárias fortes e diferentes. A conta Administrador já existente
é o quarto perfil. Ao concluir a homologação, desative ou exclua somente essas
contas temporárias.

### 2. Validar permissões

1. Com `HOMO-USUARIO-A`, confirme consulta de todas as unidades e edição apenas
   da Unidade A.
2. Com `HOMO-COORD-A`, tente cadastrar e administrar uma conta da Unidade A;
   confirme que não consegue alterar usuários da Unidade B.
3. Com `HOMO-GERAL`, confirme operação de leitos de qualquer unidade e ausência
   das contas administrativas na tela de usuários.
4. Como Administrador, confirme acesso a todos os perfis sem tentar desativar
   ou excluir a própria conta.

### 3. Validar um leito de teste

Escolha um leito sem uso assistencial na base de homologação e registre, nesta
ordem:

1. `Ocupado`: deve permanecer fora do painel.
2. `Alta`: deve aparecer em azul e ser anunciado.
3. `Desocupado`: deve mudar para ciano/azul-petróleo e ser anunciado.
4. `Apto`: deve mudar para verde com o texto `DISPONÍVEL` e ser anunciado.
5. `Ocupado`: deve sair silenciosamente do painel.

Espere 12 segundos após a última chamada visível e confirme o retorno para
`AGUARDANDO...`. Atualize o painel com `Ctrl + F5`: os cartões atuais devem
reaparecer sem voz.

### 4. Validar data retroativa e relatório

1. Em outro leito, desmarque “Usar data e hora atuais” e registre um evento com
   horário anterior.
2. Gere o relatório incluindo esse horário.
3. Compare o histórico e os tempos do leito com a diferença entre os eventos.
4. Filtre a enfermaria usada e confirme que o total é igual à soma das linhas.
5. Salve o PDF e confira logo, período, filtro, responsável, horário de
   Brasília, tabela e numeração das páginas.

### 5. Validar telas e persistência

1. Compare Dashboard, Indicadores, Leitos e Relatório para o mesmo status.
2. Teste computador, celular e TV sem rolagem horizontal indevida.
3. Saia e entre novamente; confirme que os eventos permanecem.
4. Reinicie somente o serviço no ambiente de homologação e confirme novamente
   os dados e a reconexão do painel.

### Registro de aceite

| Bloco | Responsável | Data/hora | Resultado | Observação |
|---|---|---|---|---|
| Perfis e permissões |  |  | Pendente |  |
| Fluxo de leitos e painel |  |  | Pendente |  |
| Relatório e PDF |  |  | Pendente |  |
| Responsividade |  |  | Pendente |  |
| Reinício e persistência |  |  | Pendente |  |

### Autenticação

- [ ] Login inválido exibe mensagem genérica, sem revelar qual campo falhou.
- [ ] Após cinco falhas, novas tentativas recebem bloqueio temporário.
- [ ] Logout encerra a sessão e impede retorno pelo botão do navegador.
- [ ] Usuário desativado perde o acesso.

### Leitos

- [ ] Usuário visualiza todas as unidades para consulta.
- [ ] Usuário altera apenas leitos da própria unidade.
- [ ] Coordenador consegue operar qualquer unidade.
- [ ] Leito bloqueado não aceita evento.
- [ ] Data e hora retroativas são gravadas corretamente.

### Painel público

- [ ] Leitos em `apto`, `desocupado` e `alta` aparecem com texto e cor corretos.
- [ ] Abrir ou atualizar a página cria a linha de base sem voz.
- [ ] Mudança entre os três estados visíveis atualiza e anuncia sem recarregar.
- [ ] Leito desaparece silenciosamente ao mudar para `ocupado` ou ficar bloqueado.
- [ ] Após 12 segundos da última chamada, o painel retorna para `AGUARDANDO...`.
- [ ] Reconexão após perda de rede recupera o estado atual.

### Dashboard e indicadores

- [ ] Totais por status coincidem com a tela de leitos.
- [ ] Ocupação usa apenas leitos monitorados como denominador.
- [ ] Períodos de 7, 30 e 90 dias carregam sem erro.
- [ ] Desktop, tablet e celular não apresentam rolagem horizontal indevida.

### Relatórios

- [ ] Filtros por período e enfermaria funcionam.
- [ ] Soma por status corresponde ao histórico de uma amostra de leitos.
- [ ] Evento anterior ao início do período define corretamente o status inicial.
- [ ] Impressão/PDF contém período, filtros e todas as linhas esperadas.

### Usuários e permissões

- [ ] Usuário comum não acessa gerenciamento de contas.
- [ ] Coordenador de unidade gerencia apenas a própria unidade.
- [ ] Coordenação geral gerencia todas as unidades, mas não contas administrativas.
- [ ] Administrador consegue cadastrar perfis de unidade, coordenação geral e administração.
- [ ] A conta administrativa não pode ser desativada, rebaixada ou excluída.
- [ ] Usuário não consegue desativar, excluir ou mudar o escopo da própria conta.
- [ ] Senha fraca é recusada.
- [ ] Troca de senha revoga sessões anteriores.

Consulte a definição completa em [PERMISSOES.md](PERMISSOES.md).

## Encerramento

- [ ] Nenhum erro relevante aparece no console do navegador ou log da API.
- [ ] Responsável assistencial aprovou os cálculos e nomes das unidades.
- [ ] Responsável técnico aprovou backup, HTTPS e restauração.
- [ ] `ALLOW_HOMOLOGATION_DATA` está ausente ou `false` fora da homologação.
