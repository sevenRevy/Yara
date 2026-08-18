# YARA

YARA é um assistente virtual de hotel pensado para começar já com uma demonstração útil: o usuário entra, vê a apresentação da assistente, recebe uma reserva de exemplo e passa direto para o chat com contexto carregado.

## Visão geral

O fluxo principal é este:

```text
Entrada
  ↓
Apresentação da YARA
  ↓
Reserva demonstrativa aleatória
  ↓
Contexto da estadia carregado
  ↓
Chat
```

Exemplo de contexto inicial:

```text
Hóspede: Lucas Mendes
Quarto: 304
Tipo: Deluxe
Período: 18–21 agosto
Café da manhã: incluído
```

A ideia é que o usuário possa perguntar imediatamente coisas como:

- Que horas é o café da manhã?
- Onde fica a piscina?
- Meu quarto tem frigobar?
- Posso fazer checkout mais tarde?

## Dois tipos de conhecimento

A aplicação trata **CSV** e **PDF** como fontes diferentes de conhecimento.

### CSV: conhecimento estruturado

O CSV alimenta dados operacionais do hotel:

- quartos
- reservas
- serviços
- horários
- atributos fixos da hospedagem

Esses dados devem ser consultados de forma estruturada, normalmente via SQL, e não como embeddings.

Exemplos de perguntas que podem ir direto para consulta estruturada:

- Qual é o quarto do Lucas Mendes?
- Meu quarto tem frigobar?
- Qual é a data de checkout da reserva atual?

### PDF: conhecimento textual

O PDF alimenta o material textual usado pelo RAG:

- políticas
- manuais
- regras
- descrições do hotel
- orientações para o hóspede

Esse conteúdo passa por extração, limpeza, divisão em chunks, embeddings e busca semântica.

Exemplos:

- Posso fazer checkout mais tarde?
- Qual é a política de café da manhã?
- Como funciona o late checkout?

## Fluxo de resposta

Na prática, a resposta da YARA combina:

```text
Reserva atual
+ dados estruturados do hotel
+ RAG dos documentos
+ LLM
```

Um roteamento simples já resolve o MVP:

```text
Pergunta do usuário
  ↓
Identificação do tipo de consulta
  ↓
Consulta estruturada, RAG, ou ambos
  ↓
Montagem do contexto
  ↓
LLM
  ↓
Resposta da YARA
```

Para perguntas claramente ligadas à reserva atual, a consulta estruturada deve vir primeiro. Para perguntas sobre políticas, regras e informações textuais, o RAG deve ser a fonte principal. Em casos mistos, a resposta pode combinar as duas fontes.

## Arquitetura lógica

```text
                          FRONTEND
                            ↓
                          BACKEND API
                            ↓
┌──────────────┬──────────────────┬─────────────────┐
│              │                  │                 │
▼              ▼                  ▼                 ▼
CSV        Banco local        PDFs             Sessão atual
dados       estruturados       de hotel        da hospedagem
```

O núcleo do pipeline de documentos é:

```text
parsing → limpeza → chunking → embeddings → indexação → busca → seleção de contexto → prompt → LLM
```

O núcleo dos dados estruturados é:

```text
CSV → validação/normalização → armazenamento estruturado → consulta SQL
```

