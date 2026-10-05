# CKP02 — DocMind RAG

Pipeline RAG sobre documentos reais do domínio **recarga de veículos elétricos**: carregadores GoodWe HCA G2 (ficha técnica, manual, aplicativo, compatibilidade) e a norma NDU-042 da Energisa, que define as regras de conexão à rede.

Disciplina: Prompt Engineering and Artificial Intelligence · FIAP · 2º semestre · Checkpoint 02

## Integrantes

| Nome | RM |
|------|----|
| Aline Medri Marcolino | RM:569349 |
| Luis Fernando de Azevedo | RM:574167 |


## O que o projeto faz

Pipeline completo: `load → split → embed → store → retrieve → generate`. A resposta cita o documento e a página de origem dos trechos usados.

| Componente | Escolha |
|------------|---------|
| Embeddings | `nomic-embed-text` (OllamaEmbeddings) |
| Modelo de chat | `gemma4:cloud` via Ollama Cloud, `temperature=0` |
| Banco vetorial | ChromaDB local (coleções `goodwe_ev_<chunk_size>`) |
| Splitter | `RecursiveCharacterTextSplitter` com `separators=["\n\n", "\n", ". ", " ", ""]` e `chunk_overlap` de 10 a 15% do `chunk_size` |
| Avaliação | RAGAS: `faithfulness` e `answer_relevancy` |
| Diferenciais | Reranking com cross-encoder `ms-marco-MiniLM-L-6-v2` e interface Gradio |

## Base de conhecimento

Documentos reais em `data/docs/`, com as fontes abaixo.

