# -*- coding: utf-8 -*-
"""
PNV3425 - Projeto de Sistemas Oceânicos
Exercício 9 - Modelo paramétrico: curva GZ, momento de vento e critério de áreas
de uma plataforma semissubmersível com 2 pontoons retangulares e 4 colunas quadradas.

Etapas do modelo (numeradas como no enunciado):
  1) curva GZ de 0° a 50° pelo método de projeções 2D (seções retangulares extrudadas)
  2) ângulo de alagamento φal (fundo do convés toca a água na borda da plataforma)
  3) força do vento em cada parcela de área exposta (DNV-OS-C301 / Código MODU 2009)
  4) centro de resistência lateral z_CLR (centroide da silhueta submersa)
  5) momento de vento sem inclinação HM0 e parcela da face inferior do convés HMud
  6) curva do braço de vento HA(φ) = (HM0 cos φ + HMud sen φ) / (Δ g)
  7) interceptos φ1 e φ2 entre GZ e HA
  8) áreas A e B sob as curvas e razão A/B
  9) verificação do critério de áreas (A ≥ 1,3 B e GZ > 0 até φ2 ou φal)

Sistema de coordenadas: z para cima a partir da quilha (fundo dos pontoons); s é a coordenada
horizontal no plano de inclinação (y na transversal, x na longitudinal), com origem no centro da
plataforma. A inclinação φ abaixa o lado s > 0.

Unidades: m, t, kN, kN·m, graus nas entradas/saídas e radianos nas integrais.

Uso:   python ex9_estabilidade.py           (imprime as tabelas e grava CSVs em ./resultados)
"""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
from pathlib import Path
import numpy as np
import pandas as pd

G = 9.81                 # m/s²
RHO_AR = 1.222           # kg/m³
RHO_AGUA = 1.025         # t/m³
PLANOS = ('Transversal', 'Longitudinal')

# Coeficiente de altura Ch (DNV-OS-C301 Cap. 2 Seç. 1 / Código MODU 2009).
# As cinco primeiras faixas são as do enunciado; as demais completam a tabela do Código MODU
# e só entram se alguma parcela ficar acima de 76 m.
CH_TABELA = [(15.3, 1.00), (30.5, 1.10), (46.0, 1.20), (61.0, 1.30), (76.0, 1.37),
             (91.5, 1.43), (106.5, 1.48), (122.0, 1.52), (137.0, 1.56), (152.5, 1.60),
             (167.5, 1.63), (183.0, 1.67), (198.0, 1.70), (213.5, 1.72), (228.5, 1.75),
             (244.0, 1.77), (256.0, 1.79), (np.inf, 1.80)]


# ======================================================================== dados de entrada
@dataclass(frozen=True)
class Plataforma:
    """Dados de entrada do modelo (nomes do enunciado)."""
    Lp: float = 100.0         # comprimento dos pontoons [m] (também largura do convés)
    bp: float = 15.0          # boca dos pontoons [m]
    hp: float = 15.0          # altura dos pontoons [m]
    bc: float = 15.0          # lado das colunas [m]
    hc: float = 45.0          # altura das colunas [m]
    T: float = 30.0           # calado [m]
    BOE: float = 120_000.0    # produção diária [boe/d]
    gamma_e: float = 0.270    # peso específico estrutural [t/m³ de volume envoltório]
    hd: float = 8.0           # altura do deck box [m]
    hm: float = 15.0          # altura média dos módulos de topside [m]
    KG: float | None = None   # KG imposto [m]; None -> KG do modelo de pesos do Exercício 8
    rho: float = RHO_AGUA     # massa específica da água [t/m³]
    # ---- modelo de pesos do Exercício 8 (codigo_ex8.py, calcular_propriedades)
    c_pl: float = 0.083       # planta de processo [t por boe/d] (83 kg/BOE)
    f_co: float = 0.35        # estrutura do convés = f_co × planta
    f_op: float = 0.35        # peso operacional   = f_op × planta
    dz_top: float = 10.0      # VCG do topside acima do topo das colunas [m]
    f_ris: float = 0.04       # risers   = f_ris × Δ, no topo das colunas
    f_amr: float = 0.03       # amarração = f_amr × Δ, no topo das colunas

    @property
    def a(self) -> float:
        """Air gap: distância da linha d'água ao fundo do convés."""
        return self.hp + self.hc - self.T


