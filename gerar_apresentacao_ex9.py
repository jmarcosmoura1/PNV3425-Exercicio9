# -*- coding: utf-8 -*-
"""
PNV3425 - Exercício 9: gera as figuras (pasta figuras/) e a apresentação ex9_apresentacao.pptx
a partir do modelo em ex9_estabilidade.py (KG e casco de menor peso dos Exercícios 7 e 8).

Requisitos:  pip install numpy pandas scipy matplotlib python-pptx
Uso:         python gerar_apresentacao_ex9.py

As figuras são geradas no tamanho exato em que entram no slide (polegadas) a 250 dpi, com a fonte
Carlito (métrica igual à Calibri usada nos slides); assim o texto dos gráficos tem o mesmo corpo do texto
dos slides e não é reescalado.
"""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Polygon, Rectangle
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

import ex9_estabilidade as ex9

PASTA = Path(__file__).parent
FIG = PASTA / 'figuras'
FIG.mkdir(exist_ok=True)
DPI = 250
FONTE = 'Calibri'

# ---------------------------------------------------------------- fonte das figuras
for f in list((PASTA.parent / '.tools' / 'fonts').glob('*.ttf')) + list((PASTA / 'fontes').glob('*.ttf')):
    font_manager.fontManager.addfont(str(f))
_nomes = {f.name for f in font_manager.fontManager.ttflist}
FONTE_FIG = next((n for n in ('Calibri', 'Carlito') if n in _nomes), 'DejaVu Sans')

HEX = dict(azul='#0B2E40', gz='#1F6FA8', ha1='#E8702A', ha2='#7A4EAB', leve='#7F8C8D', al='#C62828',
           agua='#D6E9F0', deck='#9AA5AB', mod='#F2B880', pont='#264D73', col='#3AA99F', cinza='#556066')
plt.rcParams.update({'font.family': FONTE_FIG, 'font.size': 13, 'axes.titlesize': 14, 'axes.labelsize': 13,
                     'legend.fontsize': 11.5, 'xtick.labelsize': 12, 'ytick.labelsize': 12, 'axes.grid': True,
                     'grid.color': '#E3E8EB', 'axes.spines.top': False, 'axes.spines.right': False,
                     'axes.edgecolor': '#8A969C', 'axes.titleweight': 'bold', 'savefig.dpi': DPI,
                     'legend.frameon': True, 'legend.framealpha': 0.92, 'legend.edgecolor': '#D0D7DB'})


def rgb(h):
    return RGBColor.from_string(h.lstrip('#'))


def br(x, dec=0):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return '—'
    if round(x, dec) == 0:
        x = 0.0
    return f'{x:,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


# ======================================================================== cálculos
sys.path.insert(0, str(PASTA / 'referencia'))
BASE = ex9.CASO_BASE
LEVE, OTIM = ex9.menor_peso_casco(BASE)
VEL = (51.5, 36.0)
RES = {'base': ex9.avalia(BASE, VEL), 'leve': ex9.avalia(LEVE, VEL)}
CASOS = {'base': BASE, 'leve': LEVE}
HB, HL = ex9.hidrostatica(BASE), ex9.hidrostatica(LEVE)
(TB, KGB), (TL, KGL) = ex9.pesos(BASE), ex9.pesos(LEVE)


def conferencia():
    """Compara o modelo do Ex. 9 com os códigos de referência dos Exercícios 7 e 8."""
    try:
        import codigo_ex7 as e7
        import codigo_ex8 as e8
    except ImportError:
        return None
    linhas = []
    for nome, p in (('Original', BASE), ('Otimizado', LEVE)):
        x = [getattr(p, v) for v in ex9.VARIAVEIS_EX8]
        r7 = e7.calcular_hidrostatica(*x)
        r8 = e8.calcular_propriedades(x)
        h = ex9.hidrostatica(p)
        KG = ex9.pesos(p)[1]
        for g, a, b, d in (('Δ [t]', r7['Desl [t]'], h['desloc'], 0), ('KB [m]', r7['KB [m]'], h['KB'], 2),
                           ('KM_T [m]', r7['KM_T [m]'], h['KM_T'], 2), ('KG [m]', r8['KG Plataforma (m)'], KG, 2),
                           ('GM [m]', r8['GM (m)'], h['KM_L'] - KG, 3),
                           ('Lastro [t]', r8['Peso Lastro (t)'], ex9.lastro(p), 0)):
            linhas.append([nome, g, br(a, d), br(b, d), f'{abs(a - b):.1e}'])
    return pd.DataFrame(linhas, columns=['Casco', 'Grandeza', 'Ex. 7 / Ex. 8', 'Modelo Ex. 9', '|dif.|'])


# ======================================================================== figuras
def salva(fig, nome):
    fig.savefig(FIG / nome, dpi=DPI)
    plt.close(fig)


