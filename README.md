# Exercício 9 – Curva GZ, momento de vento e critério de áreas

Modelo paramétrico de estabilidade intacta da semissubmersível (2 pontoons + 4 colunas), feito com as mesmas
ferramentas do repositório [Projetos_Sistemas_Oceanicos](https://github.com/dpratavieira/Projetos_Sistemas_Oceanicos)
(Python, NumPy, SciPy, pandas, Streamlit, Plotly, matplotlib).

| Arquivo | Conteúdo |
|---|---|
| `ex9_estabilidade.py` | modelo: hidrostática (Ex. 7), pesos/KG e otimização (Ex. 8), GZ por projeções 2D, φal, vento por parcela, z_CLR, HM0, HMud, HA(φ), φ1, φ2, A, B, critério |
| `dashboard_estabilidade_semi.py` | simulação interativa (Streamlit) |
| `gerar_apresentacao_ex9.py` | gera `figuras/` e `ex9_apresentacao.pptx` |
| `referencia/codigo_ex7.py`, `referencia/codigo_ex8.py` | códigos dos Exercícios 7 e 8 usados na conferência |
| `resultados/` | CSVs e saída de `python ex9_estabilidade.py` |

```bash
python -m pip install -r requirements.txt
python ex9_estabilidade.py                         # tabelas no terminal + CSVs
python -m streamlit run dashboard_estabilidade_semi.py
python gerar_apresentacao_ex9.py                   # figuras + apresentação
```

## Ligação com os Exercícios 7 e 8

- Hidrostática igual à do código do Ex. 7 (Δ, KB, BM e KM nos dois planos).
- KG pelo `calcular_propriedades()` do Ex. 8: topside = 1,7 × 0,083 t por boe/d a 10 m acima das colunas,
  casco = γe × volume envoltório, risers 4% Δ e amarração 3% Δ no topo das colunas, lastro em hp/2.
  Caso do enunciado: KG = 34,29 m, GM = 4,74 m.
- Casco de menor peso pela mesma otimização SLSQP do Ex. 8 (mesmos limites e restrições):
  Lp = 99,60, bp = hp = bc = 10, hc = 30, T = 27,21 m; KG = 37,54 m, GM = 1,026 m, air gap = 12,79 m.
- A conferência (diferença zero em todas as grandezas) está no slide 4 e em `gerar_apresentacao_ex9.conferencia()`.
