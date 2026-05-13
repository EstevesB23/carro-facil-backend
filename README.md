# API de Locação de Carros - Avaliação Técnica (Django REST Framework)

Esta é uma implementação de API de locação de carros usando Django REST Framework para fins de avaliação técnica.

## Início Rápido

### Opção 1: Usando Docker (Recomendado) 🐳

```bash
docker-compose up --build
```

A API estará disponível em `http://localhost:8000/api/`

Veja [DOCKER.md](DOCKER.md) para instruções detalhadas sobre Docker.

### Opção 2: Configuração Local

1. **Instale as dependências:**
```bash
pip install -r requirements.txt
```

2. **Execute as migrações:**
```bash
python manage.py migrate
```

3. **Carregue os dados iniciais (opcional):**
```bash
python manage.py shell < init_data.py
```

4. **Crie um superusuário (opcional, para painel admin):**
```bash
python manage.py createsuperuser
```

5. **Inicie o servidor de desenvolvimento:**
```bash
python manage.py runserver
```

A API estará disponível em `http://localhost:8000/api/`

## Documentação da API

### Endpoints Disponíveis

#### Carros
- `GET /api/` - Mensagem de boas-vindas
- `GET /api/cars/` - Listar todos os carros disponíveis
- `GET /api/cars/{id}/` - Obter detalhes de um carro específico

#### Locações
- `POST /api/rentals/create/` - Criar uma nova locação
- `POST /api/rentals/{id}/return/` - Devolver um carro alugado
- `GET /api/rentals/` - Listar todas as locações
- `GET /api/rentals/customer/{email}/` - Obter locações por email do cliente
- `GET /api/stats/` - Obter estatísticas de locações

#### Sistema de Recompensas
- `GET /api/rewards/customer/{email}/` - Consultar pontos e nível do cliente
- `GET /api/rewards/customer/{email}/history/` - Histórico de transações (suporta paginação via `?page=1&page_size=10`)
- `GET /api/rewards/customer/{email}/export/` - Exportar histórico completo em CSV
- `POST /api/rewards/apply/` - Resgatar pontos para desconto em locação

### Painel Admin

Acesse o painel admin do Django em `http://localhost:8000/admin/`

## Executando Testes

Da raiz do projeto:
```bash
python manage.py test rentals
```

Com detalhes de cada teste:
```bash
python manage.py test rentals --verbosity=2
```

Ou com pytest:
```bash
pytest
```

Com Docker:
```bash
docker-compose exec web python manage.py test rentals
```

## Estrutura do Projeto

```
car_rental/           # Configurações do projeto Django
rentals/              # Aplicação principal
├── models.py         # Modelos Django ORM
├── rewards_service.py # Lógica de negócio do sistema de recompensas
├── database.py       # Camada de acesso a dados
├── views.py          # Views da API DRF
├── serializers.py    # Serializers DRF
├── urls.py           # Roteamento de URLs
├── admin.py          # Configuração do admin Django
└── tests.py          # 19 testes automatizados
manage.py             # Script de gerenciamento Django
requirements.txt      # Dependências Python
Dockerfile            # Definição da imagem Docker
docker-entrypoint.sh  # Script de inicialização do container
```

## Observações

- Usa banco de dados SQLite (arquivo: `db.sqlite3`)
- Não há autenticação/autorização implementada

## Não vacile 😆

Leia o arquivo [de instruções](INSTRUCOES_CANDIDATO.md) para entender o que é esperado do exercício.