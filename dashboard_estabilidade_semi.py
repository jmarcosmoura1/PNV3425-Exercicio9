# -*- coding: utf-8 -*-
"""
PNV3425 - Projeto de Sistemas Oceânicos
Dashboard interativo do Exercício 9: curva GZ por projeções 2D, momento de vento e critério de áreas
de uma plataforma semissubmersível (2 pontoons retangulares + 4 colunas quadradas).

Requisitos:  pip install "streamlit>=1.50" plotly numpy pandas
Uso:         streamlit run dashboard_estabilidade_semi.py
             (abre no navegador em http://localhost:8501)

Os cálculos estão em ex9_estabilidade.py (mesma pasta).
"""
from dataclasses import replace, asdict
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import ex9_estabilidade as ex9

COR = dict(gz='#1F6FA8', ha1='#E8702A', ha2='#7A4EAB', leve='#9AA5AB', al='#C62828', agua='#CFE3EA',
           sub='#1F6FA8', casco='#0B2E40', deck='#9AA5AB', mod='#F2B880', ok='#2E7D32', nok='#C62828')


def br(x, dec=0):
    """número no formato brasileiro: 123.000,5"""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return '—'
    return f'{x:,.{dec}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


@st.cache_data
def calcula(p: ex9.Plataforma, velocidades: tuple, passo: float, limite: str):
    return ex9.avalia(p, velocidades, passo, limite)


@st.cache_data
def otimiza(base: ex9.Plataforma, GM_min: float, GM_max: float, airgap_min: float, gm_plano: str):
    leve, r = ex9.menor_peso_casco(base, GM_min, GM_max, airgap_min, gm_plano=gm_plano)
    return leve, bool(r.success), str(r.message)


def layout(fig, xt, yt, h=470):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=30, b=10), hovermode='x unified',
                      xaxis_title=xt, yaxis_title=yt, template='plotly_white',
                      legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    fig.update_xaxes(showgrid=True, gridcolor='#ECEFF1')
    fig.update_yaxes(showgrid=True, gridcolor='#ECEFF1', zeroline=True, zerolinecolor='#B0BEC5')
    return fig


# ------------------------------------------------------------------ interface
st.set_page_config(page_title='Estabilidade intacta – semissubmersível', page_icon='🌬️', layout='wide')
st.title('Semissubmersível – curva GZ, momento de vento e critério de áreas')
st.caption('PNV3425 · Exercício 9 · GZ por projeções 2D, vento pela DNV-OS-C301 / Código MODU 2009, '
           'plataforma livre da amarração')