CASO_BASE = Plataforma()


# ======================================================================== hidrostática e pesos
def hidrostatica(p: Plataforma) -> dict:
    """Volume, deslocamento, KB, BM e KM na posição adriçada (fórmulas do Exercício 7).

    Distâncias do centro da plataforma ao eixo das colunas: (Lp − bp)/2 na transversal (coluna
    centrada no pontoon) e (Lp − bc)/2 na longitudinal (coluna na extremidade do pontoon)."""
    v_pont = 2 * p.Lp * p.bp * p.hp
    v_col = 4 * p.bc ** 2 * max(0.0, p.T - p.hp)
    vol = v_pont + v_col
    KB = (v_pont * p.hp / 2 + v_col * (p.hp + max(0.0, p.T - p.hp) / 2)) / vol
    dist_T = (p.Lp - p.bp) / 2
    dist_L = (p.Lp - p.bc) / 2
    I_T = 4 * (p.bc ** 4 / 12 + p.bc ** 2 * dist_T ** 2)
    I_L = 4 * (p.bc ** 4 / 12 + p.bc ** 2 * dist_L ** 2)
    return dict(vol=vol, desloc=p.rho * vol, KB=KB, BM_T=I_T / vol, BM_L=I_L / vol,
                KM_T=KB + I_T / vol, KM_L=KB + I_L / vol, Awp=4 * p.bc ** 2)


def valida(p: Plataforma) -> None:
    """Geometria aceita pelo modelo de GZ: a linha d'água corta as colunas e a coluna cabe no pontoon."""
    if not (p.hp < p.T < p.hp + p.hc):
        raise ValueError('O calado precisa cortar as colunas: hp < T < hp + hc.')
    if p.bc > p.bp + 1e-9:
        raise ValueError('A coluna precisa caber no pontoon: bc ≤ bp.')


def pesos(p: Plataforma) -> tuple[pd.DataFrame, float]:
    """Quadro de pesos e KG pelo modelo do Exercício 8 (sem correção de superfície livre).

      - topside = planta (0,083 t por boe/d) + estrutura do convés (35%) + operacional (35%),
        com VCG 10 m acima do topo das colunas;
      - casco = γe × volume envoltório de pontoons e colunas, cada um no seu centroide;
      - risers (4% Δ) e amarração (3% Δ) no topo das colunas;
      - lastro = Δ − demais pesos, no centro dos pontoons (hp/2).
    Se p.KG for informado, ele substitui o KG do quadro."""
    D = hidrostatica(p)['desloc']
    W_pl = p.c_pl * p.BOE
    z_top = p.hp + p.hc + p.dz_top
    z_tc = p.hp + p.hc
    itens = [['Planta de processo', W_pl, z_top],
             ['Estrutura do convés', p.f_co * W_pl, z_top],
             ['Peso operacional', p.f_op * W_pl, z_top],
             ['Pontoons (aço)', p.gamma_e * 2 * p.Lp * p.bp * p.hp, p.hp / 2],
             ['Colunas (aço)', p.gamma_e * 4 * p.bc ** 2 * p.hc, p.hp + p.hc / 2],
             ['Risers', p.f_ris * D, z_tc],
             ['Amarração', p.f_amr * D, z_tc]]
    W_l = D - sum(i[1] for i in itens)
    itens.append(['Lastro', W_l, p.hp / 2])
    tab = pd.DataFrame(itens, columns=['Item', 'Peso [t]', 'KG item [m]'])
    tab['Momento [t·m]'] = tab['Peso [t]'] * tab['KG item [m]']
    KG_modelo = tab['Momento [t·m]'].sum() / D
    return tab, (p.KG if p.KG is not None else KG_modelo)


def lastro(p: Plataforma) -> float:
    """Peso de lastro [t] que fecha o balanço de pesos no calado T."""
    return float(pesos(p)[0]['Peso [t]'].iloc[-1])


def topside(p: Plataforma) -> float:
    """Peso total de topside [t] (planta + estrutura do convés + operacional)."""
    return p.c_pl * p.BOE * (1 + p.f_co + p.f_op)