def desenha_secao(ax, p, plano, fg, rotulo_gz=True):
    """Projeção 2D inclinada: retângulos do casco, volume submerso, B, G e GZ."""
    f = np.radians(fg)
    cs, sn = np.cos(f), np.sin(f)
    rets = ex9.retangulos(p, plano)
    d, sB, zB = ex9.equilibrio(rets, ex9.hidrostatica(p)['vol'], f)
    KG = ex9.pesos(p)[1]

    def terra(s, z):
        s, z = np.asarray(s, float), np.asarray(z, float)
        return s * cs + z * sn, z * cs - s * sn - d

    W = p.Lp * 0.82
    ax.add_patch(Rectangle((-W, -p.T - 30), 2 * W, p.T + 30, color=HEX['agua'], zorder=0))
    zd = p.hp + p.hc
    for z0, z1, cor in ((zd, zd + p.hd, HEX['deck']), (zd + p.hd, zd + p.hd + p.hm, HEX['mod'])):
        X, Z = terra([-p.Lp / 2, p.Lp / 2, p.Lp / 2, -p.Lp / 2], [z0, z0, z1, z1])
        ax.add_patch(Polygon(np.c_[X, Z], fc=cor, ec=HEX['azul'], lw=0.8, zorder=2))
    for r in rets:
        X, Z = terra([r[0], r[1], r[1], r[0]], [r[2], r[2], r[3], r[3]])
        ax.add_patch(Polygon(np.c_[X, Z], fc='white', ec=HEX['azul'], lw=1.2, zorder=2))
        poli = ex9.poligono_submerso(r, cs, sn, d)
        if len(poli) >= 3:
            ps = np.array(poli)
            X, Z = terra(ps[:, 0], ps[:, 1])
            ax.add_patch(Polygon(np.c_[X, Z], fc=HEX['gz'], alpha=0.55, lw=0, zorder=3))
    ax.axhline(0, color=HEX['gz'], ls='--', lw=1)
    XB, ZB = terra(sB, zB)
    XG, ZG = terra(0.0, KG)
    ax.plot([XB, XB], [ZB, ZB + 50], color=HEX['gz'], lw=1, zorder=4)
    ax.plot([XG, XG], [ZG, ZG - 50], color=HEX['azul'], lw=1, zorder=4)
    ax.plot(XB, ZB, 'o', color=HEX['gz'], ms=7, zorder=5)
    ax.plot(XG, ZG, 'D', color=HEX['azul'], ms=6, zorder=5)
    ax.text(XB + 2, ZB - 6, 'B', color=HEX['gz'], fontweight='bold', fontsize=12, zorder=6)
    ax.text(XG - 7, ZG + 2.5, 'G', color=HEX['azul'], fontweight='bold', fontsize=12, zorder=6)
    if fg > 0 and rotulo_gz:
        ax.annotate('', xy=(XB, ZG), xytext=(XG, ZG), arrowprops=dict(arrowstyle='->', color=HEX['al'], lw=2), zorder=6)
        ax.text(max(XB, XG) + 3, ZG + 5, f'GZ = {br(XB - XG, 2)} m', color=HEX['al'], fontsize=11.5, zorder=6,
                bbox=dict(fc='white', ec='none', alpha=0.8, pad=1))
    Xe, Ze = terra(p.Lp / 2, zd)
    ax.plot(Xe, Ze, 'v', color=HEX['al'], ms=8, zorder=6)
    ax.set_xlim(-W, W)
    ax.set_ylim(-p.T - 12, zd + p.hd + p.hm - p.T + 14)
    ax.set_aspect('equal')
    ax.grid(False)
    ax.tick_params(labelsize=10)


def fig_secoes():
    fig, axs = plt.subplots(2, 3, figsize=(8.6, 5.4))
    for i, plano in enumerate(ex9.PLANOS):
        fal = RES['base'][(plano, VEL[0])]['phi_al']
        for j, fg in enumerate([0.0, 15.0, fal]):
            desenha_secao(axs[i, j], BASE, plano, fg)
            t = f'φ = φal = {br(fg, 2)}°' if j == 2 else f'φ = {br(fg, 0)}°'
            axs[i, j].set_title(f'{plano} · {t}', fontsize=12)
    fig.tight_layout(pad=0.4, h_pad=0.6, w_pad=0.4)
    salva(fig, 'secoes_2d.png')

    fig, axs = plt.subplots(1, 2, figsize=(5.6, 2.55))
    fal = RES['leve'][('Transversal', VEL[0])]['phi_al']
    for ax, fg in zip(axs, [0.0, fal]):
        desenha_secao(ax, LEVE, 'Transversal', fg, rotulo_gz=False)
        ax.set_title(f'φ = {br(fg, 1)}°' + (' = φal' if fg else ''), fontsize=12)
    fig.tight_layout(pad=0.3)
    salva(fig, 'secoes_leve.png')


def fig_gz_planos():
    fig, ax = plt.subplots(figsize=(8.0, 5.3))
    KM_GM = HB['KM_T'] - KGB
    for plano, ls in zip(ex9.PLANOS, ['-', '--']):
        r = RES['base'][(plano, VEL[0])]
        val = r['phi'] <= r['phi_al'] + 1e-9
        ax.plot(r['phi'][val], r['GZ'][val], ls, color=HEX['gz'], lw=2.8, label=f'GZ {plano.lower()}')
        ax.plot(r['phi'][~val], r['GZ'][~val], ls, color=HEX['gz'], lw=1.4, alpha=0.45)
        ax.axvline(r['phi_al'], color=HEX['al'], ls=ls, lw=1.2)
        ax.text(r['phi_al'] + 0.5, 0.35 if plano == 'Transversal' else 1.05,
                f'φal {plano[:5].lower()}. = {br(r["phi_al"], 1)}°', color=HEX['al'], fontsize=11.5)
    f = np.radians(np.arange(0, 50.1, 0.5))
    ax.plot(np.degrees(f), np.sin(f) * (KM_GM + HB['BM_T'] / 2 * np.tan(f) ** 2), ':', color='#555', lw=1.8,
            label='costado vertical: sen φ (GM + BM tan²φ / 2)')
    ax.plot(np.degrees(f), KM_GM * np.sin(f), '-.', color='#9AA5AB', lw=1.5, label='GM sen φ')
    ax.set(xlim=(0, 50), ylim=(0, 9), xlabel='ângulo de inclinação φ [°]', ylabel='GZ [m]')
    ax.legend(loc='upper left')
    ax.text(49.5, 8.7, 'traço claro: acima de φal (fora da validade)', ha='right', fontsize=10.5, color=HEX['cinza'])
    fig.tight_layout()
    salva(fig, 'gz_planos.png')


