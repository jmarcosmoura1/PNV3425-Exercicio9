import numpy as np
import matplotlib.pyplot as plt

def calcular_hidrostatica(Lp, bp, hp, bc, hc, T, rho=1.025):
    # 1. Volume (∇) e Deslocamento (Δ)
    vol_pontoons = 2 * (Lp * bp * hp)
    vol_colunas = 4 * ((bc**2) * (T - hp)) if T > hp else 0
    Vol_total = vol_pontoons + vol_colunas
    Desloc = Vol_total * rho

    # 2. Centro de Carena Vertical (KB)
    kb_pontoons = hp / 2.0
    kb_colunas = hp + ((T - hp) / 2.0)
    momento_vertical = (vol_pontoons * kb_pontoons) + (vol_colunas * kb_colunas)
    KB = momento_vertical / Vol_total

    # 3. Inércias e Raios Metacêntricos (BM)
    dist_L = (Lp - bc) / 2.0  # Distância longitudinal do centro à coluna
    dist_T = (Lp - bp) / 2.0  # Distância transversal do centro à coluna

    area_coluna = bc**2
    inercia_propria_coluna = (bc * bc**3) / 12.0

    inercia_L = 4 * (inercia_propria_coluna + area_coluna * (dist_L**2))
    inercia_T = 4 * (inercia_propria_coluna + area_coluna * (dist_T**2))

    BM_L = inercia_L / Vol_total
    BM_T = inercia_T / Vol_total

    # 4. Alturas Metacêntricas (KM)
    KM_L = KB + BM_L
    KM_T = KB + BM_T

    return {
        "T [m]": T,
        "Vol [m3]": Vol_total,
        "Desl [t]": Desloc,
        "KB [m]": KB,
        "BM_T [m]": BM_T,
        "BM_L [m]": BM_L,
        "KM_T [m]": KM_T,
        "KM_L [m]": KM_L
    }

# Parâmetros de entrada do Exercício 7
Lp = 100.0
bp = 15.0
hp = 15.0
bc = 15.0
hc = 45.0
T_projeto = 30.0

# ---------------------------------------------------------
# A. MATRIZ DE RESULTADOS (Variação de calado)
# ---------------------------------------------------------
T_matriz = np.arange(15.0, 65.0, 5.0)
resultados_matriz = [calcular_hidrostatica(Lp, bp, hp, bc, hc, T) for T in T_matriz]

if __name__ == '__main__':
    print(f"{'T [m]':<7} | {'Vol [m3]':<10} | {'Desl [t]':<10} | {'KB [m]':<8} | {'BM_T [m]':<10} | {'BM_L [m]':<10} | {'KM_T [m]':<10} | {'KM_L [m]':<10}")
    print("-" * 95)
    for r in resultados_matriz:
        print(f"{r['T [m]']:<7.1f} | {r['Vol [m3]']:<10.1f} | {r['Desl [t]']:<10.1f} | {r['KB [m]']:<8.2f} | {r['BM_T [m]']:<10.2f} | {r['BM_L [m]']:<10.2f} | {r['KM_T [m]']:<10.2f} | {r['KM_L [m]']:<10.2f}")
# (os gráficos do código original foram omitidos nesta cópia de referência)