def peso_casco(p: Plataforma) -> float:
    """Peso estrutural de pontoons + colunas [t]."""
    return p.gamma_e * (2 * p.Lp * p.bp * p.hp + 4 * p.bc ** 2 * p.hc)


# ======================================================================== 1) GZ por projeções 2D
def retangulos(p: Plataforma, plano: str) -> list[tuple[float, float, float, float, float]]:
    """Projeção 2D do casco no plano de inclinação: (s_min, s_max, z_min, z_max, profundidade).

    Cada retângulo é a seção de um elemento prismático; a profundidade é a soma dos comprimentos
    dos elementos que se sobrepõem na projeção (ex.: as duas colunas de um mesmo bordo)."""
    zc0, zc1 = p.hp, p.hp + p.hc
    if plano == 'Transversal':          # plano y-z, eixo de inclinação x (ao longo dos pontoons)
        yc = p.Lp / 2 - p.bp / 2
        return [(-yc - p.bp / 2, -yc + p.bp / 2, 0.0, p.hp, p.Lp),          # pontoon BB
                (yc - p.bp / 2, yc + p.bp / 2, 0.0, p.hp, p.Lp),            # pontoon BE
                (-yc - p.bc / 2, -yc + p.bc / 2, zc0, zc1, 2 * p.bc),       # colunas BB (vante + ré)
                (yc - p.bc / 2, yc + p.bc / 2, zc0, zc1, 2 * p.bc)]         # colunas BE
    if plano == 'Longitudinal':         # plano x-z, eixo de inclinação y
        return [(-p.Lp / 2, p.Lp / 2, 0.0, p.hp, 2 * p.bp),                  # 2 pontoons sobrepostos
                (-p.Lp / 2, -p.Lp / 2 + p.bc, zc0, zc1, 2 * p.bc),          # colunas de ré (BB + BE)
                (p.Lp / 2 - p.bc, p.Lp / 2, zc0, zc1, 2 * p.bc)]            # colunas de vante
    raise ValueError(f'plano inválido: {plano}')


def poligono_submerso(ret, c, s_, d):
    """Vértices (s, z) da parte do retângulo abaixo da linha d'água z cosφ − s senφ = d
    (recorte de Sutherland–Hodgman por um semiplano). c = cos φ, s_ = sen φ."""
    s0, s1, z0, z1 = ret[:4]
    pts = [(s0, z0), (s1, z0), (s1, z1), (s0, z1)]
    dist = [z * c - s * s_ - d for s, z in pts]
    poli = []
    for i in range(4):
        (sa, za), (sb, zb) = pts[i], pts[(i + 1) % 4]
        da, db = dist[i], dist[(i + 1) % 4]
        if da <= 0:
            poli.append((sa, za))
        if da * db < 0:
            t = da / (da - db)
            poli.append((sa + t * (sb - sa), za + t * (zb - za)))
    return poli


def _corta(ret, c, s_, d):
    """Área e momentos estáticos (∫s dA, ∫z dA) da parte submersa do retângulo."""
    poli = poligono_submerso(ret, c, s_, d)
    if len(poli) < 3:
        return 0.0, 0.0, 0.0
    A = Ss = Sz = 0.0
    for i in range(len(poli)):
        (sa, za), (sb, zb) = poli[i], poli[(i + 1) % len(poli)]
        cr = sa * zb - sb * za
        A += cr
        Ss += (sa + sb) * cr
        Sz += (za + zb) * cr
    return A / 2, Ss / 6, Sz / 6


def _submerso(rets, phi, d):
    """Volume e centro de carena (s_B, z_B) para a linha d'água (φ, d)."""
    c, s_ = np.cos(phi), np.sin(phi)
    V = Ms = Mz = 0.0
    for r in rets:
        A, Ss, Sz = _corta(r, c, s_, d)
        V += A * r[4]
        Ms += Ss * r[4]
        Mz += Sz * r[4]
    return V, (Ms / V if V > 0 else 0.0), (Mz / V if V > 0 else 0.0)


def equilibrio(rets, vol, phi, tol=1e-7):
    """Posição d da linha d'água inclinada de φ que mantém o volume deslocado (bisseção)."""
    c, s_ = np.cos(phi), np.sin(phi)
    alt = [z * c - s * s_ for r in rets for s in r[:2] for z in r[2:4]]
    lo, hi = min(alt), max(alt)
    for _ in range(80):
        d = 0.5 * (lo + hi)
        if _submerso(rets, phi, d)[0] < vol:
            lo = d
        else:
            hi = d
        if hi - lo < tol:
            break
    d = 0.5 * (lo + hi)
    _, sB, zB = _submerso(rets, phi, d)
    return d, sB, zB