def fig_gz_ha(caso, plano):
    fig, ax = plt.subplots(figsize=(8.3, 5.3))
    r1, r2 = RES[caso][(plano, VEL[0])], RES[caso][(plano, VEL[1])]
    phi, GZ = r1['phi'], r1['GZ']
    fal = r1['phi_al']
    val = phi <= fal + 1e-9
    ax.fill_between(phi[val], 0, GZ[val], color=HEX['gz'], alpha=0.13, lw=0)
    ax.fill_between(phi[val], 0, r1['HA'][val], color=HEX['ha1'], alpha=0.22, lw=0)
    ax.plot(phi[val], GZ[val], color=HEX['gz'], lw=2.8, label='GZ')
    ax.plot(phi[phi >= phi[val][-1]], GZ[phi >= phi[val][-1]], ':', color=HEX['gz'], lw=2,
            label='GZ acima de φal (fora da validade)')
    for r, cor in ((r1, HEX['ha1']), (r2, HEX['ha2'])):
        ax.plot(phi, r['HA'], color=cor, lw=2.4, label=f'HA – {br(r["V"], 1)} m/s  (A/B = {br(r["AB"], 2)})')
        for nome, x, dy in (('φ1', r['phi1'], -18), ('φ2', r['phi2'], 8)):
            if x is not None:
                y = np.interp(x, phi, GZ)
                ax.plot(x, y, 'x', color='black', ms=9, mew=2.2, zorder=5)
                ax.annotate(f'{nome} = {br(x, 1)}°', (x, y), textcoords='offset points', xytext=(7, dy), fontsize=11.5,
                            bbox=dict(fc='white', ec='none', alpha=0.85, pad=1))
    ax.axvline(fal, color=HEX['al'], ls='--', lw=1.6)
    ymax = max(GZ.max(), r1['HA'].max()) * 1.08
    ax.set(xlim=(0, 50), ylim=(0, ymax), xlabel='ângulo de inclinação φ [°]', ylabel='braço [m]')
    ax.text(fal + 0.6, ymax * (0.94 if caso == 'base' else 0.84), f'φal = {br(fal, 2)}°', color=HEX['al'],
            fontsize=12.5, fontweight='bold', zorder=12, bbox=dict(fc='white', ec='none', alpha=0.85, pad=1))
    if caso == 'base':      # GZ baixo à esquerda: legenda no canto superior esquerdo, abaixo do quadro de áreas
        leg = ax.legend(loc='upper left', bbox_to_anchor=(0.005, 0.905))
    else:                   # GZ pequeno e HA alto: legenda embaixo à direita, onde não há curvas
        leg = ax.legend(loc='lower right', bbox_to_anchor=(0.995, 0.02))
    leg.set_zorder(10)
    ax.text(0.012, 0.975, f'A = {br(r1["A"], 3)} m·rad   ·   B({br(VEL[0], 1)} m/s) = {br(r1["B"], 3)} m·rad',
            transform=ax.transAxes, fontsize=12, va='top', color=HEX['azul'], zorder=11,
            bbox=dict(fc='white', ec='#D0D7DB', pad=4))
    fig.tight_layout()
    salva(fig, f'gz_ha_{caso}_{plano.lower()}.png')


def fig_comparacao():
    fig, axs = plt.subplots(1, 2, figsize=(7.3, 3.2), sharey=True)
    for ax, plano in zip(axs, ex9.PLANOS):
        for caso, cor, nome in (('base', HEX['gz'], 'enunciado'), ('leve', HEX['ha1'], 'menor peso')):
            r = RES[caso][(plano, VEL[0])]
            val = r['phi'] <= r['phi_al'] + 1e-9
            ax.plot(r['phi'][val], r['GZ'][val], color=cor, lw=2.4, label=f'GZ {nome}')
            ax.plot(r['phi'], r['HA'], '--', color=cor, lw=1.6, label=f'HA 51,5 m/s {nome}')
            ax.axvline(r['phi_al'], color=cor, ls=':', lw=1.2)
        ax.set_title(plano, fontsize=12)
        ax.set(xlim=(0, 35), xlabel='φ [°]')
        ax.tick_params(labelsize=10.5)
    axs[0].set(ylim=(0, 9), ylabel='braço [m]')
    axs[0].legend(fontsize=9.5, loc='upper left')
    fig.tight_layout(pad=0.4)
    salva(fig, 'comparacao_base_leve.png')


def fig_parcelas():
    p = BASE
    fig, ax = plt.subplots(figsize=(5.4, 4.4))
    a, T = p.a, p.T
    ax.add_patch(Rectangle((-58, -T - 4), 116, T + 4, color=HEX['agua'], zorder=0))
    ax.add_patch(Rectangle((-50, -T), 100, p.hp, fc=HEX['pont'], zorder=2))
    for x0 in (-50, 50 - p.bc):
        ax.add_patch(Rectangle((x0, -T + p.hp), p.bc, p.hc, fc=HEX['col'], zorder=2))
    ax.add_patch(Rectangle((-50, a), 100, p.hd, fc=HEX['deck'], zorder=2))
    ax.add_patch(Rectangle((-50, a + p.hd), 100, p.hm, fc='#F2A541', zorder=2))
    ax.axhline(0, color=HEX['gz'], ls='--', lw=1)
    r = RES['base'][('Transversal', VEL[0])]
    ax.plot(-28, r['z_CLR'] - T, 'o', color='#F2A541', mec='k', ms=9, zorder=3)
    ax.text(-24, r['z_CLR'] - T, 'CLR', color='white', fontsize=11, zorder=3, va='center', fontweight='bold')
    for nome, hh in zip(['colunas', 'deck box', 'módulos'], r['tab_vento']['h [m]'].iloc[:3]):
        ax.annotate('', xy=(-51, hh), xytext=(-70, hh), arrowprops=dict(arrowstyle='->', color=HEX['al'], lw=2))
        ax.text(53, hh, f'{nome}\nh = {br(hh, 1)} m', va='center', fontsize=10.5, linespacing=1.0)
    ax.annotate('', xy=(0, a), xytext=(0, 0), arrowprops=dict(arrowstyle='<->', color='k', lw=1))
    ax.text(2, a / 2, f'a = {br(a, 0)} m', va='center', fontsize=11)
    ax.text(-56, -3, "LA", color=HEX['gz'], fontsize=10, va='top')
    ax.set(xlim=(-72, 90), ylim=(-T - 4, a + p.hd + p.hm + 4), ylabel='altura acima da linha d\'água [m]')
    ax.set_aspect('equal')
    ax.grid(False)
    ax.set_xticks([])
    ax.spines['bottom'].set_visible(False)
    fig.tight_layout(pad=0.3)
    salva(fig, 'parcelas_vento.png')


def figuras():
    fig_secoes()
    fig_gz_planos()
    for caso in CASOS:
        for plano in ex9.PLANOS:
            fig_gz_ha(caso, plano)
    fig_comparacao()
    fig_parcelas()


