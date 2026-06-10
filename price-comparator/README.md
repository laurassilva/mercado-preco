# Price Comparator — Plataforma Interna de Comparação de Preços

Plataforma corporativa para comparar preços de produtos em múltiplos mercados, supermercados e atacadistas simultaneamente.

---

## Início Rápido

```bash
# 1. Clone o repositório e entre na pasta
cd price-comparator

# 2. Copie o arquivo de configuração
cp .env.example .env

# 3. Suba todos os serviços
docker-compose up -d

# 4. Acesse a interface
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
```

**Login padrão:** `admin@empresa.com` / `Admin@123`

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│                         NGINX                           │
│              Proxy Reverso (porta 80)                   │
└──────────────┬──────────────────────────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
  ┌─────────┐    ┌──────────┐
  │ Next.js │    │ FastAPI  │
  │Frontend │    │ Backend  │
  │ :3000   │    │  :8000   │
  └─────────┘    └──────┬───┘
                        │
           ┌────────────┼────────────┐
           ▼            ▼            ▼
      ┌──────────┐ ┌─────────┐ ┌────────┐
      │PostgreSQL│ │  Redis  │ │Celery  │
      │  :5432   │ │  :6379  │ │Worker  │
      └──────────┘ └─────────┘ └────────┘
```

### Serviços Docker

| Serviço    | Porta | Função                            |
|------------|-------|-----------------------------------|
| nginx      | 80    | Proxy reverso                     |
| frontend   | 3000  | Interface Next.js                 |
| backend    | 8000  | API FastAPI + Swagger             |
| postgres   | 5432  | Banco de dados PostgreSQL         |
| redis      | 6379  | Cache + fila de mensagens         |
| worker     | —     | Celery worker (scraping em fundo) |
| beat       | —     | Celery Beat (agendamento)         |

---

## Funcionalidades

### Dashboard
- Estatísticas em tempo real (produtos monitorados, mercados ativos, pesquisas do dia)
- Gráfico de preço médio por mercado
- Histórico de pesquisas recentes
- Destaque do mercado mais barato e mais caro

### Pesquisa de Preços
- Busca simultânea em todos os mercados cadastrados
- Resultados ordenados automaticamente do menor para o maior preço
- Destaque visual do menor preço (verde)
- Cálculo da diferença em R$ e % em relação ao mais barato
- Filtro por mercado específico
- Exportação imediata dos resultados (PDF, Excel, CSV)
- Sugestões de produtos populares

### Mercados
- Cadastro e gerenciamento de mercados
- Tipos de integração: Web Scraping, API Oficial, Feed XML, Feed JSON
- Sistema de conectores plugável — adicione novos mercados sem alterar o core
- 6 mercados de demonstração pré-cadastrados

### Histórico
- Registro completo de todas as pesquisas (usuário, data, hora, resultados)
- Filtro por produto ou usuário
- Re-pesquisar com um clique

### Relatórios
- Exportação em PDF (formatado, com logo e tabelas coloridas)
- Exportação em Excel (.xlsx, com formatação de células)
- Exportação em CSV (compatível com qualquer sistema)
- Relatórios rápidos de produtos populares

### Coleta Automática (Celery)
- Atualização automática a cada 6 horas
- Disparo manual de coleta pela interface admin
- Acompanhamento de jobs em tempo real
- Histórico de execuções com status e erros

### Usuários e Permissões
- Perfil **Administrador**: acesso total (CRUD de mercados, usuários, disparo de coleta)
- Perfil **Usuário**: pesquisas, histórico, relatórios
- Autenticação JWT com expiração configurável

---

## Configuração

### Arquivo `.env`

```env
# Banco de dados
POSTGRES_DB=pricecomparator
POSTGRES_USER=priceuser
POSTGRES_PASSWORD=senha_segura

# Segurança (gere uma chave forte)
SECRET_KEY=chave-secreta-minimo-32-caracteres

# Usuário admin inicial
FIRST_ADMIN_EMAIL=admin@suaempresa.com
FIRST_ADMIN_PASSWORD=SenhaForte@123
FIRST_ADMIN_NAME=Administrador

# Token JWT (minutos)
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

### Variáveis de Ambiente — Backend

| Variável                   | Padrão              | Descrição                    |
|----------------------------|---------------------|------------------------------|
| DATABASE_URL               | postgresql+asyncpg://... | URL do banco (async)    |
| SYNC_DATABASE_URL          | postgresql+psycopg2://...| URL do banco (sync/Alembic)|
| REDIS_URL                  | redis://redis:6379/0 | URL do Redis               |
| SECRET_KEY                 | obrigatório         | Chave JWT                    |
| ACCESS_TOKEN_EXPIRE_MINUTES| 1440                | Expiração do token (minutos) |
| PLAYWRIGHT_HEADLESS        | true                | Modo headless do browser     |
| SCRAPING_TIMEOUT           | 30                  | Timeout de scraping (s)      |

---

## Adicionar Novos Mercados

