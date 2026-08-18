# Sistema de Controle de Leitos e login dos usuários das unidades

## 1. Objetivo do sistema

O **Sistema de Controle de Leitos** apoia o acompanhamento dos leitos hospitalares e permite registrar, consultar e divulgar mudanças de situação em tempo real.

Suas principais funções são:

- consultar unidades, enfermarias, leitos e a situação atual de cada leito;
- registrar eventos de **Alta**, **Desocupado**, **Apto** e **Ocupado**;
- mostrar movimentações recentes e indicadores;
- emitir relatórios com o tempo dos leitos em cada situação;
- atualizar o painel público de chamada em tempo real;
- controlar o acesso por usuário, unidade e perfil profissional;
- manter o histórico e identificar qual usuário registrou cada movimentação.

O painel público de chamada pode ser aberto sem autenticação. As telas internas e as operações sobre leitos exigem login.

## 2. Organização das unidades e dos leitos

Cada leito pertence a uma enfermaria, e cada enfermaria pertence a um grupo de unidade. O catálogo atual contém os grupos **UCC, Risco, UTI-Semi Intensiva, Estabilização e Unidades A, B, C, D, G, H, I e J**.

O sistema utiliza um identificador técnico único para cada enfermaria. Assim, enfermarias com o mesmo número em unidades diferentes não são confundidas. Nas telas, o profissional visualiza o nome habitual da enfermaria.

## 3. Login dos usuários das unidades

### 3.1 Conta individual

O acesso é feito por uma **conta pessoal e individual**. Cada profissional deve utilizar seu próprio login e sua própria senha; a conta não deve ser compartilhada entre pessoas da mesma unidade.

Cada conta contém:

- nome completo do profissional;
- login único;
- senha protegida;
- unidade à qual o profissional está vinculado;
- tipo de vínculo ou função;
- situação da conta: ativa ou inativa.

Esse modelo permite identificar no histórico tanto a unidade quanto o login responsável por uma movimentação de leito.

### 3.2 Como entrar

1. Acesse a página `/login` do endereço disponibilizado pelo hospital.
2. Informe o **login pessoal**.
3. Informe a senha.
4. Selecione **Entrar**.
5. Após a autenticação, o sistema direcionará o usuário ao dashboard.

O login não diferencia letras maiúsculas de minúsculas: o sistema normaliza o nome de usuário antes da validação. A senha continua sendo validada exatamente como foi cadastrada.

Se o login, a senha ou a situação da conta forem inválidos, o acesso será recusado com uma mensagem genérica. Essa mensagem não informa se foi o usuário ou a senha que estava incorreto, reduzindo a exposição de informações sobre as contas existentes.

### 3.3 Bloqueio por tentativas malsucedidas

O sistema limita tentativas repetidas de login. Depois do número máximo configurado de erros para a combinação de endereço de origem e login, novas tentativas ficam temporariamente bloqueadas.

Na configuração padrão documentada no projeto, são permitidas até **5 tentativas em uma janela de 5 minutos**. Esses valores podem ser alterados pelo responsável técnico. Quando houver bloqueio, o usuário deverá aguardar o período informado e tentar novamente.

### 3.4 Sessão de acesso

Após um login válido, o servidor cria uma sessão e envia ao navegador um cookie de autenticação. Esse cookie:

- é inacessível ao JavaScript da página (`HttpOnly`);
- é enviado apenas ao próprio sistema (`SameSite=Lax`);
- deve ser transmitido somente por HTTPS em produção (`Secure`);
- possui prazo de validade configurável, documentado por padrão como 30 dias;
- pode ser revogado no servidor antes do vencimento.

O sistema não utiliza JWT. A sessão permanece registrada no banco de dados, facilitando seu encerramento quando necessário.

Em cada página protegida, o sistema consulta `/api/auth/me` para confirmar se a sessão ainda é válida. Se não existir sessão, se ela estiver vencida ou se a conta estiver inativa, o usuário será direcionado de volta ao login.

### 3.5 Saída do sistema

Ao selecionar a opção de sair, o sistema:

1. exclui a sessão no servidor;
2. remove o cookie do navegador;
3. limpa os dados temporários da interface;
4. retorna à página de login.

O usuário deve sempre sair do sistema ao terminar o trabalho, principalmente em computadores compartilhados.

## 4. Perfis e permissões

As permissões resultam da combinação entre o perfil técnico, o tipo de vínculo e a unidade da conta.

| Tipo de usuário | Consulta de leitos | Registro de eventos | Gestão de usuários |
|---|---|---|---|
| Diarista | Todas as unidades | Somente na própria unidade | Não possui acesso |
| Plantonista | Todas as unidades | Somente na própria unidade | Não possui acesso |
| Coordenador de unidade | Todas as unidades | Somente na própria unidade | Contas da própria unidade |
| Coordenação geral | Todas as unidades | Todas as unidades | Todas, exceto contas administrativas |
| Administrador | Todas as unidades | Todas as unidades | Todas as contas e perfis |

Todos os usuários autenticados podem consultar o panorama completo de unidades, enfermarias e leitos. A restrição por unidade é aplicada no momento de registrar uma mudança: um usuário comum ou coordenador de unidade só pode alterar leitos vinculados à sua própria unidade.