def curva_gz(p: Plataforma, plano: str, phis_graus, KG: float | None = None) -> pd.DataFrame:
    """GZ(φ) = (s_B − s_G) cos φ + (z_B − KG) sen φ, com s_G = 0, pelo método de projeções 2D."""
    rets = retangulos(p, plano)
    vol = hidrostatica(p)['vol']
    if KG is None:
        KG = pesos(p)[1]
    linhas = []
    for fg in np.atleast_1d(phis_graus):
        f = np.radians(fg)
        d, sB, zB = equilibrio(rets, vol, f)
        gz = sB * np.cos(f) + (zB - KG) * np.sin(f)
        linhas.append((fg, d, sB, zB, gz))
    return pd.DataFrame(linhas, columns=['phi [°]', 'd [m]', 's_B [m]', 'z_B [m]', 'GZ [m]'])


# ======================================================================== 2) ângulo de alagamento
def angulo_alagamento(p: Plataforma, plano: str) -> float:
    """φal [°]: o fundo do convés (z = hp + hc) na borda s = Lp/2 toca a linha d'água inclinada."""
    rets = retangulos(p, plano)
    vol = hidrostatica(p)['vol']
    zd, sd = p.hp + p.hc, p.Lp / 2

    def folga(fg):
        f = np.radians(fg)
        d = equilibrio(rets, vol, f)[0]
        return zd * np.cos(f) - sd * np.sin(f) - d

    lo, hi = 0.0, 89.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        if folga(m) > 0:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


# ======================================================================== 3) a 5) vento
def coef_altura(h: float) -> float:
    """Ch lido na altura h do centroide acima da linha d'água."""
    for h_max, ch in CH_TABELA:
        if h <= h_max:
            return ch
    return CH_TABELA[-1][1]


def z_clr(p: Plataforma, plano: str) -> tuple[float, pd.DataFrame]:
    """Centro de resistência lateral: centroide da silhueta submersa vista na direção do vento."""
    if plano == 'Transversal':
        A_p = p.Lp * p.hp                  # um pontoon de lado (o outro fica atrás na silhueta)
    else:
        A_p = 2 * p.bp * p.hp              # as duas seções dos pontoons
    A_c = 2 * p.bc * (p.T - p.hp)          # duas colunas lado a lado
    tab = pd.DataFrame([['Pontoon(s)', A_p, p.hp / 2], ['Colunas', A_c, p.hp + (p.T - p.hp) / 2]],
                       columns=['Parcela', 'Área [m²]', 'z [m]'])
    return float((tab['Área [m²]'] * tab['z [m]']).sum() / tab['Área [m²]'].sum()), tab


def forcas_vento(p: Plataforma, plano: str, V: float) -> tuple[pd.DataFrame, dict]:
    """Força, braço e momento de cada parcela; HM0, HMud e z_CLR.

    F_i = ½ ρar Cs Ch A_i V²; braço = h_i + T − z_CLR (de z_CLR até o centroide da parcela)."""
    a = p.a
    zc, _ = z_clr(p, plano)
    q = 0.5 * RHO_AR * V ** 2 / 1e3            # pressão dinâmica [kPa = kN/m²]
    parcelas = [('Colunas', 4 * p.bc * a, a / 2, 1.0),
                ('Deck box', p.Lp * p.hd, a + p.hd / 2, 1.0),
                ('Módulos de topside', p.Lp * p.hm, a + p.hd + p.hm / 2, 1.1),
                ('Face inferior do convés (× sen φ)', p.Lp ** 2, a, 1.0)]
    linhas = []
    for nome, A, h, Cs in parcelas:
        Ch = coef_altura(h)
        F = q * Cs * Ch * A
        braco = h + p.T - zc
        linhas.append([nome, A, h, Cs, Ch, F, braco, F * braco])
    tab = pd.DataFrame(linhas, columns=['Parcela', 'Área [m²]', 'h [m]', 'Cs', 'Ch', 'F [kN]',
                                        'Braço [m]', 'Momento [kN·m]'])
    HM0 = tab['Momento [kN·m]'].iloc[:3].sum()
    HMud = tab['Momento [kN·m]'].iloc[3]
    return tab, dict(q=q, z_CLR=zc, HM0=HM0, HMud=HMud, F0=tab['F [kN]'].iloc[:3].sum(),
                     Fud=tab['F [kN]'].iloc[3])


