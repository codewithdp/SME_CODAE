# Frontend - Sistema de Reconciliação EMEI

Interface web em TypeScript + React para o sistema de reconciliação de dados EMEI da SME.

## Tecnologias

- **React 18.3** - Framework UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool
- **Tailwind CSS** - Estilização
- **Axios** - Cliente HTTP
- **Lucide React** - Ícones

## Pré-requisitos

- Node.js 18+ instalado
- Backend rodando em `http://localhost:8000`

## Instalação

```bash
# Instalar dependências
npm install
```

## Execução

```bash
# Desenvolvimento (porta 3000)
npm run dev

# Build para produção
npm run build

# Preview do build
npm run preview
```

## Estrutura

```
src/
├── api/
│   └── reconciliation.ts    # Cliente API
├── types/
│   └── index.ts             # TypeScript interfaces
├── App.tsx                  # Componente principal
├── main.tsx                 # Entry point
└── index.css                # Estilos globais
```

## Funcionalidades

1. **Upload de Arquivos**
   - Seleção de arquivo Excel (.xlsm, .xlsx, .xls)
   - Seleção de arquivo PDF
   - Validação de tipos

2. **Processamento**
   - Upload via API
   - Polling de status em tempo real
   - Barra de progresso

3. **Resultados**
   - Métricas de reconciliação
   - Taxa de correspondência
   - Lista detalhada de divergências por seção
   - Download de relatório Excel

## API Backend

O frontend se comunica com os seguintes endpoints:

- `POST /api/v1/reconciliation/upload` - Upload de arquivos
- `GET /api/v1/reconciliation/{id}/status` - Status da reconciliação
- `GET /api/v1/reconciliation/{id}/report` - Download do relatório

## Idioma

Toda a interface está em **Português Brasileiro**.
