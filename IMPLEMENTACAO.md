# Sistema de Recompensas — Documentação de Implementação

## Decisões de Design

### Banco de Dados

Optei por criar dois modelos separados em vez de um só.

O `CustomerRewards` guarda o saldo atual de cada cliente, usando o email como identificador — faz sentido porque o email já era o campo de referência nas locações existentes, então não precisei criar um modelo de Cliente do zero nem quebrar nada que já funcionava.

O `RewardTransaction` registra cada movimentação de pontos individualmente, com motivo, timestamp e referência à locação. Isso dá rastreabilidade total — se um cliente questionar um saldo, dá pra mostrar exatamente quando cada ponto entrou ou saiu e por quê.

### Arquitetura

Toda a lógica de pontos ficou em `rewards_service.py`, separada das views. A razão é simples: se a lógica ficasse dentro da view, eu só conseguiria testá-la fazendo requisições HTTP. Assim, consigo testar `calculate_points()` diretamente com qualquer combinação de dias e tarifas, sem precisar subir um servidor.

O cálculo segue uma sequência clara: pontos base → bônus de categoria → bônus de duração → bônus de pontualidade. O multiplicador de nível é aplicado por cima no momento da concessão, baseado no saldo atual do cliente.

### Integração com o fluxo existente

A integração foi uma linha só: `rewards_service.award_points_for_rental(rental)` chamada dentro de `return_rental`, depois que o banco já foi atualizado. Nenhum endpoint existente foi alterado em comportamento — quem já usava a API não percebe nenhuma diferença.

### Bugs encontrados e corrigidos

Dois bugs existiam no código original:

**Bug 1** — `create_rental` referenciava `daily_rate` diretamente, mas essa variável não existia no escopo da função. Corrigido para `car.daily_rate`.

**Bug 2** — O cálculo de desconto multiplicava um `Decimal` por um `float` (`0.1`, `0.05`), o que o Python não permite e lança `TypeError` em tempo de execução. Corrigido para `Decimal('0.1')` e `Decimal('0.05')`. Esse bug foi encontrado pelo teste end-to-end — o que reforça o valor desse tipo de teste.

---

## Funcionalidades Opcionais

### Paginação no histórico

`GET /api/rewards/customer/{email}/history/?page=1&page_size=10`

A resposta traz `total`, `page`, `page_size` e `total_pages` além das transações, então o frontend consegue montar a navegação sem precisar buscar tudo de uma vez.

### Exportação CSV

`GET /api/rewards/customer/{email}/export/`

Gera um `.csv` com duas seções: um resumo do cliente no topo (saldo atual, nível, pontos acumulados e resgatados) e o histórico completo de transações abaixo, com data, tipo, pontos, motivo e id da locação.

---

## Testes

Foram escritos 19 testes em 3 classes:

**CarAPITestCase** — cobre os endpoints de carros que já existiam: listar, buscar por id e resposta 404 para id inexistente.

**RewardsCalculationTestCase** — testa as regras de cálculo de forma isolada, sem depender de HTTP. Cobre carro econômico, standard e premium, devolução atrasada (sem bônus pontual), e bônus de duração para 7 e 14 dias. Cada teste tem um comentário com a conta esperada, por exemplo:
```
# base: 80, category: 10*8=80, duration 7+: +50, on-time: +25 = 235
```

**RewardsAPITestCase** — testa os endpoints de recompensas: saldo do cliente, histórico, resgate com sucesso, resgate com pontos insuficientes, os três níveis com multiplicadores, concessão automática na devolução, e um teste end-to-end completo.

O teste end-to-end (`test_fluxo_completo_locacao_devolucao_pontos`) cria a locação via API, devolve via API e verifica se os pontos foram concedidos corretamente e aparecem no histórico. Foi esse teste que encontrou o Bug 2 descrito acima.

---

## Como rodar

```bash
# Ativar o ambiente virtual
venv\Scripts\activate.bat

# Aplicar migrações
python manage.py migrate

# Carregar dados de exemplo
Get-Content init_data.py | python manage.py shell

# Rodar os testes
python manage.py test rentals

# Ver detalhes de cada teste
python manage.py test rentals --verbosity=2

# Subir o servidor
python manage.py runserver
```

Endpoints disponíveis para teste manual:
```
GET  /api/cars/
GET  /api/rewards/customer/{email}/
GET  /api/rewards/customer/{email}/history/
GET  /api/rewards/customer/{email}/history/?page=1&page_size=10
GET  /api/rewards/customer/{email}/export/
POST /api/rewards/apply/
```

---

## Suposições

- O email já era o identificador natural nas locações, então foi suficiente para o sistema de recompensas sem precisar de um modelo de Cliente separado.
- O multiplicador de nível é calculado com base no saldo no momento da concessão — quem subir de nível durante uma locação já recebe o multiplicador novo na devolução.
- Devolução atrasada não penaliza pontos existentes, apenas perde o bônus de pontualidade (+25).
- Resgate mínimo de 100 pontos, sempre em múltiplos de 100. Cada 100 pontos = R$50 de desconto.

---

## O que eu melhoraria com mais tempo

- **Cache do saldo de pontos** — para clientes com muitas consultas, evitar bater no banco a cada request.
- **Validação de resgate em locações encerradas** — hoje é possível resgatar pontos referenciando uma locação já devolvida.
- **Proteção contra dupla concessão** — se `award_points_for_rental` for chamado duas vezes para a mesma locação, os pontos são duplicados. Um campo `rewards_processed` no modelo `Rental` resolveria isso.