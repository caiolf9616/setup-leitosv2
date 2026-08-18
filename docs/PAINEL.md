# Contrato do painel público

O painel deste projeto segue o comportamento homologado no serviço que já roda
na VM do hospital.

| Estado | Lista lateral | Nova chamada | Voz | Cor |
|---|---:|---:|---:|---|
| Apto, Livre ou Available | Sim | Sim | Sim | Verde |
| Desocupado | Sim | Sim | Sim | Azul-petróleo/ciano |
| Alta | Sim | Sim | Sim | Azul |
| Ocupado ou Occupied | Não | Não | Não | — |
| Bloqueado ou `blocked=true` | Não | Não | Não | — |
| Reservado, transferência isolada ou desconhecido | Não | Não | Não | — |

## Regras de atualização

- `bed_id` é a identidade principal. Sem ele, usa-se unidade, enfermaria e
  número do leito.
- Registros duplicados são consolidados antes da exibição.
- A primeira resposta REST cria apenas a linha de base e nunca gera voz.
- Somente entradas novas ou mudanças entre os três estados visíveis entram na
  fila interna de chamadas.
- A lista lateral sempre representa o estado atual, independentemente da fila
  de voz.
- Ocupado, bloqueado ou estado desconhecido remove o leito sem anúncio.
- `blocked=true` prevalece sobre qualquer evento.
- Uma requisição REST em andamento bloqueia outra consulta concorrente.
- Timeout, resposta HTTP inválida ou JSON inválido preserva o último estado
  conhecido.
- O frontend é versionado em `painel.html` para evitar cache antigo na TV.

## Operação na VM

Após atualizar backend ou arquivos estáticos:

```bash
sudo systemctl restart painel-leitos
```

Na TV ou navegador, use `Ctrl + F5`.