| Arquivo | Documento | Emissor |   data /versão   |  Link de origem |
|---------|-----------|---------|------------------|-----------------|
| `goodwe_hca_g2_datasheet.pdf` | Linha HCA G2: carregador CA monofásico 7 kW e trifásico 11/22 kW (ficha técnica) | GoodWe | `V2.1` (2024) | [https://admin.goodwe.com/Ftp/Downloads/Datasheet/PT/GW_HCA-G2_Datasheet-PT.pdf] |
| `goodwe_hca_g2_manual.pdf` | Manual do usuário da linha HCA G2 | GoodWe | `V1.6`(2026) | [https://admin.goodwe.com/Ftp/Downloads/User%20Manual/GW_HCA-G2_User-Manual-PT.pdf] |
| `goodwe_sems_plus_app.pdf` | Guia do aplicativo SEMS+ | GoodWe | `V1.1`(2026) | [https://latam.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_SEMS-PLUS_User-Manual-EN.pdf] |
| `goodwe_compatibilidade.pdf` | Lista de compatibilidade entre carregadores GoodWe e inversores | GoodWe | Versão 1 2026 | [https://en.goodwe.com/Ftp/EN/Downloads/User%20Manual/GW_Compatibility-list-of-GoodWe-EV-Chargers-and-Inverters-EN.pdf] |
| `energisa_ndu042.pdf` | NDU-042: Fornecimento de energia para estações de recarga de veículo elétrico (ENERGISA/GTD-NRM/Nº023/2021) | Grupo Energisa | Versão 1.0 (2026)| [https://www.energisa.com.br/sites/energisa/files/media/documents/2025-02/NDU%20042%20-%20Fornecimento%20de%20energia%20para%20esta%C3%A7%C3%B5es%20de%20recarga%20de%20ve%C3%ADculo%20el%C3%A9trico.pdf] |

## Estrutura do repositório

```
├── app/
│   └── rag.py              funções do pipeline (carregar, dividir, buscar, gerar)
├── data/docs/              documentos da base
├── resultados/             respostas (JSON) e métricas RAGAS (CSV) de cada variante
├── 1_checkin.py            documentos carregados, chunks e busca semântica
├── 2_pipeline.py           pipeline end-to-end (cria o banco vetorial)
├── 3_avaliar.py            comparação de chunking com RAGAS
├── 4_gradio.py             interface web
├── perguntas.py            as 8 perguntas de teste
├── CKP02_DocMind.ipynb     versão em notebook para o Google Colab
├── requirements.txt
├── .env.example
└── README.md
```

## Resultados da comparação de chunking

Foram testadas 4 variantes com as mesmas 8 perguntas. O RAGAS mede `faithfulness` (a resposta está sustentada pelos trechos recuperados) e `answer_relevancy` (a resposta atende à pergunta). A meta do checkpoint é faithfulness média ≥ 0,7.

| Variante | chunk_size | Rerank | Nº de chunks | Faithfulness | Answer relevancy |
|----------|-----------|--------|--------------|--------------|------------------|
| chunk256 | 256 | não | 633 | 0,813 | 0,582 |
| **chunk512** | **512** | **não** | **348** | **1,000** | 0,564 |
| chunk1024 | 1024 | não | 223 | 0,844 | 0,589 |
| chunk512_rerank | 512 | sim | 348 | 0,969 | 0,560 |

Todas as variantes ficaram acima da meta de 0,7. Nenhuma pergunta ficou com valor `NaN`.

### Resultado por pergunta (faithfulness / answer relevancy)

| # | Pergunta | chunk256 | chunk512 | chunk1024 | chunk512_rerank |
|---|----------|----------|----------|-----------|-----------------|
| 0 | Modos de carregamento do HCA e modo PV + Bateria | 0,50 / 0,97 | 1,00 / 0,99 | 1,00 / 1,00 | 1,00 / 0,93 |
| 1 | Modelos da linha HCA G2 e potência de cada um | 1,00 / 0,96 | 1,00 / 0,96 | 1,00 / 0,96 | 1,00 / 0,96 |
| 2 | Iniciar e encerrar recarga pelo aplicativo | 1,00 / 0,00 | 1,00 / 0,00 | 1,00 / 0,00 | 1,00 / 0,00 |
| 3 | Instalação precisa ser comunicada à distribuidora | 1,00 / 0,97 | 1,00 / 0,96 | 0,75 / 0,98 | 0,75 / 0,98 |
| 4 | Cobrar recarga de veículos de terceiros | 1,00 / 0,82 | 1,00 / 0,00 | 1,00 / 0,84 | 1,00 / 0,00 |
| 5 | Veículos injetando energia na rede | 0,00 / 0,93 | 1,00 / 0,87 | 0,00 / 0,93 | 1,00 / 0,87 |
| 6 | Graus de proteção da norma Energisa (ambiente externo) | 1,00 / 0,00 | 1,00 / 0,00 | 1,00 / 0,00 | 1,00 / 0,00 |
| 7 | O que fazer antes de instalar um carregador em casa | 1,00 / 0,00 | 1,00 / 0,74 | 1,00 / 0,00 | 1,00 / 0,74 |

Tabelas completas em `resultados/ragas_<variante>.csv` e resumo em `resultados/resumo.csv`.

### Escolha final: `chunk_size = 512`

- **Maior faithfulness:** com 512 a faithfulness média foi 1,000, contra 0,813 (256) e 0,844 (1024). Em 256 e 1024 a pergunta sobre injeção de energia na rede (#5) teve faithfulness 0,0, enquanto em 512 foi 1,0.
- **Melhor equilíbrio:** o tamanho 256 gera mais que o dobro de chunks (633) e fragmenta as regras da norma; o 1024 mistura assuntos no mesmo trecho. Com 512, a pergunta #7, que cruza regulação e norma da distribuidora, também foi respondida de forma relevante (0,74), o que não ocorreu com 256 e 1024.
- **Reranking:** o cross-encoder entregou faithfulness equivalente (0,969 contra 1,000). A diferença vem de uma única pergunta (#3, com 0,75), então não indica que um seja melhor que o outro nesta amostra. O reranking foi implementado como diferencial e não trouxe ganho adicional medido.

### Limitações

- A amostra tem **8 perguntas**: uma pergunta muda a faithfulness média em 0,125, então diferenças pequenas entre variantes não são conclusivas.
- O avaliador do RAGAS é um LLM e há **variação entre execuções**. Em uma execução anterior, a variante `chunk512` obteve 0,875 e o `chunk512_rerank` 0,975; as variantes `chunk256` e `chunk1024` foram idênticas nas duas execuções. A tabela acima é da execução mais recente e corresponde aos arquivos em `resultados/`.
- Quatro perguntas têm `answer_relevancy = 0,0` em todas ou em quase todas as variantes (#2, #4, #6 e #7 em algumas): [descrever a causa depois de conferir as respostas em `resultados/respostas_chunk512.json`].

## Como rodar

1. Instale o Python 3.12 e o [Ollama](https://ollama.com/download). Baixe o modelo de embeddings:
   ```
   ollama pull nomic-embed-text
   ```
2. Crie o ambiente e instale as dependências:
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\activate
    
   ```
3. Copie `.env.example` para `.env` e preencha:
   ```
   OLLAMA_API_KEY=sua_chave_do_ollama_cloud
   EMBED_BASE_URL=http://localhost:11434
   ```
   A chave é usada pelo modelo de chat (`gemma4:cloud`). Os embeddings rodam no Ollama local, que precisa estar aberto.
4. Rode os scripts na ordem:
   ```
   python 1_checkin.py
   python 2_pipeline.py
   python 3_avaliar.py
   python 4_gradio.py
   ```
   O `3_avaliar.py` leva cerca de 10 a 15 minutos, porque o RAGAS chama o modelo avaliador para cada pergunta.

O arquivo `CKP02_DocMind.ipynb` reproduz o pipeline no Google Colab (a chave fica em **Secrets**, com o nome `OLLAMA_API_KEY`).

## Como adicionar novos documentos

1. Coloque o arquivo (PDF, TXT ou Markdown) em `data/docs/`.
2. Registre o documento e a sua fonte em `data/manifesto.json` e na tabela "Base de conhecimento" deste README.
3. Apague a pasta `chroma_db/` e rode `python 2_pipeline.py` para reindexar.
4. Se quiser medir o efeito do novo documento, rode `python 3_avaliar.py` e compare o `resultados/resumo.csv`.

## Observações

- `app/rag.py` expõe a função `buscar(consulta)`, que será reutilizada como tool no CKP03.
- Se aparecer erro de import sobre `vertexai` ao carregar o `ragas`, instale `langchain-community>=0.4,<0.4.2`.
- O arquivo `.env`, a pasta `.venv/` e o banco `chroma_db/` não são enviados ao repositório.