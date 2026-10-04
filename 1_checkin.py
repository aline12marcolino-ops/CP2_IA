from app.rag import buscar, carregar_documentos, criar_colecao, dividir

docs = carregar_documentos()
print(f"{len(docs)} páginas/documentos carregados")

chunks = dividir(docs, 512)
print(f"{len(chunks)} chunks gerados (chunk_size=512)")

vs = criar_colecao(chunks, "goodwe_ev_512")
consulta = "Quais são os modos de carregamento do carregador?"
print(f"\nBusca: {consulta}\n")
for d in buscar(consulta, vs):
    print(d.metadata["arquivo"], "| p.", d.metadata.get("pagina", "-"))
    print(d.page_content[:200].replace("\n", " "), "\n")
