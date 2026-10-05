import html
import re
from datetime import datetime

import gradio as gr

from app.rag import abrir_colecao, carregar_documentos, criar_colecao, dividir, responder


NOME = "goodwe_ev_512"
vs = abrir_colecao(NOME)
if vs._collection.count() == 0:
    vs = criar_colecao(dividir(carregar_documentos(), 512), NOME)

TIPOS = ["todos", "manual", "norma", "pagina_oficial"]  # valores da metadata "tipo"

SAUDACAO = "Olá! 👋 Sou a Norah, assistente inteligente da GoodWe.\n\nComo posso ajudar você hoje?"
AVISO = "Assistente demonstrativo. Confirme funções, limites e condições comerciais nos documentos oficiais do produto."


PERGUNTAS_RAPIDAS = [
    ("Carregar durante meu filme",
     "Quero carregar o carro em poucas horas, por exemplo enquanto assisto a um filme. Qual modo de carregamento devo usar?"),
    ("Isso prejudica minha bateria?",
     "Carregar o veículo elétrico com o carregador GoodWe HCA pode prejudicar a bateria do carro?"),
    ("Meu carregador suporta isso?",
     "Quais são as potências e as características técnicas de cada modelo do carregador GoodWe HCA G2?"),
    ("Eu recebo por ceder energia?",
     "Posso injetar energia do veículo elétrico de volta na rede e receber por isso?"),
    ("Preciso sair com urgência",
     "Preciso carregar o carro o mais rápido possível. Como funciona o modo de carregamento rápido?"),
]