R = ex9.CASO_BASE
with st.sidebar:
    st.header('Casco')
    Lp = st.number_input('Comprimento dos pontoons Lp [m]', 40.0, 200.0, R.Lp, 1.0)
    bp = st.number_input('Boca dos pontoons bp [m]', 5.0, 40.0, R.bp, 0.5)
    hp = st.number_input('Altura dos pontoons hp [m]', 5.0, 30.0, R.hp, 0.5)
    bc = st.number_input('Lado das colunas bc [m]', 5.0, 40.0, R.bc, 0.5)
    hc = st.number_input('Altura das colunas hc [m]', 10.0, 80.0, R.hc, 0.5)
    T = st.slider('Calado T [m]', float(hp) + 0.5, float(hp + hc) - 0.5, min(max(R.T, hp + 0.5), hp + hc - 0.5), 0.5)
    st.header('Convés e pesos')
    hd = st.number_input('Altura do deck box hd [m]', 2.0, 20.0, R.hd, 0.5)
    hm = st.number_input('Altura média dos módulos hm [m]', 2.0, 40.0, R.hm, 0.5)
    BOE = st.number_input('Produção BOE [boe/d]', 10_000.0, 300_000.0, R.BOE, 5_000.0, format='%.0f')
    gamma_e = st.number_input('Peso específico estrutural γe [t/m³]', 0.10, 0.50, R.gamma_e, 0.005, format='%.3f')
    with st.expander('Modelo de pesos do Exercício 8'):
        c_pl = st.number_input('Planta de processo [t por boe/d]', 0.01, 0.30, R.c_pl, 0.001, format='%.3f')
        f_co = st.number_input('Estrutura do convés [× planta]', 0.0, 1.0, R.f_co, 0.01)
        f_op = st.number_input('Peso operacional [× planta]', 0.0, 1.0, R.f_op, 0.01)
        dz_top = st.number_input('VCG do topside acima do topo das colunas [m]', 0.0, 40.0, R.dz_top, 0.5)
        f_ris = st.number_input('Risers [× Δ]', 0.0, 0.2, R.f_ris, 0.005, format='%.3f')
        f_amr = st.number_input('Amarração [× Δ]', 0.0, 0.2, R.f_amr, 0.005, format='%.3f')
    usar_KG = st.toggle('Impor um KG', value=False, help='Por padrão o KG vem do modelo de pesos do Exercício 8.')
    KG_in = st.number_input('KG [m]', 5.0, 80.0, 34.29, 0.01, disabled=not usar_KG)
    st.header('Vento')
    V1 = st.number_input('V tempestade severa [m/s]', 10.0, 80.0, 51.5, 0.5)
    V2 = st.number_input('V operação normal [m/s]', 10.0, 80.0, 36.0, 0.5)
    limite = st.segmented_control('Limite de integração de A e B', ['φal (enunciado)', 'mín(φ2, φal) (MODU)'],
                                  default='φal (enunciado)')
    st.header('Solução de menor peso (Ex. 8)')
    comparar = st.toggle('Comparar com o casco de menor peso', value=True)
    fonte = st.radio('Origem das dimensões', ['Otimização do Exercício 8 (SLSQP)', 'Informar dimensões'],
                     disabled=not comparar)
    otim_on = comparar and fonte.startswith('Otim')
    c1, c2 = st.columns(2)
    GM_min = c1.number_input('GM mín. [m]', 0.0, 10.0, 1.0, 0.1, disabled=not otim_on)
    GM_max = c2.number_input('GM máx. [m]', 0.5, 20.0, 4.0, 0.1, disabled=not otim_on)
    ag_min = c1.number_input('Air gap mín. [m]', 0.0, 40.0, 12.0, 0.5, disabled=not otim_on)
    gm_corr = c2.toggle('GM nos 2 planos', value=False, disabled=not otim_on,
                        help='O código do Ex. 8 usa só a distância (Lp − bc)/2 (GM longitudinal). '
                             'Ativado, a restrição usa o menor entre GM_T e GM_L.')
    if st.button('Restaurar dados do exercício'):
        st.session_state.clear()
        st.rerun()

lim_key = 'MODU' if (limite or '').startswith('mín') else 'enunciado'
p = ex9.Plataforma(Lp=Lp, bp=bp, hp=hp, bc=bc, hc=hc, T=T, BOE=BOE, gamma_e=gamma_e, hd=hd, hm=hm,
                   KG=KG_in if usar_KG else None, c_pl=c_pl, f_co=f_co, f_op=f_op, dz_top=dz_top,
                   f_ris=f_ris, f_amr=f_amr)
VEL = (float(V1), float(V2))
try:
    res = calcula(p, VEL, 0.25, lim_key)
except ValueError as e:
    st.error(f'Geometria inválida: {e}')
    st.stop()
hs = ex9.hidrostatica(p)
tab_p, KG = ex9.pesos(p)

leve = res_l = None
if comparar:
    if otim_on:
        leve, sucesso, msg = otimiza(replace(p, KG=None), GM_min, GM_max, ag_min, 'min' if gm_corr else 'Ex8')
        if not sucesso:
            st.warning(f'A otimização do Exercício 8 não convergiu ({msg}); mostrando o casco analisado.')
    else:
        with st.sidebar:
            o = ex9.menor_peso_casco()[0]
            c1, c2 = st.columns(2)
            l_Lp = c1.number_input('Lp leve', 40.0, 200.0, round(o.Lp, 3), 0.1, format='%.3f')
            l_T = c2.number_input('T leve', 5.0, 80.0, round(o.T, 3), 0.1, format='%.3f')
            l_bp = c1.number_input('bp leve', 5.0, 40.0, o.bp, 0.5)
            l_hp = c2.number_input('hp leve', 5.0, 30.0, o.hp, 0.5)
            l_bc = c1.number_input('bc leve', 5.0, 40.0, o.bc, 0.5)
            l_hc = c2.number_input('hc leve', 10.0, 80.0, o.hc, 0.5)
            l_KG = st.number_input('KG leve [m] (0 = modelo de pesos)', 0.0, 80.0, 0.0, 0.01)
        leve = replace(p, Lp=l_Lp, T=l_T, bp=l_bp, hp=l_hp, bc=l_bc, hc=l_hc, KG=l_KG if l_KG > 0 else None)
    try:
        res_l = calcula(leve, VEL, 0.25, lim_key)
    except ValueError as e:
        st.warning(f'Casco de menor peso inválido: {e}')
        leve = res_l = None