Essas regras são verificadas pela API, e não apenas pelos botões mostrados na tela. Portanto, uma tentativa de enviar diretamente uma movimentação para um leito de outra unidade também será recusada.

## 5. Cadastro e manutenção de usuários

### 5.1 Quem pode cadastrar

- O **coordenador de unidade** cadastra e administra apenas usuários da sua unidade.
- A **coordenação geral** administra contas de todas as unidades, mas não contas administrativas.
- O **administrador** administra todas as contas e todos os perfis.

Os usuários diaristas e plantonistas não possuem acesso à gestão de contas.

### 5.2 Regras do cadastro

- O login deve ser único e ter pelo menos 3 caracteres.
- O nome completo é obrigatório.
- A senha deve ter pelo menos 8 caracteres, incluindo ao menos uma letra e um número.
- Diaristas, plantonistas e coordenadores de unidade devem estar vinculados a uma unidade existente.
- Coordenação geral e administrador ficam vinculados ao grupo técnico `COORDENACAO`.
- Um coordenador de unidade não pode cadastrar alguém em outra unidade nem conceder perfil central.
- Somente o administrador pode criar ou alterar uma conta administrativa.

### 5.3 Alteração, desativação e exclusão

Um gestor autorizado pode alterar o nome, a unidade, o vínculo, o perfil, a situação e a senha de uma conta, respeitando seu próprio escopo de permissão.

Existem proteções adicionais:

- ninguém pode desativar ou excluir a própria conta;
- ninguém pode alterar o perfil, a unidade ou o vínculo da própria conta;
- a conta administrativa não pode ser desativada, rebaixada ou excluída;
- ao trocar a senha ou desativar uma conta, todas as sessões abertas desse usuário são encerradas;
- ao excluir uma conta, suas sessões são encerradas, mas o histórico de movimentações já registrado é preservado.

Para afastamentos temporários, recomenda-se **desativar** a conta. A exclusão deve ser reservada para situações em que a conta realmente não será mais utilizada.

## 6. Registro e auditoria das movimentações

Ao registrar uma mudança de leito, o sistema grava:

- leito afetado;
- nova situação;
- data e hora da ocorrência;
- unidade do usuário autenticado;
- login do usuário que realizou a operação;
- data de criação do registro.

Leitos bloqueados não aceitam novas movimentações. Depois de um evento válido, o painel público recebe o estado atualizado em tempo real.

## 7. Situações comuns e orientação ao usuário

### “Login ou senha inválidos”

Verifique se o login pessoal foi digitado corretamente e se as teclas Caps Lock e Num Lock estão na posição esperada. Se o problema persistir, solicite ao coordenador da unidade ou ao administrador a redefinição da senha e a confirmação de que a conta está ativa.

### “Muitas tentativas de login”

Aguarde o período de bloqueio antes de tentar novamente. Repetir tentativas durante esse intervalo não libera o acesso.

### O sistema voltou para a página de login

A sessão pode ter vencido, sido encerrada por uma troca de senha, por desativação da conta ou pelo logout em outra ação administrativa. Entre novamente; se o acesso continuar indisponível, procure o responsável pela conta.

### O usuário visualiza outra unidade, mas não consegue alterar seus leitos

Esse é o comportamento esperado. A consulta é global, enquanto o registro de eventos dos usuários de unidade fica limitado à unidade cadastrada em sua conta.

### O usuário não encontra a tela de gestão de contas

A funcionalidade aparece apenas para coordenador de unidade, coordenação geral e administrador. A API também bloqueia o acesso dos demais perfis.

## 8. Boas práticas de segurança

- Não compartilhar login ou senha.
- Não anotar senhas em locais visíveis.
- Utilizar senhas diferentes das usadas em outros serviços.
- Conferir o nome e a função exibidos no sistema antes de registrar movimentações.
- Sair do sistema ao deixar uma estação compartilhada.
- Comunicar imediatamente mudança de setor, desligamento ou suspeita de uso indevido.
- Manter o sistema em produção exclusivamente com HTTPS e configuração segura de cookies.
- Nunca enviar senhas por mensagens abertas ou registrá-las em documentos operacionais.

## 9. Resumo do fluxo de autenticação

```text
Usuário informa login e senha
             |
             v
Servidor valida conta ativa e senha
             |
       +-----+-----+
       |           |
    inválido      válido
       |           |
       v           v
acesso recusado  sessão criada no banco
                   |
                   v
             cookie seguro enviado
                   |
                   v
        páginas confirmam a sessão
                   |
             +-----+-----+
             |           |
          inválida      válida
             |           |
             v           v
        volta ao login  acesso conforme perfil e unidade
```

## 10. Responsabilidades recomendadas

- **Usuário da unidade:** proteger suas credenciais, conferir a conta utilizada e registrar apenas movimentações reais.
- **Coordenador da unidade:** cadastrar os profissionais da própria unidade, manter os vínculos atualizados, redefinir senhas e desativar acessos quando necessário.
- **Coordenação geral:** administrar os acessos assistenciais entre unidades e acompanhar o uso global do sistema.
- **Administrador:** manter contas centrais, configurações técnicas, segurança, banco de dados, HTTPS, backups e disponibilidade da aplicação.

---

Este documento descreve o comportamento implementado no **Setup de Leitos v2** em julho de 2026. Configurações operacionais, como duração da sessão e limite de tentativas, podem ser ajustadas pelo administrador técnico.