VERMELHO = "#d9131b"
CSS = f"""
.gradio-container {{ max-width: 100% !important; background: #ffffff; color-scheme: light;
  font-family: 'Inter','Segoe UI',Arial,sans-serif; }}
.gradio-container .block {{ border: none !important; box-shadow: none !important; background: transparent !important; padding: 0 !important; }}
footer {{ display: none !important; }}

#marca, #rapidas, #principal {{ border: 1px solid #e3e7e8 !important; border-radius: 18px !important; background: #fff !important; padding: 18px !important; }}
#principal {{ padding: 0 !important; overflow: hidden; }}
#lateral {{ gap: 16px !important; }}

.marca {{ text-align: center; }}
.marca .logo {{ width: 38px; height: 38px; margin: 6px auto 10px; border-radius: 10px; background: {VERMELHO};
  color: #fff; font-weight: 800; font-size: 14px; display: flex; align-items: center; justify-content: center; }}
.marca .nome {{ font-weight: 700; font-size: 14px; color: #1d2327; }}
.marca .desc {{ font-size: 10.5px; color: #6b767c; margin: 6px 0 10px; }}
.chip {{ display: inline-flex; align-items: center; gap: 6px; background: #fdecee; color: {VERMELHO};
  font-size: 10px; font-weight: 700; padding: 4px 10px; border-radius: 999px; }}
.chip i {{ width: 6px; height: 6px; border-radius: 50%; background: {VERMELHO}; display: inline-block; }}

.rotulo {{ font-size: 9.5px; letter-spacing: .08em; color: #6b767c; font-weight: 700; margin: 4px 0 12px; }}
.rapida {{ background: #fff !important; border: 1px solid #d8dde0 !important; border-radius: 12px !important;
  color: #2b3236 !important; font-weight: 600 !important; font-size: 14px !important; padding: 14px 12px !important;
  box-shadow: none !important; width: 100%; margin-bottom: 6px; }}
.rapida:hover {{ border-color: {VERMELHO} !important; color: {VERMELHO} !important; }}

.topo {{ display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; border-bottom: 1px solid #eceff0; }}
.topo .titulo {{ font-weight: 700; font-size: 17px; color: #1d2327; }}
.topo .sub {{ font-size: 11px; color: #6b767c; margin-top: 3px; }}
.selo {{ background: #fdecee; color: {VERMELHO}; font-size: 9px; font-weight: 800; padding: 5px 10px; border-radius: 999px; }}

.rolagem {{ display: flex; flex-direction: column-reverse; height: calc(100vh - 300px); min-height: 340px; overflow-y: auto; padding: 24px 32px; }}
.lista {{ margin-bottom: auto; display: flex; flex-direction: column; gap: 18px; }}
.msg {{ display: flex; gap: 10px; align-items: flex-start; max-width: 78%; }}
.msg.user {{ align-self: flex-end; flex-direction: row-reverse; }}
.av {{ flex: 0 0 auto; width: 30px; height: 30px; border-radius: 50%; background: {VERMELHO}; color: #fff;
  font-size: 10px; font-weight: 800; display: flex; align-items: center; justify-content: center; }}
.corpo .nome {{ font-size: 10.5px; color: #6b767c; margin-bottom: 4px; }}
.corpo .nome b {{ color: #1d2327; margin-right: 4px; }}
.balao {{ background: #f6f8f7; border: 1px solid #e3e7e8; border-radius: 14px; padding: 12px 16px;
  font-size: 12.5px; line-height: 1.55; color: #2b3236 !important; }}
.msg.user .balao {{ background: {VERMELHO}; border-color: {VERMELHO}; color: #fff !important; }}
.fontes {{ font-size: 10px; color: #8a949a; margin-top: 6px; }}
.pontos i {{ display: inline-block; width: 6px; height: 6px; margin: 0 2px; border-radius: 50%; background: #9aa5ab;
  animation: pulo 1s infinite ease-in-out; }}
.pontos i:nth-child(2) {{ animation-delay: .15s; }} .pontos i:nth-child(3) {{ animation-delay: .3s; }}
@keyframes pulo {{ 0%,80%,100% {{ opacity: .3; transform: translateY(0); }} 40% {{ opacity: 1; transform: translateY(-3px); }} }}

#barra {{ border-top: 1px solid #eceff0 !important; padding: 16px 18px !important; gap: 12px !important;
  align-items: center !important; flex-wrap: nowrap !important; }}
#entrada textarea, #entrada input {{ border: 1px solid #d8dde0 !important; border-radius: 999px !important;
  padding: 14px 22px !important; font-size: 13px !important; box-shadow: none !important;
  background: #fff !important; color: #1d2327 !important; -webkit-text-fill-color: #1d2327 !important; }}
#entrada textarea::placeholder, #entrada input::placeholder {{ color: #98a2a8 !important; -webkit-text-fill-color: #98a2a8 !important; }}
#entrada textarea:focus, #entrada input:focus {{ border-color: {VERMELHO} !important; }}
#enviar {{ background: {VERMELHO} !important; border: none !important; border-radius: 14px !important; color: #fff !important;
  height: 48px !important; min-width: 56px !important; max-width: 56px !important; font-size: 18px !important; box-shadow: none !important; }}
.aviso {{ text-align: center; font-size: 8.5px; color: #98a2a8; padding: 4px 16px 14px; }}
"""


def _formatar(texto):
    """Escapa o texto e converte **negrito**, listas e quebras de linha em HTML."""
    seguro = html.escape(texto)
    seguro = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", seguro)
    seguro = re.sub(r"^[-*] ", "• ", seguro, flags=re.M)
    return seguro.replace("\n", "<br>")


def _hora():
    return datetime.now().strftime("%H:%M")


def _limpar(texto_html):
    """Remove as tags HTML para enviar o histórico como texto puro ao RAG."""
    return re.sub(r"<[^>]+>", " ", texto_html).strip()


def _render(historico, digitando=False):
    """Monta o HTML do chat a partir do histórico [(papel, html, hora, fontes), ...]."""
    blocos = []
    for papel, texto, hora, fontes in historico:
        if papel == "user":
            blocos.append(f'<div class="msg user"><div class="corpo"><div class="balao">{texto}</div></div></div>')
        else:
            extra = f'<div class="fontes">Fontes: {html.escape(fontes)}</div>' if fontes else ""
            blocos.append(
                f'<div class="msg bot"><div class="av">GW</div><div class="corpo">'
                f'<div class="nome"><b>GoodWe</b> {hora}</div><div class="balao">{texto}</div>{extra}</div></div>'
            )
    if digitando:
        blocos.append(
            '<div class="msg bot"><div class="av">GW</div><div class="corpo"><div class="nome"><b>GoodWe</b> digitando</div>'
            '<div class="balao"><span class="pontos"><i></i><i></i><i></i></span></div></div></div>'
        )
    return f'<div class="rolagem"><div class="lista">{"".join(blocos)}</div></div>'