def braco_vento(phis_graus, HM0, HMud, desloc):
    """HA(φ) = (HM0 cos φ + HMud sen φ) / (Δ g)  [m]."""
    f = np.radians(np.asarray(phis_graus, float))
    return (HM0 * np.cos(f) + HMud * np.sin(f)) / (desloc * G)


# ======================================================================== 7) a 9) critério de áreas
def _cruzamentos(phi, y):
    """Ângulos em que y troca de sinal (interpolação linear), com o sentido da troca."""
    out = []
    for i in range(len(phi) - 1):
        if y[i] == 0 and i > 0:
            out.append((phi[i], np.sign(y[i + 1])))
        elif y[i] * y[i + 1] < 0:
            out.append((phi[i] - y[i] * (phi[i + 1] - phi[i]) / (y[i + 1] - y[i]), np.sign(y[i + 1])))
    return out


def _integra(phi_g, y, ate):
    """∫ y dφ de 0 até 'ate' [°], com φ em radianos (trapézios)."""
    sel = phi_g <= ate + 1e-12
    x = np.append(phi_g[sel], ate) if phi_g[sel][-1] < ate else phi_g[sel]
    yy = np.append(y[sel], np.interp(ate, phi_g, y)) if phi_g[sel][-1] < ate else y[sel]
    return float(np.trapezoid(yy, np.radians(x)))


def analise(p: Plataforma, plano: str, V: float, passo: float = 0.25, phi_max: float = 50.0,
            limite: str = 'enunciado', gz: pd.DataFrame | None = None, phi_al: float | None = None) -> dict:
    """Análise completa em um plano e uma velocidade de vento.

    limite = 'enunciado' : A e B integradas de 0 a φal (como no enunciado)
    limite = 'MODU'      : integradas até o menor entre φ2 e φal (Código MODU 2009, 3.2.3)
    gz e phi_al podem ser passados prontos para reaproveitar o cálculo entre velocidades."""
    hs = hidrostatica(p)
    _, KG = pesos(p)
    if phi_al is None:
        phi_al = angulo_alagamento(p, plano)
    if gz is None:
        phis = np.unique(np.concatenate([np.arange(0.0, phi_max + 1e-9, passo), [phi_al]]))
        phis = phis[phis <= phi_max + 1e-9]
        gz = curva_gz(p, plano, phis, KG)
    phi = gz['phi [°]'].values
    GZ = gz['GZ [m]'].values
    tab_v, v = forcas_vento(p, plano, V)
    HA = braco_vento(phi, v['HM0'], v['HMud'], hs['desloc'])

    cr = _cruzamentos(phi, GZ - HA)
    phi1 = next((x for x, sg in cr if sg > 0), None)                         # GZ passa a superar HA
    phi2 = next((x for x, sg in cr if sg < 0 and phi1 is not None and x > phi1), None)  # GZ volta abaixo

    lim = phi_al if (limite == 'enunciado' or phi2 is None) else min(phi2, phi_al)
    A = _integra(phi, GZ, lim)
    B = _integra(phi, HA, lim)
    # GZ > 0 de 0° até φ2 (se φ2 < φal) ou até φal
    phi_chk = phi2 if (phi2 is not None and phi2 < phi_al) else phi_al
    sel = (phi > 0) & (phi <= phi_chk + 1e-9)
    gz_pos = bool(np.all(GZ[sel] > 0))
    crit_area = A >= 1.3 * B
    return dict(plano=plano, V=V, KG=KG, desloc=hs['desloc'], GM=(hs['KM_T'] if plano == 'Transversal'
                                                                  else hs['KM_L']) - KG,
                phi=phi, GZ=GZ, HA=HA, gz=gz, tab_vento=tab_v, phi_al=phi_al, phi1=phi1, phi2=phi2,
                lim=lim, A=A, B=B, AB=A / B, crit_area=crit_area, gz_pos=gz_pos, phi_chk=phi_chk,
                atende=bool(crit_area and gz_pos), **v)


