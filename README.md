<p align="center">
  <img src="public/favicon.svg" width="80" height="80" alt="Laptop Hunter Logo" />
</p>

<h1 align="center">Laptop Hunter</h1>

<p align="center">
  Plataforma inteligente de monitorização, agregação de ofertas, análise técnica de hardware e automação de propostas de negociação para computadores portáteis no mercado português.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Electron-33.2-47848F?style=flat-square" alt="Electron" />
  <img src="https://img.shields.io/badge/React-19.0-61DAFB?style=flat-square" alt="React 19" />
  <img src="https://img.shields.io/badge/FastAPI-0.110-009688?style=flat-square" alt="FastAPI" />
  <img src="https://img.shields.io/badge/TypeScript-5.7-3178C6?style=flat-square" alt="TypeScript" />
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-38B2AC?style=flat-square" alt="TailwindCSS" />
  <img src="https://img.shields.io/badge/SQLite-WAL-003B57?style=flat-square" alt="SQLite" />
  <img src="https://img.shields.io/badge/Playwright-1.42-2EAD33?style=flat-square" alt="Playwright" />
</p>

---

## Descrição do Projeto

O **Laptop Hunter** é uma ferramenta autónoma desenvolvida para identificar as melhores oportunidades de portáteis em Portugal. A aplicação combina agregação de dados em tempo real, enriquecimento de especificações técnicas através de heurísticas determinísticas e um motor de negociação de preços concebido para o ecossistema de compras nacional.

### Principais Capacidades:
- **Agregação Multi-Plataforma**:
  - **Classificados C2C**: OLX Portugal (via API REST v1 oficial de alto rendimento) e Facebook Marketplace.
  - **Lojas de Retalho & Recondicionados**: PCDiga, Worten, CeX Portugal (5 anos de garantia), PcComponentes, GlobalData e Amazon Prime / Renewed.
- **Identificação de Estado & Garantia Legal**:
  - Deteção automática do estado do equipamento: **Segunda Mão (Usado)**, **Recondicionado** ou **Novo**.
  - Identificação de garantias ativas: garantia legal oficial portuguesa de 3 anos para lojas de retalho, garantia de 5 anos CeX, garantia Amazon Renewed e extração de faturas/prazos de garantia em anúncios particulares do OLX.
  - Filtros rápidos na interface e nas preferências do utilizador para selecionar apenas equipamentos com garantia ou de tipos específicos.
- **Comparador & Dossiê de Engenharia de Hardware**:
  - Classificação e cálculo do valor real de cada GPU (NVIDIA RTX/GTX, AMD Radeon, Apple Silicon, Gráficas Integradas).
  - Cálculo de VRAM dedicada vs partilhada.
  - Índice de adequação para Inteligência Artificial Local (Ollama, PyTorch, LLMs) e tarefas exigentes de engenharia/gaming.
- **Lançador de Propostas em Massa (Batch Pitch)**:
  - Matriz de 12 templates adaptativos baseados no método de entrega (`Auto por Raio`, `CTT à Cobrança`, `Levantamento Presencial`) e no tom de negociação (`Direto`, `Dinheiro Imediato`, `Estudante com Limite de Orçamento`, `Tom Suave`).
  - Arredondamento natural a múltiplos de 5 euros para propostas credíveis no mercado português.
  - Gatekeeping de autenticação que assegura que propostas só são despachadas com sessão de utilizador ativa e certificada.
- **Verificação Contínua de Links (SSE Streaming)**:
  - Verificação em tempo real da validade de cada anúncio com barra de progresso não bloqueante. Anúncios expirados ou eliminados são removidos da base de dados e da interface no milissegundo em que são detetados.
- **Suporte Bilingue**:
  - Interface integralmente disponível em Português e Inglês com comutação instantânea.

---

## Pré-requisitos

Certifique-se de que tem instalado no seu sistema:
1. **Node.js** (versão 18 ou superior) e **npm**
2. **Python** (versão 3.10 ou superior) com módulo `venv`

---

## Instalação

Clone o repositório e instale as dependências:

```bash
# 1. Clonar o repositório
git clone https://github.com/<seu-utilizador>/Laptop_Scraper.git
cd Laptop_Scraper

# 2. Instalar dependências do Frontend e Electron
npm install

# 3. Criar e configurar o ambiente virtual Python
python3 -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# 4. Instalar dependências do Backend Python
pip install -r backend/requirements.txt

# 5. Instalar navegadores headless do Playwright
playwright install chromium
```