# ---------------- indicadores
m = st.columns(7)
m[0].metric('Deslocamento Δ [t]', br(hs['desloc']))
m[1].metric('KG [m]', br(KG, 2), help='imposto' if usar_KG else 'modelo de pesos do Exercício 8')
m[2].metric('GM [m]', br(hs['KM_T'] - KG, 2), help=f'GM_L = {br(hs["KM_L"] - KG, 2)} m')
m[3].metric('Air gap a [m]', br(p.a, 1))
m[4].metric('Peso do casco [t]', br(ex9.peso_casco(p)))
m[5].metric('φal transversal', f'{br(res[("Transversal", VEL[0])]["phi_al"], 2)}°')
m[6].metric('φal longitudinal', f'{br(res[("Longitudinal", VEL[0])]["phi_al"], 2)}°')
if tab_p['Peso [t]'].iloc[-1] < -1e-6 and not usar_KG:
    st.warning('Lastro negativo: o casco não flutua com o topside neste calado (pesos > deslocamento).')

# ---------------- veredito geral
ok_base = all(r['atende'] for r in res.values())
txt = ' · '.join(f'{pl[:5]}. {br(V, 1)} m/s: {"✅" if r["atende"] else "❌"} A/B = {br(r["AB"], 2)}'
                 for (pl, V), r in res.items())
(st.success if ok_base else st.error)(f'**Caso analisado {"ATENDE" if ok_base else "NÃO ATENDE"} ao critério de áreas** — {txt}')


def grafico(r_v1, r_v2, r_sel, r_leve=None):
    """GZ e HA × φ, com φal, interceptos e áreas A (sob GZ) e B (sob HA) da velocidade escolhida."""
    phi, GZ = r_sel['phi'], r_sel['GZ']
    lim = r_sel['lim']
    sel = phi <= lim + 1e-9
    fig = go.Figure()
    xa = np.append(phi[sel], lim)
    fig.add_scatter(x=np.concatenate([xa, xa[::-1]]),
                    y=np.concatenate([np.append(GZ[sel], np.interp(lim, phi, GZ)), np.zeros(len(xa))]),
                    fill='toself', fillcolor='rgba(31,111,168,0.12)', line=dict(width=0), hoverinfo='skip',
                    name=f'A = {br(r_sel["A"], 3)} m·rad')
    HA = r_sel['HA']
    fig.add_scatter(x=np.concatenate([xa, xa[::-1]]),
                    y=np.concatenate([np.append(HA[sel], np.interp(lim, phi, HA)), np.zeros(len(xa))]),
                    fill='toself', fillcolor='rgba(232,112,42,0.25)', line=dict(width=0), hoverinfo='skip',
                    name=f'B = {br(r_sel["B"], 3)} m·rad')
    val = phi <= r_sel['phi_al'] + 1e-9
    fig.add_scatter(x=phi[val], y=GZ[val], name='GZ', line=dict(color=COR['gz'], width=3))
    fig.add_scatter(x=phi[~val | (phi == phi[val][-1])], y=GZ[~val | (phi == phi[val][-1])],
                    name='GZ acima de φal (fora da validade)', line=dict(color=COR['gz'], width=2, dash='dot'))
    for r, cor in ((r_v1, COR['ha1']), (r_v2, COR['ha2'])):
        fig.add_scatter(x=phi, y=r['HA'], name=f'HA – V = {br(r["V"], 1)} m/s',
                        line=dict(color=cor, width=3 if r is r_sel else 1.5, dash=None if r is r_sel else 'dash'))
    if r_leve is not None:
        fig.add_scatter(x=r_leve['phi'], y=r_leve['GZ'], name='GZ – casco de menor peso',
                        line=dict(color=COR['leve'], width=2, dash='dashdot'))
    fig.add_vline(x=r_sel['phi_al'], line=dict(color=COR['al'], dash='dash', width=1.5),
                  annotation_text=f'φal = {br(r_sel["phi_al"], 2)}°', annotation_position='top left')
    for nome, x in (('φ1', r_sel['phi1']), ('φ2', r_sel['phi2'])):
        if x is not None:
            fig.add_scatter(x=[x], y=[np.interp(x, phi, GZ)], mode='markers+text', text=[f'{nome} = {br(x, 1)}°'],
                            textposition='bottom right', marker=dict(size=10, color='black', symbol='x'),
                            showlegend=False, hoverinfo='skip')
    fig.update_traces(hovertemplate='%{y:.3f} m', selector=dict(mode='lines'))
    return layout(fig, 'Ângulo de inclinação φ [°]', 'Braço [m]')


