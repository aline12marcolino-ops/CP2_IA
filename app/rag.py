import json
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "data" / "docs"
MANIFESTO = BASE_DIR / "data" / "manifesto.json"
CHROMA_DIR = BASE_DIR / "chroma_db"
EXTENSOES = {".pdf", ".txt", ".md"}

_API_KEY = os.getenv("OLLAMA_API_KEY")
if not _API_KEY:
    raise RuntimeError("OLLAMA_API_KEY não foi encontrada no arquivo .env")
_CHAT_URL = "https://ollama.com"
_EMBED_URL = os.getenv("EMBED_BASE_URL", "https://ollama.com")


def _auth(url):
    """Só envia a chave quando o destino é o Ollama Cloud."""
    if "ollama.com" in url:
        return {"headers": {"Authorization": f"Bearer {_API_KEY}"}}
    return {}

embeddings = OllamaEmbeddings(
    model="nomic-embed-text", base_url=_EMBED_URL, client_kwargs=_auth(_EMBED_URL)
)

llm = ChatOllama(
    model="gemma4:cloud", base_url=_CHAT_URL, temperature=0,
    client_kwargs=_auth(_CHAT_URL),
)

SISTEMA = (
    "Você é a Norah, assistente virtual da GoodWe especializada em mobilidade "
    "elétrica e carregadores de veículos elétricos.\n"
    "Responda sempre em português do Brasil, de forma clara e objetiva.\n"
    "Use APENAS as informações do contexto fornecido. Não invente valores, "
    "modelos ou funcionalidades.\n"
    "Cite a fonte de cada informação no formato [arquivo, p.X].\n"
    "Se o contexto não tiver a resposta, diga que não há dados suficientes "
    "nos documentos para responder com segurança.\n"
    "Use a conversa anterior (quando houver) apenas para entender a pergunta atual.\n"
    "Se a pergunta for ambígua (por exemplo, não diz o modelo), pergunte qual modelo "
    "o usuário tem ou apresente a resposta para cada modelo encontrado no contexto.\n"
    "Em perguntas técnicas, apresente os valores com unidade e modelo, em lista curta.\n"
    "Se o usuário apenas cumprimentar ou agradecer, responda de forma breve e natural, "
    "sem citar fontes.\n"
    "Não copie os documentos literalmente; explique de forma simples."
)

def carregar_documentos(pasta=DOCS_DIR, manifesto=MANIFESTO):
    """Carrega PDF/TXT/MD e anexa a metadata do manifesto.json a cada página."""
    meta_arquivos = json.loads(Path(manifesto).read_text(encoding="utf-8"))
    docs = []
    for arq in sorted(Path(pasta).iterdir()):
        if arq.suffix.lower() not in EXTENSOES:
            continue
        if arq.name not in meta_arquivos:
            print(f"[aviso] {arq.name} não está no manifesto.json (ficará sem metadata)")
        if arq.suffix.lower() == ".pdf":
            paginas = PyPDFLoader(str(arq)).load()
        else:
            paginas = TextLoader(str(arq), encoding="utf-8").load()
        for p in paginas:
            if not p.page_content.strip():
                continue
            meta = {"arquivo": arq.name, **meta_arquivos.get(arq.name, {})}
            if "page" in p.metadata:  # PDFs: página começa em 0, então somamos 1
                meta["pagina"] = int(p.metadata["page"]) + 1
            p.metadata = meta
            docs.append(p)
    return docs

