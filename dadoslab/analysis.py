from __future__ import annotations
import numpy as np
import pandas as pd
from scipy import stats
from .bridge import NativeDice, audit, validate

MC_REPETITIONS = 10_000


def analyze(values, selected=1, native=None):
    values = validate(values)
    if type(selected) is not int or not 1 <= selected <= 6:
        raise ValueError("Selecione uma face entre 1 e 6.")
    n = len(values)
    counts = (native or NativeDice()).counts(values)
    java = audit(values)
    if java["counts"] != counts:
        raise RuntimeError("Contagens C++ e Java divergiram; análise interrompida.")
    frequencies = np.array(counts, dtype=float) / n if n else np.zeros(6)
    intervals = [stats.binomtest(k, n, 1/6).proportion_ci(method="exact") for k in counts] if n else [(0, 1)] * 6
    rows = pd.DataFrame({"face": range(1, 7), "contagem": counts,
        "frequencia": frequencies, "probabilidade_teorica": [1/6] * 6,
        "ic95_inferior": [float(c[0]) for c in intervals],
        "ic95_superior": [float(c[1]) for c in intervals]})
    pvalue = None
    method = "Sem observações"
    mc_error = None
    if n:
        expected = n / 6
        reference = float(stats.chisquare(counts).statistic)
        if not np.isclose(reference, java["chi2"], atol=1e-8):
            raise RuntimeError("Estatística Java divergiu da referência SciPy.")
        if expected >= 5 and min(counts) >= 5:
            pvalue = float(stats.chisquare(counts).pvalue)
            method = "Qui-quadrado de Pearson · 5 graus de liberdade"
        else:
            # Finite-sample null reference; avoids a chi-square approximation in sparse data.
            rng = np.random.default_rng(20261023)
            simulated = rng.multinomial(n, [1/6]*6, size=MC_REPETITIONS)
            statistics = ((simulated - expected)**2 / expected).sum(axis=1)
            pvalue = float((1 + np.count_nonzero(statistics >= reference - 1e-10)) / (MC_REPETITIONS + 1))
            mc_error = float(np.sqrt(pvalue * (1-pvalue) / (MC_REPETITIONS+1)))
            method = "Monte Carlo multinomial · 10.000 réplicas · semente fixa"
    array = np.asarray(values, dtype=float)
    selected_row = rows.iloc[selected-1].to_dict()
    return {"n": n, "selected": selected, "counts": counts, "table": rows.to_dict(orient="records"),
        "selected_row": selected_row, "mean": float(array.mean()) if n else None,
        "median": float(np.median(array)) if n else None,
        "variance": float(array.var(ddof=1)) if n > 1 else None,
        "std": float(array.std(ddof=1)) if n > 1 else None,
        "modes": [i+1 for i,c in enumerate(counts) if c == max(counts)] if n else [],
        "pvalue": pvalue, "method": method, "mc_standard_error": mc_error,
        "java": java, "theoretical_mean": 3.5, "theoretical_variance": 35/12}


def conclusion(result, mode):
    n = result["n"]
    if not n:
        return "Faça o primeiro lançamento para iniciar a análise. Em um dado justo, cada face tem chance de 1/6 (16,67%) em cada tentativa independente."
    face = result["selected"]
    row = result["selected_row"]
    text = (f"Em {n:,} lançamentos, a face {face} apareceu {int(row['contagem']):,} vezes "
        f"({row['frequencia']:.2%}). O modelo de dado justo atribui 16,67% a essa face. "
        f"IC individual de 95% para sua proporção: {row['ic95_inferior']:.2%} a {row['ic95_superior']:.2%}. ")
    if result["pvalue"] < .05:
        text += "O teste exploratório encontrou discrepância em relação à uniformidade (p < 0,05). Isso não prova viés nem identifica sua causa. "
    else:
        text += "O teste exploratório não encontrou evidência suficiente contra a uniformidade a 5%. Isso não prova que o dado seja justo. "
    if mode == "virtual":
        text += "Esta sessão avalia resultados de um gerador pseudoaleatório, não um dado físico. "
    text += "A análise não prevê a próxima face. Testes repetidos e escolha posterior da face exigem cautela."
    return text


def report_text(result, mode):
    def fmt(value):
        return "não definido" if value is None else f"{value:.6g}"
    java = result["java"]
    text = ["DadosLab 0.1.0 — relatório estatístico", f"Origem: {mode}", "",
        conclusion(result, mode), "", f"N: {result['n']}",
        f"Média: {fmt(result['mean'])}; teórica: 3,5",
        f"Mediana: {fmt(result['median'])}",
        f"Variância amostral (n-1): {fmt(result['variance'])}; teórica: 35/12",
        f"Desvio padrão amostral: {fmt(result['std'])}", f"Modas: {result['modes']}",
        f"Entropia empírica (Java): {java['entropy']:.6g} bits; máximo: log2(6)",
        f"Maior sequência da mesma face (Java): {java['longest_run']}",
        f"Correlação descritiva de defasagem 1 (Java): {fmt(java['lag1'])}",
        f"Estatística de Pearson (Java, conferida em SciPy): {java['chi2']:.6g}",
        f"Método do p-valor: {result['method']}", f"p-valor: {fmt(result['pvalue'])}",
        f"Erro padrão Monte Carlo aproximado: {fmt(result['mc_standard_error'])}", "",
        "Os ICs são individuais, não simultâneos. O p-valor não é a probabilidade de o dado ser justo.",
        "Independência dos lançamentos é uma hipótese, não uma conclusão do teste de frequências.",
        "Entropia, correlação e sequências são descritivas; não certificam aleatoriedade.",
        "Nenhum resultado passado altera 1/6 no modelo de dado justo e independente.", "",
        pd.DataFrame(result["table"]).to_string(index=False)]
    return "\n".join(text)
