# Implementação - Sistema de Recompensas

## Suas Decisões de Design

### 1. Esquema do Banco de Dados

Foram criados dois modelos separados:

- **CustomerRewards**: armazena o saldo atual de pontos de cada cliente, vinculado ao email. Optei por usar o email como identificador pois é o campo já utilizado no sistema de locações, evitando a necessidade de criar um modelo de Cliente separado e manter retrocompatibilidade.

- **RewardTransaction**: registra cada transação de pontos (ganho ou resgate) com motivo, timestamp e referência à locação. Isso permite auditoria completa do histórico e rastreabilidade de cada movimentação de pontos.

### 2. Arquitetura

A lógica de negócio foi isolada em `rewards_service.py`, separada das views. Isso segue o princípio de separação de responsabilidades e facilita os testes unitários, pois a lógica de cálculo pode ser testada sem depender de requisições HTTP.

- **Maior preocupação**: garantir que os pontos sejam concedidos de forma atômica junto com a devolução do carro, sem quebrar o fluxo existente.
- **Cálculo de pontos**: centralizado na função `calculate_points()`, que aplica as regras de negócio em sequência (base → categoria → duração → pontualidade), retornando o total antes do multiplicador de nível.

### 3. Abordagem de Integração

A integração foi feita adicionando uma única chamada `rewards_service.award_points_for_rental(rental)` na view `return_rental`, após a atualização do banco. Isso garante retrocompatibilidade total — nenhum endpoint existente foi alterado em seu comportamento.

O multiplicador de nível é aplicado automaticamente no momento da concessão dos pontos, baseado no saldo atual do cliente.

**Bug corrigido 1**: a view `create_rental` usava a variável `daily_rate` que não existia no escopo. Corrigido para `car.daily_rate`.

**Bug corrigido 2**: o cálculo de desconto em `create_rental` multiplicava `Decimal` por `float` (`0.1`, `0.05`), causando `TypeError` em tempo de execução. Corrigido para `Decimal('0.1')` e `Decimal('0.05')`. Este bug foi descoberto pelo teste end-to-end.

**Qualidade de código**: os imports foram reorganizados seguindo o padrão PEP8 — stdlib → terceiros → locais — e consolidados em blocos únicos por arquivo, eliminando imports duplicados que existiam na versão inicial.

## Estratégia de Testes

Foram implementados 19 testes organizados em 3 classes:

- **CarAPITestCase**: testa os endpoints existentes de carros (listar, buscar por id, 404).
- **RewardsCalculationTestCase**: testa as regras de cálculo de pontos isoladamente, cobrindo todos os cenários (carro econômico, standard, premium, devolução atrasada, bônus de 7 e 14 dias).
- **RewardsAPITestCase**: testa os endpoints de recompensas (saldo, histórico, resgate com sucesso, resgate com pontos insuficientes, níveis Bronze/Prata/Ouro com multiplicadores corretos, concessão automática de pontos na devolução, e teste end-to-end completo).

O teste end-to-end (`test_fluxo_completo_locacao_devolucao_pontos`) simula o fluxo real: criação de locação via API → devolução via API → verificação dos pontos concedidos e histórico disponível. Este teste foi responsável por identificar o bug do `Decimal*float` descrito acima.

Cada teste inclui comentários explicando o cálculo esperado, facilitando a manutenção futura.

## Como Testar

```bash
# 1. Ativar o ambiente virtual
venv\Scripts\activate.bat

# 2. Rodar as migrações
python manage.py migrate

# 3. Carregar dados de exemplo
Get-Content init_data.py | python manage.py shell

# 4. Rodar os testes automatizados
python manage.py test rentals

# 5. Rodar com detalhes de cada teste
python manage.py test rentals --verbosity=2

# 6. Subir o servidor
python manage.py runserver

# 7. Testar manualmente via browser ou curl:
# GET  http://localhost:8000/api/cars/
# GET  http://localhost:8000/api/rewards/customer/{email}/
# GET  http://localhost:8000/api/rewards/customer/{email}/history/
# POST http://localhost:8000/api/rewards/apply/
```

## Suposições Feitas

1. O email do cliente é suficiente como identificador único, sem necessidade de modelo Cliente separado.
2. O multiplicador de nível é calculado com base no saldo total atual no momento da concessão dos pontos.
3. Devoluções atrasadas não penalizam pontos existentes, apenas não recebem o bônus de pontualidade.
4. O resgate de pontos deve ser em múltiplos de 100, com mínimo de 100 pontos.

## O Que Eu Melhoraria Com Mais Tempo

- Paginação no histórico de transações para clientes com muitas locações.
- Exportação do histórico em CSV.
- Cache do saldo de pontos para evitar queries desnecessárias em consultas frequentes.
- Validação para impedir resgate de pontos em locações já encerradas.
- Proteção contra dupla concessão de pontos na mesma locação.