def dividir(docs, chunk_size):
    """Divide em chunks. O overlap é 12,5% do chunk_size (faixa exigida: 10-15%)."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size * 0.125),
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def abrir_colecao(nome):
    """Abre uma coleção ChromaDB já persistida (sem recalcular embeddings)."""
    return Chroma(
        collection_name=nome,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR / nome),
    )

def criar_colecao(chunks, nome):
    """Recria a coleção do zero (evita chunks duplicados ao rodar de novo)."""
    try:
        abrir_colecao(nome).delete_collection()
    except Exception:
        pass
    vs = abrir_colecao(nome)
    for i in range(0, len(chunks), 64):  # lotes pequenos para não estourar a API
        vs.add_documents(chunks[i:i + 64])
    return vs

_reranker = None

def _obter_reranker():
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker


def buscar(consulta, vs, k=4, filtro=None, rerank=False):
    """
    Busca semântica na base. Esta é a função que vira @tool no CKP03.

    filtro: dict de metadata, ex.: {"tipo": "norma"}
    rerank: se True, busca 15 candidatos e reordena com cross-encoder.
            Se False, usa MMR (relevância + diversidade) para evitar chunks repetidos.
    """
    if rerank:
        candidatos = vs.similarity_search(consulta, k=15, filter=filtro)
        if candidatos:
            notas = _obter_reranker().predict([(consulta, d.page_content) for d in candidatos])
            ordenados = sorted(zip(notas, candidatos), key=lambda x: -x[0])
            candidatos = [d for _, d in ordenados][:k]
        return candidatos
    return vs.max_marginal_relevance_search(consulta, k=k, fetch_k=15, filter=filtro)

def rotulo_fonte(d):
    """Texto de citação, ex.: 'goodwe_hca_manual.pdf, p.12'."""
    arquivo = d.metadata.get("arquivo", "?")
    pagina = d.metadata.get("pagina")
    return f"{arquivo}, p.{pagina}" if pagina else arquivo

def _formatar_conversa(historico, limite=6):
    """Converte [(papel, texto), ...] em texto simples com as últimas mensagens."""
    return "\n".join(
        f"{'Usuário' if papel == 'user' else 'Norah'}: {texto}"
        for papel, texto in historico[-limite:]
    )

def reescrever(pergunta, historico):
    """
    Transforma uma pergunta de acompanhamento (ex.: 'e a potência dele?')
    em uma consulta independente, usando a conversa anterior.
    Só roda quando há histórico e a pergunta é curta (economiza uma chamada ao LLM).
    """
    if not historico or len(pergunta.split()) >= 12:
        return pergunta
    prompt = (
        "Dada a conversa abaixo, reescreva a ÚLTIMA pergunta do usuário como uma "
        "pergunta completa e independente, em português, citando o produto/modelo "
        "mencionado antes se necessário. Responda apenas com a pergunta reescrita.\n\n"
        f"{_formatar_conversa(historico)}\n\nÚltima pergunta: {pergunta}"
    )
    try:
        reescrita = llm.invoke([("human", prompt)]).content.strip()
        return reescrita or pergunta
    except Exception as erro:
        print("Falha ao reescrever a pergunta:", repr(erro))
        return pergunta


def gerar(pergunta, docs, historico=None):
    """Gera a resposta da Norah usando APENAS os chunks recuperados e citando a fonte."""
    contexto = "\n\n".join(f"[Fonte: {rotulo_fonte(d)}]\n{d.page_content}" for d in docs)
    conversa = ""
    if historico:
        conversa = f"<conversa>\n{_formatar_conversa(historico)}\n</conversa>\n\n"
    humano = f"{conversa}<contexto>\n{contexto}\n</contexto>\n\nPergunta: {pergunta}"
    return llm.invoke([("system", SISTEMA), ("human", humano)]).content


def responder(pergunta, vs, k=4, filtro=None, rerank=False, historico=None):
    """
    Atalho: reescrita + busca + geração.
    historico: lista [(papel, texto_puro), ...] das mensagens anteriores.
    Devolve resposta, fontes, textos dos chunks e a consulta usada na busca.
    """
    historico = historico or []
    consulta = reescrever(pergunta, historico)
    docs = buscar(consulta, vs, k=k, filtro=filtro, rerank=rerank)
    return {
        "resposta": gerar(pergunta, docs, historico),
        "fontes": [rotulo_fonte(d) for d in docs],
        "contextos": [d.page_content for d in docs],
        "consulta": consulta,
    }