def tabela_resumo(rs):
    return ex9.resumo({k: v for k, v in rs.items()})


def fmt_tab(df, dec):
    return df.style.format({c: (lambda x, d=d: br(x, d)) for c, d in dec.items()})


abas = st.tabs(['Transversal', 'Longitudinal', 'Seção inclinada', 'Resumo e comparação', 'Pesos e hipóteses'])
for aba, plano in zip(abas[:2], ex9.PLANOS):
    with aba:
        Vsel = st.segmented_control('Áreas para a velocidade', [f'{br(V, 1)} m/s' for V in VEL],
                                    default=f'{br(VEL[0], 1)} m/s', key=f'v_{plano}')
        Vk = VEL[1] if Vsel == f'{br(VEL[1], 1)} m/s' else VEL[0]
        r = res[(plano, Vk)]
        col_g, col_t = st.columns([3, 2])
        with col_g:
            st.plotly_chart(grafico(res[(plano, VEL[0])], res[(plano, VEL[1])], r,
                                    res_l[(plano, Vk)] if res_l else None), width='stretch', key=f'g_{plano}')
        with col_t:
            st.markdown(f'**Critério – {plano.lower()}, V = {br(Vk, 1)} m/s**')
            c = st.columns(3)
            c[0].metric('A/B', br(r['AB'], 2), delta='≥ 1,30 ✅' if r['crit_area'] else '< 1,30 ❌',
                        delta_color='normal' if r['crit_area'] else 'inverse')
            c[1].metric('φ1 [°]', br(r['phi1'], 2))
            c[2].metric('φ2 [°]', br(r['phi2'], 2), help='— : sem 2º intercepto até 50°')
            st.markdown(f'z_CLR = **{br(r["z_CLR"], 2)} m** · HM0 = **{br(r["HM0"] / 1e3, 1)} MN·m** · '
                        f'HMud = **{br(r["HMud"] / 1e3, 1)} MN·m** · pressão q = {br(r["q"], 3)} kPa')
            st.markdown(f'GZ > 0 de 0° a {br(r["phi_chk"], 1)}°: **{"sim" if r["gz_pos"] else "não"}** · '
                        f'integração até {br(r["lim"], 2)}°')
            st.latex(r'HA(\varphi)=\frac{HM_0\cos\varphi+HM_{ud}\,\mathrm{sen}\,\varphi}{\Delta g},\quad '
                     r'A=\int_0^{\varphi_{al}}GZ\,d\varphi,\quad B=\int_0^{\varphi_{al}}HA\,d\varphi')
        st.markdown('**Forças, braços e momentos por parcela** (braço = h + T − z_CLR; a face inferior multiplica sen φ)')
        st.dataframe(fmt_tab(r['tab_vento'], {'Área [m²]': 0, 'h [m]': 2, 'Cs': 2, 'Ch': 2, 'F [kN]': 1,
                                              'Braço [m]': 2, 'Momento [kN·m]': 0}), hide_index=True, width='stretch')
        cz, ct = st.columns(2)
        with cz:
            zc, tz = ex9.z_clr(p, plano)
            st.markdown(f'**Silhueta submersa (z_CLR = {br(zc, 2)} m acima da quilha)**')
            st.dataframe(fmt_tab(tz, {'Área [m²]': 0, 'z [m]': 2}), hide_index=True, width='stretch')
        with ct:
            st.markdown('**Interceptos e áreas nas duas velocidades**')
            st.dataframe(fmt_tab(ex9.resumo({k: v for k, v in res.items() if k[0] == plano}).drop(columns='Plano'),
                                 {'V [m/s]': 1, 'V [nós]': 0, 'φ1 [°]': 2, 'φ2 [°]': 2, 'φal [°]': 2,
                                  'A [m·rad]': 3, 'B [m·rad]': 3, 'A/B': 2}), hide_index=True, width='stretch')