---

## Como Executar

Pode executar o **Laptop Hunter** de duas formas consoante a sua preferência:

### Opção A: Executar como Aplicação Desktop (Electron)

Para uma experiência nativa de desktop com integração de janela local:

```bash
npm run electron:dev
```

*Nota: Este comando inicia o servidor de desenvolvimento Vite e abre a janela nativa do Electron. Certifique-se de que o backend Python está ativo em segundo plano ou utilize `npm run web` em conjunto.*

---

### Opção B: Executar no Browser (Aplicação Web)

Se preferir utilizar a aplicação diretamente no seu navegador de internet habitual:

#### Método Rápido (Comando Único):
```bash
npm run web
```
Este comando arranca simultaneamente o backend FastAPI (porta `8001`) e o frontend Vite (porta `5173`).

#### Método Manual (Dois Terminais):
- **Terminal 1 (Backend FastAPI)**:
  ```bash
  source .venv/bin/activate
  python backend/main.py
  ```
  O servidor backend fica acessível em `http://localhost:8001`.

- **Terminal 2 (Frontend Vite)**:
  ```bash
  npm run dev
  ```
  Abra `http://localhost:5173` no seu navegador.

---

### Opção C: Executar com Gestor de Processos PM2 (Servidor / Homelab)

Se pretender manter a aplicação e o daemon de recolha a correr continuamente em segundo plano:

```bash
# Iniciar todos os serviços geridos (Backend + Frontend)
npm run pm2:start

# Consultar os logs em tempo real
npm run pm2:logs

# Parar os serviços
npm run pm2:stop
```

---

## Testes & Qualidade de Código (TDD)

O projeto inclui uma suíte completa de testes unitários e de integração validando o motor de negociação e a classificação de garantias.

Para executar todos os testes localmente:
```bash
.venv/bin/python -m unittest discover -s backend/tests -p "test_*.py" -v
```

Em alternativa, pode verificar o relatório de testes diretamente através da API em execução:
```bash
curl http://localhost:8001/api/system/run-tests
```

Para validar a compilação de produção e tipos TypeScript:
```bash
npm run build
```

---

## Estrutura do Repositório

```text
├── backend/
│   ├── main.py                   # API FastAPI & Orquestrador de Serviços
│   ├── database.py               # Motor SQLite (WAL, transações atómicas)
│   ├── hardware_comparator.py    # Dossiê técnico de CPU/GPU/VRAM
│   ├── negotiation.py            # Regras de desconto e templates portugueses
│   ├── laptop_scraper.py         # Motores de recolha multi-loja
│   ├── link_verifier.py          # Verificador de integridade de links (SSE)
│   ├── geo_utils.py              # Cálculo de distâncias e áreas metropolitanas
│   ├── tests/                    # Suíte TDD de testes unitários
│   └── requirements.txt          # Dependências Python
├── electron/
│   ├── main.cjs                  # Ponto de entrada Electron
│   └── preload.cjs               # Context bridge seguro
├── src/
│   ├── App.tsx                   # Componente raiz e navegação
│   ├── components/               # Vistas do catálogo, negociações e definições
│   ├── i18n/                     # Sistema bilingue (PT / EN)
│   └── lib/                      # Utilitários de interface
├── public/
│   ├── favicon.svg               # Ícone oficial da aplicação
│   └── logos/                    # Vetores das lojas suportadas
├── scripts/                      # Scripts auxiliares de arranque e importação
├── ecosystem.config.cjs          # Configuração para PM2
├── package.json                  # Dependências e scripts npm
├── tailwind.config.js            # Configuração de estilos
└── README.md
```

---

## Segurança & Privacidade

- **Ficheiros Sensíveis Ignorados**: O ficheiro `.gitignore` foi configurado de forma estrita para impedir o envio acidental de ficheiros de base de dados locais (`*.db`), sessões autenticadas ou cookies de navegação (`storage_state_*.json`, `playwright_profile/`), registos de log (`*.log`) e ficheiros de configuração de utilizador.
- **Armazenamento 100% Local**: Todos os dados recolhidos e preferências são mantidos exclusivamente na base de dados SQLite local na sua máquina, sem qualquer envio para servidores ou telemetrias de terceiros.
- **Design Limpo**: Cumprimento rigoroso de padrões visuais modernos, tema claro de alto contraste e utilização exclusiva de ícones SVG.
