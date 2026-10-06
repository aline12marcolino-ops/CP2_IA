from app.rag import abrir_colecao, carregar_documentos, criar_colecao, dividir, responder

NOME = "goodwe_ev_512"
vs = abrir_colecao(NOME)
if vs._collection.count() == 0: 
    vs = criar_colecao(dividir(carregar_documentos(), 512), NOME)

while True:
    pergunta = input("\nPergunta (enter para sair): ").strip()
    if not pergunta:
        break
    r = responder(pergunta, vs)
    print("\n" + r["resposta"])
    print("\nFontes recuperadas:", "; ".join(r["fontes"]))