# ---------------- seção inclinada (simulação da projeção 2D)
with abas[2]:
    c1, c2, c3 = st.columns([1, 1, 3])
    plano = c1.radio('Plano', ex9.PLANOS, key='sec_plano')
    caso = c2.radio('Casco', ['Analisado', 'Menor peso'] if leve else ['Analisado'], key='sec_caso')
    q = leve if caso == 'Menor peso' else p
    rq = (res_l if caso == 'Menor peso' else res)[(plano, VEL[0])]
    fg = c3.slider('Ângulo de inclinação φ [°]', 0.0, 50.0, 15.0, 0.5)
    f = np.radians(fg)
    cs, sn = np.cos(f), np.sin(f)
    rets = ex9.retangulos(q, plano)
    vol = ex9.hidrostatica(q)['vol']
    d, sB, zB = ex9.equilibrio(rets, vol, f)
    KGq = ex9.pesos(q)[1]
    terra = lambda s, z: (s * cs + z * sn, z * cs - s * sn - d)     # (horizontal, vertical) com a LA em 0
    fig = go.Figure()
    W = q.Lp * 0.85
    fig.add_scatter(x=[-W, W, W, -W], y=[0, 0, -q.T - 25, -q.T - 25], fill='toself', fillcolor=COR['agua'],
                    line=dict(width=0), hoverinfo='skip', showlegend=False)
    zd = q.hp + q.hc
    outros = [(-q.Lp / 2, q.Lp / 2, zd, zd + q.hd, COR['deck'], 'deck box'),
              (-q.Lp / 2, q.Lp / 2, zd + q.hd, zd + q.hd + q.hm, COR['mod'], 'módulos')]
    for s0, s1, z0, z1, cor, nome in outros:
        X, Z = terra(np.array([s0, s1, s1, s0, s0]), np.array([z0, z0, z1, z1, z0]))
        fig.add_scatter(x=X, y=Z, fill='toself', fillcolor=cor, line=dict(color=COR['casco'], width=1),
                        name=nome, hoverinfo='skip', opacity=0.8)
    for i, rr in enumerate(rets):
        s0, s1, z0, z1, _ = rr
        X, Z = terra(np.array([s0, s1, s1, s0, s0]), np.array([z0, z0, z1, z1, z0]))
        fig.add_scatter(x=X, y=Z, line=dict(color=COR['casco'], width=1.5), fill='toself',
                        fillcolor='rgba(255,255,255,0.6)', hoverinfo='skip', showlegend=False)
        poli = ex9.poligono_submerso(rr, cs, sn, d)
        if len(poli) >= 3:
            ps = np.array(poli + [poli[0]])
            X, Z = terra(ps[:, 0], ps[:, 1])
            fig.add_scatter(x=X, y=Z, fill='toself', fillcolor='rgba(31,111,168,0.55)', line=dict(width=0),
                            name='volume submerso', legendgroup='sub', showlegend=(i == 0), hoverinfo='skip')
    XB, ZB = terra(sB, zB)
    XG, ZG = terra(0.0, KGq)
    fig.add_scatter(x=[-W, W], y=[0, 0], line=dict(color='#1F6FA8', width=1.5, dash='dash'), name="linha d'água",
                    hoverinfo='skip')
    fig.add_scatter(x=[XB, XB], y=[ZB, ZB + 60], line=dict(color=COR['gz'], width=1.5), showlegend=False,
                    hoverinfo='skip')
    fig.add_scatter(x=[XG, XG], y=[ZG, ZG - 60], line=dict(color=COR['casco'], width=1.5), showlegend=False,
                    hoverinfo='skip')
    fig.add_scatter(x=[XB], y=[ZB], mode='markers+text', text=['B'], textposition='bottom right',
                    marker=dict(size=11, color=COR['gz']), name='centro de carena B')
    fig.add_scatter(x=[XG], y=[ZG], mode='markers+text', text=['G'], textposition='top left',
                    marker=dict(size=11, color=COR['casco'], symbol='diamond'), name='centro de gravidade G')
    GZv = (XB - XG)
    fig.add_annotation(x=XB, y=ZG, ax=XG, ay=ZG, xref='x', yref='y', axref='x', ayref='y', showarrow=True,
                       arrowhead=2, arrowcolor=COR['al'], text='', arrowwidth=2)
    fig.add_annotation(x=(XB + XG) / 2, y=ZG, text=f'GZ = {br(GZv, 2)} m', showarrow=False, yshift=12,
                       font=dict(color=COR['al']))
    Xe, Ze = terra(q.Lp / 2, zd)
    fig.add_scatter(x=[Xe], y=[Ze], mode='markers', marker=dict(size=9, color=COR['al'], symbol='triangle-down'),
                    name=f'borda do convés (folga {br(Ze, 2)} m)')
    for yy in (zd + q.hd / 2 - q.T, zd + q.hd + q.hm / 2 - q.T, (zd - q.T) / 2):
        fig.add_annotation(x=-W * 0.72, y=yy, ax=-W * 0.98, ay=yy, xref='x', yref='y', axref='x', ayref='y',
                           showarrow=True, arrowhead=2, arrowcolor='#C62828', arrowwidth=2, text='')
    fig.add_annotation(x=-W * 0.85, y=zd + q.hd + q.hm - q.T + 6, text='vento', showarrow=False,
                       font=dict(color='#C62828'))
    fig.update_layout(height=620, template='plotly_white', margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation='h', yanchor='bottom', y=1.02, x=0))
    fig.update_xaxes(range=[-W, W], title='horizontal [m]', zeroline=False)
    fig.update_yaxes(range=[-q.T - 20, zd + q.hd + q.hm - q.T + 15], scaleanchor='x', scaleratio=1,
                     title="vertical a partir da linha d'água [m]")
    cg, ci = st.columns([3, 1])
    cg.plotly_chart(fig, width='stretch')
    with ci:
        st.metric('GZ [m]', br(GZv, 3))
        st.metric('HA (V tempestade) [m]', br(float(np.interp(fg, rq['phi'], rq['HA'])), 3))
        st.metric("Folga do convés à água [m]", br(Ze, 2), help='Zera em φ = φal')
        st.metric('φal [°]', br(rq['phi_al'], 2))
        st.caption(f'd = {br(d, 2)} m (posição da linha d\'água no eixo inclinado) · B = ({br(sB, 2)}; {br(zB, 2)}) m '
                   f'· KG = {br(KGq, 2)} m. Os retângulos são as projeções 2D dos pontoons e colunas; a parte azul '
                   'é o volume submerso que mantém o deslocamento.')

