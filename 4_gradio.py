import gradio as gr
from app.rag import abrir_colecao, carregar_documentos, criar_colecao, dividir, responder

NOME = "goodwe_ev_512"
vs = abrir_colecao(NOME)
if vs._collection.count() == 0:
    vs = criar_colecao(dividir(carregar_documentos(), 512), NOME)


def chat(mensagem, historico, tipo, rerank):
    filtro = None if tipo == "todos" else {"tipo": tipo}
    r = responder(mensagem, vs, filtro=filtro, rerank=rerank)
    fontes = "\n".join(f"- {f}" for f in dict.fromkeys(r["fontes"]))
    return f"{r['resposta']}\n\n**Fontes consultadas:**\n{fontes}"


demo = gr.ChatInterface(
    chat,
    title="DocMind · Norah GoodWe",
    description="Pergunte sobre carregadores GoodWe e regulação de recarga de veículos elétricos.",
    additional_inputs=[
        gr.Dropdown(["todos", "manual", "norma", "pagina_oficial"], value="todos",
                    label="Filtrar por tipo de documento"),
        gr.Checkbox(value=False, label="Usar reranking (cross-encoder)"),
    ],
)

if __name__ == "__main__":
    demo.launch()
