# First Budget 2027 — configuração inicial

## 1. Arquivo principal
Use `first_budget_2027.py` como aplicação Streamlit separada do First Intelligence.

## 2. Mesmos usuários do First Intelligence
O app usa o mesmo bloco `[usuarios]` dos Secrets do Streamlit. Assim, quando os usuários forem mantidos nos Secrets, os dois apps podem usar a mesma configuração de perfis, senhas e linhas de negócio.

Os perfis esperados são:
- `DIRETORIA`: consulta consolidada;
- `CONTROLADORIA` / `ADMIN`: acesso e edição de todas as linhas;
- `GESTOR`: edição somente da linha vinculada ao usuário.

## 3. Persistência do Forecast
Sem configuração adicional, o app grava em `budget_data/` localmente. Esse modo serve para desenvolvimento/testes e não deve ser considerado persistência definitiva em hospedagens que reiniciam o filesystem.

Para usar GitHub como persistência inicial, adicione nos Secrets do app:

```toml
[budget_storage]
mode = "github"
repo = "SEU_USUARIO/SEU_REPOSITORIO"
branch = "main"
token = "SEU_TOKEN_GITHUB"
folder = "budget_data"
```

O token não deve ser gravado no código ou no repositório.

## 4. Arquivos de dados criados pelo app
- `budget_data/forecast_comercial_2027.csv`
- `budget_data/historico_forecast_2027.csv`

## 5. Fase 1 implementada
- Forecast Comercial 2027;
- permissões por perfil/linha;
- forecast bruto e ponderado;
- probabilidade Alta/Média/Baixa;
- inclusão, alteração e exclusão lógica;
- histórico de alterações;
- consolidação mensal e anual;
- exportação Excel;
- bloqueio básico de sobrescrita silenciosa quando um lançamento foi alterado por outro usuário.

## 6. Próximas fases previstas
Orçamento de Receita, Premissas 2027, Orçamento de Despesas, Investimentos, versões/aprovação do Budget oficial e integração de Budget/Forecast com o First Intelligence.