# ---------------- resumo e comparação
with abas[3]:
    st.markdown('**Caso analisado**')
    dec = {'V [m/s]': 1, 'V [nós]': 0, 'φ1 [°]': 2, 'φ2 [°]': 2, 'φal [°]': 2, 'A [m·rad]': 3, 'B [m·rad]': 3, 'A/B': 2}
    st.dataframe(fmt_tab(ex9.resumo(res), dec), hide_index=True, width='stretch')
    if leve:
        hl = ex9.hidrostatica(leve)
        KGl = ex9.pesos(leve)[1]
        st.markdown(f'**Casco de menor peso** – Lp = {br(leve.Lp, 2)} m, T = {br(leve.T, 2)} m, '
                    f'bp = {br(leve.bp, 1)} m, hp = {br(leve.hp, 1)} m, '
                    f'bc = {br(leve.bc, 1)} m, hc = {br(leve.hc, 1)} m, air gap = {br(leve.a, 2)} m · '
                    f'peso do casco {br(ex9.peso_casco(leve))} t '
                    f'({br(100 * (ex9.peso_casco(leve) / ex9.peso_casco(p) - 1), 1)}%) · Δ = {br(hl["desloc"])} t · '
                    f'KG = {br(KGl, 2)} m · GM_T = {br(hl["KM_T"] - KGl, 2)} m · GM_L = {br(hl["KM_L"] - KGl, 2)} m')
        st.dataframe(fmt_tab(ex9.resumo(res_l), dec), hide_index=True, width='stretch')
        ok_l = all(r['atende'] for r in res_l.values())
        st.info('O casco de menor peso foi dimensionado só por flutuação, GM inicial e air gap. '
                + ('Ele também atende ao critério de áreas.' if ok_l else
                   'Com air gap menor, φal cai; com GM perto do mínimo e Δ menor (HA ∝ 1/Δ), a área sob GZ '
                   'não cobre a do vento: o critério de áreas passa a limitar o projeto.'))
        st.markdown('**Comparação no formato do Exercício 8**')
        st.dataframe(ex9.comparativo_ex8(p, leve).style.format(lambda x: br(x, 2)), width='stretch')
    linhas = []
    for nome, rs in (('Analisado', res), ('Menor peso', res_l)):
        if rs:
            for (pl, V), r in rs.items():
                df = r['gz'][['phi [°]', 'GZ [m]']].assign(**{'HA [m]': r['HA'], 'Caso': nome, 'Plano': pl, 'V [m/s]': V})
                linhas.append(df)
    st.download_button('Exportar CSV (GZ e HA)', pd.concat(linhas).to_csv(sep=';', decimal=',', index=False)
                       .encode('utf-8-sig'), file_name='ex9_gz_ha.csv', mime='text/csv', icon=':material/download:')