def avalia(p: Plataforma, velocidades=(51.5, 36.0), passo=0.25, limite='enunciado') -> dict:
    """Roda os dois planos e todas as velocidades; reaproveita a curva GZ entre velocidades."""
    valida(p)
    res = {}
    KG = pesos(p)[1]
    for plano in PLANOS:
        phi_al = angulo_alagamento(p, plano)
        phis = np.unique(np.concatenate([np.arange(0.0, 50.0 + 1e-9, passo), [phi_al]]))
        gz = curva_gz(p, plano, phis[phis <= 50.0 + 1e-9], KG)
        for V in velocidades:
            res[(plano, V)] = analise(p, plano, V, passo, limite=limite, gz=gz, phi_al=phi_al)
    return res


def resumo(res: dict) -> pd.DataFrame:
    """Tabela com φ1, φ2, φal, A, B, A/B e o veredito, uma linha por plano e velocidade."""
    f = lambda x: np.nan if x is None else x
    linhas = [[r['plano'], r['V'], r['V'] / 0.5144, f(r['phi1']), f(r['phi2']), r['phi_al'], r['A'], r['B'],
               r['AB'], 'sim' if r['crit_area'] else 'não', 'sim' if r['gz_pos'] else 'não',
               'ATENDE' if r['atende'] else 'NÃO ATENDE'] for r in res.values()]
    return pd.DataFrame(linhas, columns=['Plano', 'V [m/s]', 'V [nós]', 'φ1 [°]', 'φ2 [°]', 'φal [°]',
                                         'A [m·rad]', 'B [m·rad]', 'A/B', 'A ≥ 1,3B', 'GZ > 0', 'Critério'])


# ======================================================================== solução de menor peso (Ex. 8)
VARIAVEIS_EX8 = ('Lp', 'bp', 'hp', 'bc', 'hc', 'T')
LIMITES_EX8 = ((70, 150), (10, 25), (10, 25), (10, 25), (30, 60), (20, 40))


def area_conves_requerida(p: Plataforma) -> float:
    """Área mínima de convés [m²] do Exercício 8: 42,246 Q + 4850,1, com Q em mil boe/d."""
    return 42.246 * p.BOE / 1000.0 + 4850.1


def menor_peso_casco(base: Plataforma = CASO_BASE, GM_min: float = 1.0, GM_max: float = 4.0,
                     airgap_min: float = 12.0, limites=LIMITES_EX8, gm_plano: str = 'Ex8'):
    """Otimização do Exercício 8 (SLSQP): minimiza o peso do casco variando Lp, bp, hp, bc, hc e T.

    Restrições (iguais às de codigo_ex8.py): GM_min ≤ GM ≤ GM_max, air gap ≥ airgap_min, lastro ≥ 0,
    Lp² ≥ área de convés requerida e bc ≤ bp. Ponto de partida: as dimensões de 'base'.

    gm_plano = 'Ex8' usa o GM do código do Exercício 8 (distância (Lp − bc)/2, isto é, o GM longitudinal);
    gm_plano = 'min' usa o menor entre GM_T e GM_L (correção sugerida; só muda o resultado se bp > bc).
    Retorna (Plataforma ótima, resultado do scipy). Se a otimização falhar, devolve 'base' (como no Ex. 8)."""
    from scipy.optimize import minimize

    def plat(x):
        return replace(base, **dict(zip(VARIAVEIS_EX8, map(float, x))), KG=None)

    def gm(x):
        q = plat(x)
        h = hidrostatica(q)
        KG = pesos(q)[1]
        return (h['KM_L'] - KG) if gm_plano == 'Ex8' else (min(h['KM_T'], h['KM_L']) - KG)

    restr = [{'type': 'ineq', 'fun': lambda x: gm(x) - GM_min},
             {'type': 'ineq', 'fun': lambda x: GM_max - gm(x)},
             {'type': 'ineq', 'fun': lambda x: plat(x).a - airgap_min},
             {'type': 'ineq', 'fun': lambda x: lastro(plat(x)) / 1e4},
             {'type': 'ineq', 'fun': lambda x: (x[0] ** 2 - area_conves_requerida(base)) / 1e3},
             {'type': 'ineq', 'fun': lambda x: x[1] - x[3]}]
    x0 = [getattr(base, v) for v in VARIAVEIS_EX8]
    r = minimize(lambda x: peso_casco(plat(x)), x0=x0, method='SLSQP', bounds=limites, constraints=restr)
    return (plat(r.x) if r.success else replace(base, KG=None)), r