def conversar(mensagem, historico, tipo, rerank, consulta=None):
    """Registra a pergunta, roda o RAG (com memória) e devolve (html do chat, histórico, campo limpo)."""
    texto = (mensagem or "").strip()
    if not texto:
        yield _render(historico), historico, ""
        return

    # conversa anterior em texto puro (pula a saudação inicial), capturada ANTES da pergunta atual
    anteriores = [(p, _limpar(t)) for p, t, _, _ in historico[1:]]

    historico = historico + [("user", _formatar(texto), _hora(), "")]
    yield _render(historico, digitando=True), historico, ""
    try:
        filtro = None if tipo == "todos" else {"tipo": tipo}
        r = responder(consulta or texto, vs, filtro=filtro, rerank=rerank, historico=anteriores)
        resposta = _formatar(r["resposta"])
        fontes = "; ".join(dict.fromkeys(r["fontes"]))
    except Exception as erro:  # mostra o erro no chat em vez de derrubar a interface
        print("Erro ao consultar o RAG:", repr(erro))
        resposta = "Não consegui consultar os documentos agora. Tente de novo em instantes."
        fontes = ""
    historico = historico + [("bot", resposta, _hora(), fontes)]
    yield _render(historico), historico, ""


def _rapida(rotulo, pergunta):
    def acao(historico, tipo, rerank):
        yield from conversar(rotulo, historico, tipo, rerank, pergunta)
    return acao


INICIO = [("bot", _formatar(SAUDACAO), "agora", "")]

with gr.Blocks(title="DocMind · Norah GoodWe") as demo:
    gr.HTML(f"<style>{CSS}</style>")
    estado = gr.State(INICIO)
    tipo = gr.State("todos")     # sem filtro por tipo de documento
    rerank = gr.State(True)      # reranking sempre ligado

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=250, elem_id="lateral"):
            with gr.Column(elem_id="marca"):
                gr.HTML(
                    '<div class="marca"><div class="logo">GW</div><div class="nome">Assistente GoodWe</div>'
                    '<div class="desc">Seu assistente inteligente para carregamento de veículos elétricos.</div>'
                    '<span class="chip"><i></i>IA online</span></div>'
                )
            with gr.Column(elem_id="rapidas"):
                gr.HTML('<div class="rotulo">PERGUNTAS RÁPIDAS</div>')
                botoes = [(gr.Button(r, elem_classes="rapida"), r, p) for r, p in PERGUNTAS_RAPIDAS]

        with gr.Column(scale=4, elem_id="principal"):
            gr.HTML(
                '<div class="topo"><div><div class="titulo">Assistente de Energia</div>'
                '<div class="sub">Como posso ajudar com seu carregamento?</div></div>'
                '<span class="selo">GOODWE AI</span></div>'
            )
            chat = gr.HTML(_render(INICIO), elem_id="chat")
            with gr.Row(elem_id="barra"):
                entrada = gr.Textbox(placeholder="Digite sua pergunta sobre o carregador...", show_label=False,
                                     container=False, lines=1, max_lines=1, scale=12, elem_id="entrada")
                enviar = gr.Button("➤", elem_id="enviar", scale=1, min_width=56)
            gr.HTML(f'<div class="aviso">{AVISO}</div>')

    saidas = [chat, estado, entrada]
    entrada.submit(conversar, [entrada, estado, tipo, rerank], saidas)
    enviar.click(conversar, [entrada, estado, tipo, rerank], saidas)
    for botao, rotulo, pergunta in botoes:
        botao.click(_rapida(rotulo, pergunta), [estado, tipo, rerank], saidas)


if __name__ == "__main__":
    try:
        demo.launch(css=CSS, theme=gr.themes.Default(), inbrowser=True)
    except TypeError:
        demo.launch(inbrowser=True)