# ---------------- pesos e hipóteses
with abas[4]:
    st.markdown('**Quadro de pesos do caso analisado** ' + ('(o KG informado substitui o KG do quadro)' if usar_KG else ''))
    st.dataframe(fmt_tab(tab_p, {'Peso [t]': 0, 'KG item [m]': 2, 'Momento [t·m]': 0}), hide_index=True)
    st.markdown(f'KG do quadro = **{br((tab_p["Momento [t·m]"].sum() / hs["desloc"]), 2)} m** · '
                f'KB = {br(hs["KB"], 2)} m · BM = {br(hs["BM_T"], 2)} m · KM = {br(hs["KM_T"], 2)} m')
    st.markdown(
        '- **GZ por projeções 2D:** pontoons e colunas viram retângulos no plano de inclinação, extrudados pelo '
        'comprimento perpendicular (na transversal, os pontoons têm profundidade Lp e cada par de colunas 2bc; na '
        'longitudinal, os dois pontoons se sobrepõem com profundidade 2bp). Para cada φ a linha d\'água inclinada '
        'é deslocada até o volume submerso igualar ∇ (bisseção) e GZ = s_B cos φ + (z_B − KG) sen φ.\n'
        '- **φal:** fundo do convés (z = hp + hc) na borda s = Lp/2 toca a água. Acima dele o modelo não vale '
        '(o deck box não entra no volume).\n'
        '- **Vento:** F = ½ ρar Cs Ch A V², ρar = 1,222 kg/m³, Ch na altura do centroide acima da LA; colunas sem '
        'sombra; face inferior com área Lp² e Ch na altura a.\n'
        '- **Critério:** A ≥ 1,3 B e GZ > 0 de 0° até φ2 (ou φal, se φ2 não ocorrer antes).\n'
        '- **Hidrostática (Ex. 7):** ∇ = 2Lp·bp·hp + 4bc²(T − hp); colunas a (Lp − bp)/2 do centro na transversal '
        'e a (Lp − bc)/2 na longitudinal.\n'
        '- **KG (Ex. 8, sem superfície livre):** planta 0,083 t por boe/d + estrutura do convés (35%) + operacional '
        '(35%) a 10 m acima do topo das colunas; casco = γe × volume envoltório; risers 4% Δ e amarração 3% Δ no '
        'topo das colunas; lastro fecha Δ no centro dos pontoons (hp/2).\n'
        '- **Casco de menor peso (Ex. 8):** SLSQP sobre Lp, bp, hp, bc, hc e T, minimizando o peso do casco com '
        '1 ≤ GM ≤ 4 m, air gap ≥ 12 m, lastro ≥ 0, Lp² ≥ 42,246·Q + 4850,1 e bc ≤ bp.')
