# Matriz de permissões

O sistema usa contas individuais. O acesso é definido pela combinação de
`role`, `employment_type` e `unit_group`; a interface nunca é a única barreira,
pois todas as regras também são validadas pela API.

| Perfil | Consulta de leitos | Registro de eventos | Gerenciamento de usuários |
|---|---|---|---|
| Diarista / plantonista | Todas as unidades | Somente a própria unidade | Não |
| Coordenador de unidade | Todas as unidades | Somente a própria unidade | Somente contas da própria unidade |
| Coordenação geral | Todas as unidades | Todas as unidades | Todas as contas, exceto administradores |
| Administrador | Todas as unidades | Todas as unidades | Todas as contas e perfis |

## Proteções

- Coordenadores de unidade não conseguem transferir contas para outra unidade.
- Apenas administradores criam ou alteram contas administrativas.
- A conta administrativa não pode ser desativada, rebaixada ou excluída.
- Nenhum usuário pode desativar, excluir ou alterar o escopo da própria conta.
- Alterar senha ou desativar uma conta encerra suas sessões abertas.
- A exclusão de uma conta preserva o histórico assistencial já registrado.

## Perfis centrais

`coordenador_geral` e `administrador` usam `role=coordenador` e
`unit_group=COORDENACAO`. Os demais vínculos usam `role=unidade` e uma unidade
existente.