# ======================================================================== apresentação
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
VERDE, VERMELHO = rgb('#2E7D32'), rgb('#C62828')
DEST = {'ATENDE': VERDE, 'NÃO ATENDE': VERMELHO, 'sim': VERDE, 'não': VERMELHO}
N_SLIDE = [0]


def run_fmt(run, tam, cor=None, bold=False, italic=False):
    run.font.name = FONTE
    run.font.size = Pt(tam)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = cor or rgb(HEX['azul'])


def caixa(s, x, y, w, h, fill=None, line=None, forma=MSO_SHAPE.RECTANGLE):
    sh = s.shapes.add_shape(forma, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill:
        sh.fill.solid()
        sh.fill.fore_color.rgb = rgb(fill)
    else:
        sh.fill.background()
    if line:
        sh.line.color.rgb = rgb(line)
        sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def slide(titulo, sub=None, secao=None):
    s = prs.slides.add_slide(BLANK)
    N_SLIDE[0] += 1
    caixa(s, 0, 0, 0.18, 7.5, fill=HEX['azul'])
    tf = s.shapes.add_textbox(Inches(0.55), Inches(0.28), Inches(12.2), Inches(0.75)).text_frame
    tf.word_wrap = True
    run_fmt(tf.paragraphs[0].add_run(), 28, bold=True).__class__
    tf.paragraphs[0].runs[0].text = titulo
    if sub:
        p = tf.add_paragraph()
        r = p.add_run()
        r.text = sub
        run_fmt(r, 15, rgb(HEX['cinza']))
    caixa(s, 0.55, 1.2, 1.4, 0.06, fill=HEX['ha1'])
    rod = s.shapes.add_textbox(Inches(0.55), Inches(7.02), Inches(10), Inches(0.3)).text_frame
    r = rod.paragraphs[0].add_run()
    r.text = 'PNV3425 – Projeto de Sistemas Oceânicos · Exercício 9' + (f' · {secao}' if secao else '')
    run_fmt(r, 10.5, rgb('#8A969C'))
    num = s.shapes.add_textbox(Inches(12.2), Inches(7.02), Inches(0.6), Inches(0.3)).text_frame
    num.paragraphs[0].alignment = PP_ALIGN.RIGHT
    r = num.paragraphs[0].add_run()
    r.text = str(N_SLIDE[0])
    run_fmt(r, 10.5, rgb('#8A969C'), bold=True)
    return s


def texto(s, linhas, x, y, w, h, tam=16, espaco=8):
    """Lista com marcadores; '  ' no início = subnível; '**' no início = parágrafo em negrito sem marcador."""
    tf = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)).text_frame
    tf.word_wrap = True
    for i, l in enumerate(linhas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(espaco)
        if l.startswith('**'):
            r = p.add_run()
            r.text = l[2:]
            run_fmt(r, tam, bold=True)
            continue
        sub = l.startswith('  ')
        r = p.add_run()
        r.text = ('–\u00a0\u00a0' if sub else '•\u00a0\u00a0') + l.strip()
        run_fmt(r, tam - 1.5 if sub else tam, rgb('#2B3A42'))
        # recuo deslocado: as linhas quebradas alinham com o início do texto, não com o marcador
        pPr = p._p.get_or_add_pPr()
        pPr.set('marL', str(int(Inches(0.62 if sub else 0.22))))
        pPr.set('indent', str(int(-Inches(0.2 if sub else 0.22))))
        if sub:
            p.space_after = Pt(max(espaco - 4, 2))
    return tf


def imagem(s, arq, x, y, w=None, h=None):
    return s.shapes.add_picture(str(FIG / arq), Inches(x), Inches(y), Inches(w) if w else None, Inches(h) if h else None)


def tabela(s, df, x, y, w, larg=None, tam=13, alt_lin=0.4, destaque=None, negrito_col0=True):
    nl, nc = len(df) + 1, len(df.columns)
    t = s.shapes.add_table(nl, nc, Inches(x), Inches(y), Inches(w), Inches(alt_lin * nl)).table
    larg = larg or [1] * nc
    for j, fr in enumerate(larg):
        t.columns[j].width = Emu(int(Inches(w) * fr / sum(larg)))
    for i in range(nl):
        t.rows[i].height = Inches(alt_lin)
    for i in range(nl):
        for j in range(nc):
            cel = t.cell(i, j)
            v = str(df.columns[j]) if i == 0 else str(df.iat[i - 1, j])
            cel.text = ''
            cel.vertical_anchor = MSO_ANCHOR.MIDDLE
            cel.margin_left = cel.margin_right = Inches(0.06)
            cel.margin_top = cel.margin_bottom = Inches(0.02)
            par = cel.text_frame.paragraphs[0]
            par.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            r = par.add_run()
            r.text = v if v else ' '
            cel.fill.solid()
            if i == 0:
                cel.fill.fore_color.rgb = rgb(HEX['azul'])
                run_fmt(r, tam, rgb('#FFFFFF'), bold=True)
            else:
                cel.fill.fore_color.rgb = rgb('#F3F6F8' if i % 2 else '#FFFFFF')
                cor = destaque.get(v) if destaque else None
                run_fmt(r, tam, cor or rgb('#2B3A42'), bold=bool(cor) or (j == 0 and negrito_col0))
    return t


def cartao(s, x, y, w, h, titulo, valor, cor=HEX['azul'], tam_valor=26):
    caixa(s, x, y, w, h, fill='#F3F6F8')
    caixa(s, x, y, 0.07, h, fill=cor)
    tf = s.shapes.add_textbox(Inches(x + 0.2), Inches(y + 0.08), Inches(w - 0.3), Inches(h - 0.1)).text_frame
    tf.word_wrap = True
    r = tf.paragraphs[0].add_run()
    r.text = titulo
    run_fmt(r, 12.5, rgb(HEX['cinza']))
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = valor
    run_fmt(r, tam_valor, rgb(cor), bold=True)


def tab_vento(caso, plano):
    linhas = []
    for V in VEL:
        tv = RES[caso][(plano, V)]['tab_vento']
        for _, r in tv.iterrows():
            linhas.append([r['Parcela'].replace(' (× sen φ)', ' (× sen φ)'), br(V, 1), br(r['Área [m²]']),
                           br(r['h [m]'], 1), br(r['Cs'], 1), br(r['Ch'], 2), br(r['F [kN]']), br(r['Braço [m]'], 2),
                           br(r['Momento [kN·m]'] / 1e3, 1)])
    return pd.DataFrame(linhas, columns=['Parcela', 'V [m/s]', 'A [m²]', 'h [m]', 'Cs', 'Ch', 'F [kN]',
                                         'braço [m]', 'M [MN·m]'])


def tab_resumo(caso, gz=True):
    df = ex9.resumo(RES[caso])
    out = pd.DataFrame({'Plano': df['Plano'], 'V [m/s]': df['V [m/s]'].map(lambda x: br(x, 1)),
                        'φ1 [°]': df['φ1 [°]'].map(lambda x: br(x, 2)), 'φ2 [°]': df['φ2 [°]'].map(lambda x: br(x, 2)),
                        'φal [°]': df['φal [°]'].map(lambda x: br(x, 2)),
                        'A [m·rad]': df['A [m·rad]'].map(lambda x: br(x, 3)),
                        'B [m·rad]': df['B [m·rad]'].map(lambda x: br(x, 3)), 'A/B': df['A/B'].map(lambda x: br(x, 2)),
                        'GZ > 0': df['GZ > 0'], 'Critério': df['Critério']})
    return out if gz else out.drop(columns='GZ > 0')


def frase_intercepto(r):
    if r['phi1'] is None:
        return (f'{br(r["V"], 1)} m/s: HA > GZ de 0° a 50° (sem φ1: não há ângulo de equilíbrio), '
                f'A/B = {br(r["AB"], 2)} → NÃO atende.')
    s = f'{br(r["V"], 1)} m/s: φ1 = {br(r["phi1"], 2)}°'
    s += f', φ2 = {br(r["phi2"], 2)}°' if r['phi2'] is not None else ', sem φ2 até 50°'
    return s + f', A/B = {br(r["AB"], 2)} → {"atende" if r["atende"] else "NÃO atende"}.'


def montar():
    # ---------------------------------------------------------------- 1 capa
    s = prs.slides.add_slide(BLANK)
    N_SLIDE[0] += 1
    caixa(s, 0, 0, 13.333, 7.5, fill=HEX['azul'])
    caixa(s, 0.8, 3.55, 1.6, 0.07, fill=HEX['ha1'])
    tf = s.shapes.add_textbox(Inches(0.8), Inches(1.6), Inches(11.5), Inches(2)).text_frame
    tf.word_wrap = True
    r = tf.paragraphs[0].add_run()
    r.text = 'Exercício 9'
    run_fmt(r, 22, rgb('#F2B880'), bold=True)
    p = tf.add_paragraph()
    r = p.add_run()
    r.text = 'Curva GZ, momento de vento e critério de áreas'
    run_fmt(r, 40, rgb('#FFFFFF'), bold=True)
    tf = s.shapes.add_textbox(Inches(0.8), Inches(3.8), Inches(11.5), Inches(2)).text_frame
    tf.word_wrap = True
    for i, (t_, tam) in enumerate((('Modelo paramétrico de estabilidade intacta de uma semissubmersível '
                                    '(2 pontoons + 4 colunas), livre da amarração', 19),
                                   ('Hidrostática do Exercício 7 · pesos, KG e casco de menor peso do Exercício 8', 16),
                                   ('PNV3425 – Projeto de Sistemas Oceânicos · Escola Politécnica da USP · '
                                    '2º semestre de 2026', 14))):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(10)
        r = p.add_run()
        r.text = t_
        run_fmt(r, tam, rgb('#D6E9F0' if i < 2 else '#9AB4C2'))

    # ---------------------------------------------------------------- 2 dados
    s = slide('Plataforma e dados de entrada', 'Casco quadrado Lp × Lp; deck box e módulos com largura Lp', 'Dados')
    dados = pd.DataFrame([
        ['Pontoons Lp × bp × hp', '100 × 15 × 15 m'], ['Colunas bc × bc × hc', '15 × 15 × 45 m'],
        ['Calado T · air gap a = hp + hc − T', '30 m · 30 m'], ['Deck box hd · módulos hm', '8 m · 15 m'],
        ['Produção BOE · γe', '120.000 boe/d · 0,270 t/m³'], ['Vento V', '51,5 m/s (100 nós) e 36 m/s (70 nós)'],
        ['Deslocamento Δ = ρ·Vol (Ex. 7)', f'{br(HB["desloc"])} t  (Vol = {br(HB["vol"])} m³)'],
        ['KB · BM · KM (Ex. 7)', f'{br(HB["KB"], 2)} · {br(HB["BM_T"], 2)} · {br(HB["KM_T"], 2)} m'],
        ['KG (Ex. 8, sem superfície livre)', f'{br(KGB, 2)} m'],
        ['GM = KM − KG', f'{br(HB["KM_T"] - KGB, 2)} m (iguais nos dois planos: bp = bc)'],
    ], columns=['Grandeza', 'Valor'])
    tabela(s, dados, 0.55, 1.5, 7.0, larg=[1.05, 1.3], tam=14, alt_lin=0.46)
    imagem(s, 'parcelas_vento.png', 7.75, 1.45, w=5.4)

    # ---------------------------------------------------------------- 3 pesos
    s = slide('Quadro de pesos e KG – modelo do Exercício 8', 'Reproduz calcular_propriedades() do código do Ex. 8', 'Pesos')
    tp = pd.DataFrame({'Item': TB['Item'], 'Peso [t]': TB['Peso [t]'].map(br),
                       'VCG [m]': TB['KG item [m]'].map(lambda x: br(x, 2)), 'Momento [t·m]': TB['Momento [t·m]'].map(br)})
    tp.loc[len(tp)] = ['Total = Δ', br(HB['desloc']), br(KGB, 2), br(TB['Momento [t·m]'].sum())]
    tabela(s, tp, 0.55, 1.5, 7.3, larg=[1.6, 1, 0.8, 1.1], tam=14, alt_lin=0.44)
    texto(s, ['Topside = planta (0,083 t por boe/d) + estrutura do convés (35%) + operacional (35%) = '
              f'{br(ex9.topside(BASE))} t, a 10 m acima do topo das colunas.',
              'Casco = γe × volume envoltório; risers (4% Δ) e amarração (3% Δ) no topo das colunas.',
              'Lastro fecha o balanço Δ = ΣW, no centro dos pontoons (hp/2).',
              f'KG = ΣWz / Δ = {br(KGB, 2)} m → GM = {br(HB["KM_T"] - KGB, 2)} m.'],
          8.15, 1.5, 4.75, 4.6, tam=15)
    cartao(s, 8.25, 5.55, 2.2, 1.15, 'KG', f'{br(KGB, 2)} m')
    cartao(s, 10.6, 5.55, 2.2, 1.15, 'GM', f'{br(HB["KM_T"] - KGB, 2)} m', cor=HEX['gz'])

    # ---------------------------------------------------------------- 4 conferência
    conf = conferencia()
    s = slide('Conferência com os códigos dos Exercícios 7 e 8',
              'O modelo do Ex. 9 reproduz os dois códigos; observações sobre as contas', 'Verificação')
    if conf is not None:
        tabela(s, conf, 0.55, 1.5, 5.9, larg=[1, 1, 1.15, 1.15, 0.8], tam=12, alt_lin=0.355)
    texto(s, ['Hidrostática (Ex. 7) e pesos (Ex. 8) batem com o modelo: diferença zero.',
              'GM do Ex. 8 usa só (Lp − bc)/2, isto é, o GM longitudinal. Se bp > bc, GM_T < GM_L e a restrição '
              'fica do lado inseguro. Aqui bp = bc nos dois cascos: sem efeito no resultado.',
              f'Ótimo do Ex. 8 encostado nos limites: bp = hp = bc = 10 m e hc = 30 m (mínimos), lastro = 0, '
              f'Lp = {br(LEVE.Lp, 2)} m (área de convés ativa), GM = {br(HL["KM_L"] - KGL, 3)} m.',
              'Hipóteses conservadoras do KG (mantidas por serem as do Ex. 8):',
              '  lastro a hp/2: se a água ficar no fundo dos pontoons, o KG cai 1,30 m;',
              '  risers e amarração no topo das colunas, embora o Ex. 9 seja livre da amarração: sem eles, o KG cai 3,68 m;',
              '  VCG do topside 10 m acima das colunas; com hd e hm do Ex. 9 seria 11,5 m (+0,42 m).',
              'Detalhes menores: comentário de x_inicial cita bc = 13,5 m, mas o valor usado é 15 m; '
              'se o SLSQP falhar, o código volta para x_inicial sem aviso.'],
          6.7, 1.45, 6.2, 5.5, tam=13.5, espaco=5)

    # ---------------------------------------------------------------- 5 método 2D
    s = slide('1) e 2) Curva GZ por projeções 2D e ângulo de alagamento',
              'Pontoons e colunas viram retângulos no plano de inclinação, extrudados na direção perpendicular', 'GZ')
    imagem(s, 'secoes_2d.png', 0.45, 1.45, w=8.6)
    texto(s, ['Transversal: 2 pontoons (prof. Lp) + 2 pares de colunas (prof. 2bc).',
              'Longitudinal: pontoons sobrepostos (prof. 2bp) + colunas de vante e de ré (prof. 2bc).',
              'Para cada φ a linha d\'água inclinada é deslocada até o volume submerso igualar o volume deslocado (bisseção).',
              'GZ = s_B cos φ + (z_B − KG) sen φ.',
              'φal: o fundo do convés na borda (▼) toca a água. Acima dele o modelo não vale.'],
          9.25, 1.5, 3.75, 5.4, tam=14.5)

    # ---------------------------------------------------------------- 6 GZ planos
    rt, rl = RES['base'][('Transversal', VEL[0])], RES['base'][('Longitudinal', VEL[0])]
    s = slide('Curva GZ de 0° a 50° nos dois planos', 'Caso do enunciado, KG = 34,29 m', 'GZ')
    imagem(s, 'gz_planos.png', 0.45, 1.45, w=8.0)
    texto(s, ['Até ~17° as curvas coincidem com a fórmula de costado vertical: só as colunas cortam a linha d\'água.',
              'Na transversal o pontoon de barlavento emerge antes; a carena migra para sotavento e GZ cresce mais rápido.',
              f'φal = {br(rt["phi_al"], 2)}° (transversal) e {br(rl["phi_al"], 2)}° (longitudinal).',
              'Acima de φal o convés entraria na água; o modelo não o inclui como volume.'],
          8.75, 1.5, 4.25, 5.4, tam=15)

    # ---------------------------------------------------------------- 7 vento
    s = slide('3) a 5) Forças de vento, z_CLR, HM0 e HMud',
              'F = ½ ρar Cs Ch A V², ρar = 1,222 kg/m³ · braço = h + T − z_CLR', 'Vento')
    clr = pd.DataFrame([[pl, br(ex9.z_clr(BASE, pl)[1]['Área [m²]'].iloc[0]), br(ex9.z_clr(BASE, pl)[1]['Área [m²]'].iloc[1]),
                         br(RES['base'][(pl, VEL[0])]['z_CLR'], 2),
                         br(RES['base'][(pl, VEL[0])]['HM0'] / 1e3, 1), br(RES['base'][(pl, VEL[0])]['HMud'] / 1e3, 1),
                         br(RES['base'][(pl, VEL[1])]['HM0'] / 1e3, 1), br(RES['base'][(pl, VEL[1])]['HMud'] / 1e3, 1)]
                        for pl in ex9.PLANOS],
                       columns=['Plano', 'A pontoon [m²]', 'A colunas [m²]', 'z_CLR [m]', 'HM0 51,5 [MN·m]',
                                'HMud 51,5 [MN·m]', 'HM0 36 [MN·m]', 'HMud 36 [MN·m]'])
    tabela(s, clr, 0.55, 1.5, 12.25, tam=13.5, alt_lin=0.5)
    ch = pd.DataFrame([['Ch', '1,00', '1,10', '1,20', '1,30', '1,37']],
                      columns=['h [m]', 'até 15,3', '15,3–30,5', '30,5–46,0', '46,0–61,0', '61,0–76,0'])
    tabela(s, ch, 0.55, 3.2, 6.2, tam=13, alt_lin=0.42)
    texto(s, ['Áreas iguais nos dois planos (convés quadrado): colunas 4bc·a = 1.800 m², deck box Lp·hd = 800 m², '
              'módulos Lp·hm = 1.500 m² (Cs = 1,1), face inferior Lp² = 10.000 m² (× sen φ).',
              'Ch no centroide: colunas 15 m → 1,00; deck box 34 m → 1,20; módulos 45,5 m → 1,20; face inferior 30 m → 1,10.',
              'z_CLR muda com o plano: na transversal o pontoon aparece de lado (Lp·hp); na longitudinal, só as '
              'seções (2bp·hp). z_CLR mais baixo dá braços transversais maiores.',
              'HM ∝ V²: de 51,5 para 36 m/s os momentos caem para (36/51,5)² = 49%.'],
          0.55, 4.25, 12.25, 2.7, tam=15, espaco=5)

    # ---------------------------------------------------------------- 8–9 tabelas de vento
    for plano in ex9.PLANOS:
        r = RES['base'][(plano, VEL[0])]
        s = slide(f'Forças, braços e momentos por parcela – {plano.lower()}',
                  f'Caso do enunciado · z_CLR = {br(r["z_CLR"], 2)} m · a face inferior entra em HA multiplicada por sen φ',
                  'Vento')
        tabela(s, tab_vento('base', plano), 0.55, 1.5, 12.25, larg=[2.6, 0.8, 0.9, 0.7, 0.55, 0.6, 0.9, 0.9, 0.9],
               tam=13, alt_lin=0.47)
        for k, V in enumerate(VEL):
            rv = RES['base'][(plano, V)]
            cartao(s, 0.55 + k * 6.2, 5.9, 6.05, 0.95, f'V = {br(V, 1)} m/s',
                   f'HM0 = {br(rv["HM0"] / 1e3, 1)} MN·m · HMud = {br(rv["HMud"] / 1e3, 1)} MN·m · '
                   f'HA(0) = {br(rv["HA"][0], 3)} m', cor=HEX['ha1'] if k == 0 else HEX['ha2'], tam_valor=15)

    # ---------------------------------------------------------------- 10–11 GZ x HA base
    for plano in ex9.PLANOS:
        r1, r2 = RES['base'][(plano, VEL[0])], RES['base'][(plano, VEL[1])]
        s = slide(f'6) a 9) GZ × HA – {plano.lower()}', 'Caso do enunciado · áreas A e B de 0 a φal', 'Critério')
        imagem(s, f'gz_ha_base_{plano.lower()}.png', 0.45, 1.45, w=8.3)
        cartao(s, 9.0, 1.5, 1.9, 1.1, 'A/B 51,5 m/s', br(r1['AB'], 2), cor=HEX['ha1'])
        cartao(s, 11.05, 1.5, 1.9, 1.1, 'A/B 36 m/s', br(r2['AB'], 2), cor=HEX['ha2'])
        texto(s, [frase_intercepto(r1), frase_intercepto(r2),
                  f'φ2 > φal: GZ > 0 é verificado de 0° a φal = {br(r1["phi_al"], 2)}° → ok.',
                  'Limite exigido: A/B ≥ 1,3.'],
              9.0, 2.85, 4.0, 4.1, tam=14.5)

    # ---------------------------------------------------------------- 12 resumo base
    s = slide('Resumo do critério de áreas – caso do enunciado',
              'A ≥ 1,3 B e GZ > 0 de 0° a φ2 (ou φal, se φ2 não ocorrer antes)', 'Critério')
    tabela(s, tab_resumo('base'), 0.55, 1.5, 12.25, larg=[1.4, 0.9, 0.9, 0.9, 0.9, 1, 1, 0.8, 0.8, 1.3],
           tam=14, alt_lin=0.5, destaque=DEST)
    ab = [r['AB'] for r in RES['base'].values()]
    texto(s, [f'A plataforma do enunciado atende nos dois planos e nas duas velocidades (A/B de {br(min(ab), 2)} a '
              f'{br(max(ab), 2)}, contra 1,3 exigido).',
              'Com 51,5 m/s, o plano longitudinal tem o menor A/B: φal é maior, mas a área sob GZ quase não cresce '
              'e a área sob HA acompanha φal.',
              'HA cresce com φ por causa da face inferior do convés (HMud sen φ); em φal essa parcela já supera HM0 cos φ.'],
          0.55, 4.3, 12.25, 2.6, tam=15.5)

    # ---------------------------------------------------------------- 13 casco de menor peso
    s = slide('Solução de menor peso de casco (Exercício 8)',
              'SLSQP do Ex. 8: 1 ≤ GM ≤ 4 m, air gap ≥ 12 m, lastro ≥ 0, Lp² ≥ área requerida, bc ≤ bp', 'Menor peso')
    comp = ex9.comparativo_ex8(BASE, LEVE)
    linhas = ['Lp (m)', 'T (m)', 'bp (m)', 'hp (m)', 'bc (m)', 'hc (m)', 'Peso Casco (t)', 'Peso Lastro (t)', 'Δ (t)',
              'KG (m)', 'GM_T (m)', 'Air gap (m)']
    dec = {'Peso Casco (t)': 0, 'Peso Lastro (t)': 0, 'Δ (t)': 0, 'GM_T (m)': 3}
    c = pd.DataFrame([[k.replace('GM_T', 'GM'), br(comp.at[k, 'Original'], dec.get(k, 2)),
                       br(comp.at[k, 'Otimizado'], dec.get(k, 2)),
                       '—' if k == 'Peso Lastro (t)' else f'{br(comp.at[k, "Evolução (%)"], 1)}%'] for k in linhas],
                     columns=['', 'Enunciado', 'Menor peso', 'Variação'])
    tabela(s, c, 0.55, 1.45, 5.6, larg=[1.3, 1, 1, 0.9], tam=13, alt_lin=0.405)
    imagem(s, 'secoes_leve.png', 6.6, 1.45, w=5.6)
    texto(s, [f'Casco {br(100 * (1 - ex9.peso_casco(LEVE) / ex9.peso_casco(BASE)), 0)}% mais leve; Δ cai '
              f'{br(100 * (1 - HL["desloc"] / HB["desloc"]), 0)}% e o lastro some.',
              f'O topside ({br(ex9.topside(LEVE))} t) passa a dominar: KG sobe {br(KGL - KGB, 2)} m e GM fica no mínimo.',
              f'Air gap de {br(LEVE.a, 2)} m: o convés toca a água em φal = {br(RES["leve"][("Transversal", VEL[0])]["phi_al"], 1)}°, '
              'menos da metade do caso do enunciado.'],
          6.6, 4.2, 6.3, 2.7, tam=14.5)

    # ---------------------------------------------------------------- 14–15 GZ x HA leve
    for plano in ex9.PLANOS:
        r1, r2 = RES['leve'][(plano, VEL[0])], RES['leve'][(plano, VEL[1])]
        s = slide(f'GZ × HA do casco de menor peso – {plano.lower()}',
                  'Mesmo topside e mesmo vento · áreas A e B de 0 a φal', 'Menor peso')
        imagem(s, f'gz_ha_leve_{plano.lower()}.png', 0.45, 1.45, w=8.3)
        cartao(s, 9.0, 1.5, 1.9, 1.1, 'A/B 51,5 m/s', br(r1['AB'], 2), cor=HEX['al'])
        cartao(s, 11.05, 1.5, 1.9, 1.1, 'A/B 36 m/s', br(r2['AB'], 2), cor=HEX['al'] if not r2['atende'] else HEX['ha2'])
        texto(s, [frase_intercepto(r1), frase_intercepto(r2),
                  f'A = {br(r1["A"], 3)} m·rad: com GM ≈ 1 m e φal = {br(r1["phi_al"], 1)}°, a área sob GZ é '
                  f'{br(RES["base"][(plano, VEL[0])]["A"] / r1["A"], 0)} vezes menor que a do enunciado.'],
              9.0, 2.85, 4.0, 4.1, tam=14.5)

    # ---------------------------------------------------------------- 16 resumo leve
    s = slide('Resumo do critério de áreas – casco de menor peso',
              'Mesmos critérios: A ≥ 1,3 B e GZ > 0 até φ2 ou φal', 'Menor peso')
    tabela(s, tab_resumo('leve'), 0.55, 1.5, 12.25, larg=[1.4, 0.9, 0.9, 0.9, 0.9, 1, 1, 0.8, 0.8, 1.3],
           tam=14, alt_lin=0.5, destaque=DEST)
    abl = [r['AB'] for r in RES['leve'].values()]
    texto(s, [f'Não atende em nenhum plano nem velocidade: A/B entre {br(min(abl), 2)} e {br(max(abl), 2)}.',
              'Mesmo no vento de operação normal (70 nós) a área sob GZ até φal não chega à metade da área sob HA.',
              'GZ continua positivo até φal; a falha é só pela razão de áreas.'],
          0.55, 4.3, 12.25, 2.6, tam=15.5)

    # ---------------------------------------------------------------- 17 comentários
    s = slide('Comentários', secao='Conclusão')
    texto(s, [f'Caso do enunciado: atende com folga nos dois planos e nas duas velocidades (A/B ≥ {br(min(ab), 2)}).',
              'Casco de menor peso do Ex. 8: não atende em nenhum caso. Três efeitos se somam:',
              f'  air gap no mínimo (12 m) → φal cai de ~28° para {br(RES["leve"][("Transversal", VEL[0])]["phi_al"], 1)}° '
              'e corta a faixa de integração;',
              '  GM no mínimo (1 m) → GZ pequeno nessa faixa;',
              f'  Δ {br(100 * (1 - HL["desloc"] / HB["desloc"]), 0)}% menor com convés quase do mesmo tamanho → '
              'HA = HM/(Δg) maior.',
              'A otimização do Ex. 8 usa só GM inicial e air gap. Para um projeto viável, o critério de áreas '
              '(ou um air gap e um GM mínimos derivados dele) precisa entrar como restrição.',
              'Limitações: convés fora do volume flutuante, sem trim acoplado, vento constante, sem sombra entre '
              'colunas, KG do Ex. 8 com hipóteses conservadoras (slide 4).'],
          0.55, 1.5, 12.25, 5.4, tam=17, espaco=9)

    # ---------------------------------------------------------------- 18 código
    s = slide('Código e simulação interativa', 'Mesmas ferramentas do repositório Projetos_Sistemas_Oceanicos: '
              'Python, NumPy, SciPy, pandas, Streamlit e Plotly', 'Ferramentas')
    texto(s, ['**ex9_estabilidade.py – modelo paramétrico',
              'Classe Plataforma com os dados de entrada do enunciado e o modelo de pesos do Ex. 8.',
              'python ex9_estabilidade.py → tabelas no terminal e CSVs em resultados/.',
              '**dashboard_estabilidade_semi.py – simulação interativa',
              'streamlit run dashboard_estabilidade_semi.py',
              'Abas por plano (GZ × HA, áreas, interceptos, tabela por parcela), seção inclinada com B, G e GZ, '
              'otimização do Ex. 8 com restrições ajustáveis e exportação CSV.',
              '**referencia/ – códigos dos Exercícios 7 e 8 usados na conferência',
              '**gerar_apresentacao_ex9.py – figuras e esta apresentação'],
          0.55, 1.5, 12.25, 5.4, tam=16, espaco=7)

    prs.save(PASTA / 'ex9_apresentacao.pptx')


if __name__ == '__main__':
    print('fonte das figuras:', FONTE_FIG)
    figuras()
    montar()
    print('Figuras em', FIG, '| apresentação:', PASTA / 'ex9_apresentacao.pptx', '|', N_SLIDE[0], 'slides')