### Opção 1: Via Interface (scraper Mock)
1. Acesse **Mercados → Novo Mercado**
2. Preencha nome, URL e tipo
3. Selecione conector `mock` para usar dados de demonstração

### Opção 2: Scraper Real com Playwright
Crie um arquivo em `backend/app/scrapers/meu_mercado_scraper.py`:

```python
from app.scrapers.playwright_scraper import PlaywrightScraper, ProductResult
from app.scrapers.connector_manager import ConnectorManager
from decimal import Decimal

class MeuMercadoScraper(PlaywrightScraper):
    async def search(self, query: str) -> list[ProductResult]:
        await self._launch()
        await self._page.goto(f"https://meu-mercado.com.br/busca?q={query}")
        await self._page.wait_for_selector(".produto", timeout=15000)
        cards = await self._page.query_selector_all(".produto")
        results = []
        for card in cards:
            name = await card.inner_text(".nome")
            price_raw = await card.inner_text(".preco")
            price = Decimal(price_raw.replace("R$", "").replace(",", ".").strip())
            results.append(ProductResult(
                market_name=self.market_name,
                product_name=name,
                price=price,
                product_url=await card.get_attribute("href"),
            ))
        await self.close()
        return results

# Registra o conector
ConnectorManager.register("meu_mercado", MeuMercadoScraper)
```

Importe no final de `connector_manager.py` e selecione `meu_mercado` no cadastro do mercado.

### Opção 3: API ou Feed (JSON/XML)
Estenda `BaseScraper` diretamente usando `httpx` ou `aiohttp` para consumir a API/feed do fornecedor.

---

## Comandos Úteis

```bash
# Ver logs
docker-compose logs -f backend
docker-compose logs -f worker

# Reiniciar backend
docker-compose restart backend

# Rodar migrations manualmente
docker-compose exec backend alembic upgrade head

# Acessar banco de dados
docker-compose exec postgres psql -U priceuser -d pricecomparator

# Parar tudo
docker-compose down

# Parar e apagar volumes (CUIDADO: apaga dados!)
docker-compose down -v
```

---

## API — Principais Endpoints

| Método | Endpoint               | Descrição                    | Acesso  |
|--------|------------------------|------------------------------|---------|
| POST   | /auth/login            | Login                        | Público |
| GET    | /auth/me               | Usuário atual                | Auth    |
| GET    | /dashboard/            | Estatísticas dashboard       | Auth    |
| GET    | /products/search?q=... | Pesquisar preços             | Auth    |
| GET    | /markets/              | Listar mercados              | Auth    |
| POST   | /markets/              | Criar mercado                | Admin   |
| PATCH  | /markets/{id}          | Editar mercado               | Admin   |
| DELETE | /markets/{id}          | Excluir mercado              | Admin   |
| GET    | /history/              | Histórico de pesquisas       | Auth    |
| POST   | /scraping/trigger      | Disparar coleta              | Admin   |
| GET    | /scraping/jobs         | Listar jobs de coleta        | Auth    |
| GET    | /reports/pdf?q=...     | Exportar PDF                 | Auth    |
| GET    | /reports/excel?q=...   | Exportar Excel               | Auth    |
| GET    | /reports/csv?q=...     | Exportar CSV                 | Auth    |
| GET    | /users/                | Listar usuários              | Admin   |
| POST   | /users/                | Criar usuário                | Admin   |

Documentação completa: **http://localhost:8000/docs**

---

## Backup do Banco de Dados

```bash
# Exportar
docker-compose exec postgres pg_dump -U priceuser pricecomparator > backup_$(date +%Y%m%d).sql

# Restaurar
docker-compose exec -T postgres psql -U priceuser pricecomparator < backup.sql
```

---

## Estrutura do Projeto

```
price-comparator/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Endpoints REST
│   │   ├── core/            # Config, DB, segurança
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Lógica de negócio
│   │   ├── scrapers/        # Conectores de mercado
│   │   ├── normalizer/      # Normalização de produtos
│   │   ├── workers/         # Celery tasks
│   │   └── seeds.py         # Dados iniciais
│   ├── alembic/             # Migrations do banco
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/             # Pages (Next.js App Router)
│   │   ├── components/      # Componentes React
│   │   ├── hooks/           # Custom hooks
│   │   ├── services/        # API client
│   │   └── types/           # TypeScript types
│   └── Dockerfile
├── nginx/nginx.conf
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Tecnologias

| Camada       | Tecnologia                              |
|--------------|-----------------------------------------|
| Backend      | Python 3.11, FastAPI, SQLAlchemy 2.0    |
| Frontend     | Next.js 14, TypeScript, Tailwind CSS    |
| Banco        | PostgreSQL 16                           |
| Cache/Fila   | Redis 7                                 |
| Task Queue   | Celery 5 + Celery Beat                  |
| Scraping     | Playwright (plugável)                   |
| Relatórios   | ReportLab (PDF), OpenPyXL (Excel)       |
| Container    | Docker + Docker Compose                 |
| Proxy        | Nginx                                   |

---

## Licença

Uso interno corporativo.
