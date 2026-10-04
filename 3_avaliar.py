import json
from pathlib import Path
import pandas as pd
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import Faithfulness, ResponseRelevancy
from ragas.run_config import RunConfig
from app.rag import buscar, carregar_documentos, criar_colecao, dividir, embeddings, gerar, llm
from perguntas import PERGUNTAS


VARIANTES = [
    ("chunk256", 256, False),
    ("chunk512", 512, False),
    ("chunk1024", 1024, False),
    ("chunk512_rerank", 512, True),  
]


def main():
    Path("resultados").mkdir(exist_ok=True)
    docs = carregar_documentos()
    colecoes = {}
    juiz_llm = LangchainLLMWrapper(llm)
    juiz_emb = LangchainEmbeddingsWrapper(embeddings)
    resumo = []

    for nome, tam, rerank in VARIANTES:
        if tam not in colecoes:
            print(f"\n== Criando coleção com chunk_size={tam} ==")
            chunks = dividir(docs, tam)
            colecoes[tam] = (criar_colecao(chunks, f"goodwe_ev_{tam}"), len(chunks))
        vs, n_chunks = colecoes[tam]

        print(f"\n== Gerando respostas: {nome} ==")
        amostras = []
        for p in PERGUNTAS:
            ctx = buscar(p, vs, rerank=rerank)
            amostras.append({
                "user_input": p,
                "response": gerar(p, ctx),
                "retrieved_contexts": [c.page_content for c in ctx],
            })
        Path(f"resultados/respostas_{nome}.json").write_text(
            json.dumps(amostras, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"== Avaliando com RAGAS: {nome} ==")
        res = evaluate(
            dataset=EvaluationDataset.from_list(amostras),
            metrics=[Faithfulness(), ResponseRelevancy()],
            llm=juiz_llm,
            embeddings=juiz_emb,
            run_config=RunConfig(timeout=300, max_workers=2),
        )
        df = res.to_pandas()
        df.to_csv(f"resultados/ragas_{nome}.csv", index=False)
        cols = [c for c in ["user_input", "faithfulness", "answer_relevancy"] if c in df.columns]
        print(df[cols].to_string())

        resumo.append({
            "variante": nome,
            "chunk_size": tam,
            "rerank": rerank,
            "n_chunks": n_chunks,
            "faithfulness_medio": df["faithfulness"].mean(),
            "answer_relevancy_medio": df["answer_relevancy"].mean(),
            "perguntas_com_NaN": int(df[["faithfulness", "answer_relevancy"]].isna().any(axis=1).sum()),
        })

    tabela = pd.DataFrame(resumo)
    tabela.to_csv("resultados/resumo.csv", index=False)
    print("\n===== RESUMO =====")
    print(tabela.to_string(index=False))


if __name__ == "__main__":
    main()