def comparativo_ex8(orig: Plataforma, otim: Plataforma) -> pd.DataFrame:
    """Tabela comparativa no formato do Exercício 8 (original × otimizado)."""
    def props(p):
        h = hidrostatica(p)
        tab, KG = pesos(p)
        w = dict(zip(tab['Item'], tab['Peso [t]']))
        return {'Lp (m)': p.Lp, 'bp (m)': p.bp, 'hp (m)': p.hp, 'bc (m)': p.bc, 'hc (m)': p.hc, 'T (m)': p.T,
                'Peso Topside (t)': topside(p), 'Peso Casco (t)': peso_casco(p), 'Peso Risers (t)': w['Risers'],
                'Peso Amarração (t)': w['Amarração'], 'Peso Lastro (t)': w['Lastro'], 'Δ (t)': h['desloc'],
                'KG (m)': KG, 'GM_T (m)': h['KM_T'] - KG, 'GM_L (m)': h['KM_L'] - KG, 'Air gap (m)': p.a,
                'Área de convés (m²)': p.Lp ** 2}
    df = pd.DataFrame({'Original': props(orig), 'Otimizado': props(otim)})
    df['Evolução (%)'] = (df['Otimizado'] / df['Original'] - 1) * 100
    return df


# ======================================================================== execução direta
def _fmt(df):
    return df.to_string(index=False, float_format=lambda x: f'{x:,.3f}')


if __name__ == '__main__':
    pd.set_option('display.width', 200)
    saida = Path(__file__).with_name('resultados')
    saida.mkdir(exist_ok=True)
    leve, otim = menor_peso_casco()
    print('Otimização do Exercício 8:', otim.message, '\n')
    print(comparativo_ex8(CASO_BASE, leve).to_string(float_format=lambda x: f'{x:,.3f}'))
    casos = {'Caso base (Ex. 9)': CASO_BASE, 'Menor peso de casco (Ex. 8)': leve}
    for nome, p in casos.items():
        tab_p, KG = pesos(p)
        h = hidrostatica(p)
        print('=' * 100, f'\n{nome}:', {k: round(v, 2) if isinstance(v, float) else v for k, v in asdict(p).items()})
        print(f'Δ = {h["desloc"]:,.0f} t   KB = {h["KB"]:.2f} m   KM_T = {h["KM_T"]:.2f} m   '
              f'KG = {KG:.2f} m   GM = {h["KM_T"] - KG:.2f} m   air gap = {p.a:.1f} m   '
              f'peso do casco = {peso_casco(p):,.0f} t')
        print(_fmt(tab_p))
        res = avalia(p)
        for plano in PLANOS:
            r = res[(plano, 51.5)]
            print(f'\n--- {plano}: z_CLR = {r["z_CLR"]:.2f} m, φal = {r["phi_al"]:.2f}°')
            for V in (51.5, 36.0):
                rv = res[(plano, V)]
                print(f'V = {V} m/s: HM0 = {rv["HM0"]:,.0f} kN·m, HMud = {rv["HMud"]:,.0f} kN·m')
                print(_fmt(rv['tab_vento']))
        tab_r = resumo(res)
        print('\n' + _fmt(tab_r))
        tag = 'base' if 'base' in nome else 'leve'
        tab_r.to_csv(saida / f'ex9_resumo_{tag}.csv', sep=';', decimal=',', index=False, encoding='utf-8-sig')
        for (plano, V), r in res.items():
            r['tab_vento'].to_csv(saida / f'ex9_vento_{tag}_{plano.lower()}_{V:g}.csv', sep=';', decimal=',',
                                  index=False, encoding='utf-8-sig')
            df = r['gz'].assign(**{'HA [m]': r['HA']})
            df.to_csv(saida / f'ex9_gz_ha_{tag}_{plano.lower()}_{V:g}.csv', sep=';', decimal=',', index=False,
                      encoding='utf-8-sig')
