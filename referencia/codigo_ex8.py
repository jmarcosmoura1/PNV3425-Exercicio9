# Cópia de referência do código do Exercício 8 (cálculo e otimização sem alterações;
# a tabela estilizada e a figura 3D do original foram trocadas por print para rodar no terminal).
import numpy as np
import pandas as pd
from scipy.optimize import minimize

# ==========================================
# 1. MOTOR MATEMÁTICO E HIDROSTÁTICO
# ==========================================
def calcular_propriedades(x):
    """Calcula todas as propriedades da plataforma, aderindo ao roteiro PNV3425."""
    Lp, bp, hp, bc, hc, T = x

    # Parâmetros fixos e Dados de Entrada
    BOE = 120000
    Q = BOE / 1000.0 # Vazão em milhares de barris por dia (MBOPD)
    gamma_e = 0.270 # ton/m3
    rho_agua = 1.025 # ton/m3

    # Geometria e Volumes do Casco
    vol_pontoons = 2 * (Lp * bp * hp)
    vol_colunas = 4 * (bc**2 * hc)
    vol_casco = vol_pontoons + vol_colunas

    # 5) Hidrostática: Volume deslocado (Ved)
    ved_pontoons = vol_pontoons
    ved_colunas = 4 * (bc**2 * max(0, T - hp))
    Ved = ved_pontoons + ved_colunas

    # 4) Peso e Deslocamento da Plataforma
    peso_total = Ved * rho_agua # Delta

    # 1) Peso e VCG do Topside
    peso_pl = 0.083 * BOE # 83 kg/BOE convertido para t/BOE
    peso_co = 0.35 * peso_pl # Estrutura do convés
    peso_op = 0.35 * peso_pl # Peso operacional
    peso_topside = peso_pl + peso_co + peso_op
    vcg_topside = hp + hc + 10.0 # 10m acima do topo das colunas

    # 2) Peso e VCG do Casco
    peso_pontoon = vol_pontoons * gamma_e
    peso_coluna = vol_colunas * gamma_e
    peso_casco = peso_pontoon + peso_coluna

    vcg_pontoon = hp / 2.0
    vcg_coluna = hp + (hc / 2.0)
    vcg_casco = ((peso_pontoon * vcg_pontoon) + (peso_coluna * vcg_coluna)) / peso_casco

    # Cargas Externas (Risers e Amarração aplicados no topo das colunas)
    peso_r = 0.04 * peso_total
    peso_a = 0.03 * peso_total
    vcg_r = hp + hc
    vcg_a = hp + hc

    # 3) Peso e VCG do Lastro
    peso_lastro = peso_total - (peso_topside + peso_casco + peso_r + peso_a)
    vcg_lastro = hp / 2.0 # Alocado no centro dos pontoons

    # 4) KG da Plataforma (Média Ponderada)
    momento_peso = (peso_topside * vcg_topside) + \
                   (peso_casco * vcg_casco) + \
                   (peso_r * vcg_r) + \
                   (peso_a * vcg_a) + \
                   (peso_lastro * vcg_lastro)
    KG = momento_peso / peso_total

    # 6) GM da Plataforma
    kb_pontoons = hp / 2.0
    kb_colunas = hp + (max(0, T - hp) / 2.0)
    KB = ((ved_pontoons * kb_pontoons) + (ved_colunas * kb_colunas)) / Ved

    I_coluna_local = (bc * bc**3) / 12.0
    distancia_cg = (Lp - bc) / 2.0
    I_total = 4 * (I_coluna_local + (bc**2 * distancia_cg**2))

    BM = I_total / Ved
    KM = KB + BM
    GM = KM - KG

    # 7 e 8) Airgap e Área de Convés
    airgap = (hp + hc) - T
    area_conves = Lp * Lp
    area_req = 42.246 * Q + 4850.1 # Regressão baseada em MBOPD
    return {
            "Lp (m)": Lp, "bp (m)": bp, "hp (m)": hp, "bc (m)": bc, "hc (m)": hc, "T (m)": T,
            "Peso Topside (t)": peso_topside, "Peso Casco (t)": peso_casco,
            "Peso Risers (t)": peso_r, "Peso Amarração (t)": peso_a, "Peso Lastro (t)": peso_lastro,
            "Peso Plataforma (t)": peso_total, "Volume Deslocado - Ved (m³)": Ved,
            "VCG Topside (m)": vcg_topside, "VCG Casco (m)": vcg_casco, "VCG Risers/Amarração (m)": vcg_r,
            "VCG Lastro (m)": vcg_lastro, "KG Plataforma (m)": KG, "GM (m)": GM, "Airgap (m)": airgap,
            "Área de Convés (m²)": area_conves, "Área Mínima Requerida (m²)": area_req
        }

# ==========================================
# 2. ROTINA DE OTIMIZAÇÃO
# ==========================================
def funcao_objetivo(x):
    return calcular_propriedades(x)["Peso Casco (t)"]

def rest_gm_min(x):
    return calcular_propriedades(x)["GM (m)"] - 1.0

def rest_gm_max(x):
    return 4.0 - calcular_propriedades(x)["GM (m)"]

def rest_airgap(x):
    return calcular_propriedades(x)["Airgap (m)"] - 12.0

def rest_lastro(x):
    return calcular_propriedades(x)["Peso Lastro (t)"] / 10000.0

def rest_area(x):
    props = calcular_propriedades(x)
    return (props["Área de Convés (m²)"] - props["Área Mínima Requerida (m²)"]) / 1000.0

def rest_bc_bp(x):
    Lp, bp, hp, bc, hc, T = x
    return bp - bc

x_inicial = [100.0, 15.0, 15.0, 15, 45.0, 30.0]
bounds = ((70, 150), (10, 25), (10, 25), (10, 25), (30, 60), (20, 40))
restricoes = [
    {'type': 'ineq', 'fun': rest_gm_min}, {'type': 'ineq', 'fun': rest_gm_max},
    {'type': 'ineq', 'fun': rest_airgap}, {'type': 'ineq', 'fun': rest_lastro},
    {'type': 'ineq', 'fun': rest_area}, {'type': 'ineq', 'fun': rest_bc_bp},
]

if __name__ == '__main__':
    resultado = minimize(funcao_objetivo, x0=x_inicial, method='SLSQP', bounds=bounds, constraints=restricoes)
    print("====== STATUS DA OTIMIZAÇÃO ======")
    print(resultado.message, resultado.success, resultado.nit)
    x_otimo = resultado.x if resultado.success else x_inicial
    df = pd.DataFrame({'Original': calcular_propriedades(x_inicial), 'Otimizado': calcular_propriedades(x_otimo)})
    df['Evolução (%)'] = (df['Otimizado'] - df['Original']) / df['Original'] * 100
    pd.set_option('display.width', 200)
    print(df.round(3).to_string())
    print('x_otimo =', list(np.round(x_otimo, 6)))
