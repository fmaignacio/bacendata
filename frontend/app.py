"""
BacenData Dashboard — Painel interativo de indicadores do Banco Central.

Uso:
    streamlit run frontend/app.py
"""

import io
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from bacendata import sgs
from bacendata.wrapper.catalogo import CATALOGO, listar

# =============================================================================
# Configuracao da pagina
# =============================================================================

st.set_page_config(
    page_title="BacenData — Indicadores do Banco Central",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# Constantes
# =============================================================================

CORES = [
    "#1f77b4",  # azul
    "#ff7f0e",  # laranja
    "#2ca02c",  # verde
    "#d62728",  # vermelho
    "#9467bd",  # roxo
    "#8c564b",  # marrom
]

CATEGORIAS = {
    "Taxas de Juros": [11, 12, 4390, 4189, 25434],
    "Inflação": [433],
    "Câmbio": [1, 21619],
    "Crédito": [20542, 21112, 21082],
    "Setor Externo": [7326],
    "Expectativas (Focus)": [27574, 27575],
}

# Descrições detalhadas para tooltips e documentação inline
DESCRICOES_DETALHADAS = {
    11: (
        "Taxa Selic diária definida pelo COPOM. Principal instrumento de "
        "política monetária do Banco Central para controle da inflação."
    ),
    12: (
        "Selic acumulada no mês corrente. Útil para cálculo de "
        "rendimentos de renda fixa atrelados à Selic."
    ),
    433: (
        "Índice Nacional de Preços ao Consumidor Amplo — principal "
        "indicador de inflação oficial do Brasil, medido pelo IBGE."
    ),
    4390: (
        "Taxa Selic acumulada no mês expressa em termos anuais. "
        "Referência para remuneração de títulos públicos."
    ),
    1: (
        "Cotação de compra do dólar americano (PTAX). Média das "
        "operações no mercado interbancário, divulgada diariamente pelo BACEN."
    ),
    21619: (
        "Cotação de compra do euro (PTAX). Média das operações no "
        "mercado interbancário, divulgada diariamente pelo BACEN."
    ),
    4189: (
        "Taxa média de juros cobrada nas operações de crédito para "
        "pessoa física. Indicador do custo do crédito ao consumidor."
    ),
    25434: (
        "Taxa média de juros nas operações de crédito livre total. "
        "Abrange PF e PJ em modalidades sem direcionamento obrigatório."
    ),
    20542: (
        "Saldo total da carteira de crédito com recursos livres no "
        "sistema financeiro. Indicador do volume de crédito na economia."
    ),
    21112: (
        "Percentual de operações em atraso acima de 90 dias na carteira "
        "de crédito de pessoa física. Indicador de risco de crédito PF."
    ),
    21082: (
        "Percentual de operações em atraso acima de 90 dias na carteira "
        "de crédito de pessoa jurídica. Indicador de risco de crédito PJ."
    ),
    7326: (
        "Reservas internacionais sob o conceito de liquidez. Colchão de "
        "segurança do país para obrigações externas e estabilidade cambial."
    ),
    27574: (
        "Mediana das expectativas do mercado para o IPCA acumulado nos "
        "próximos 12 meses. Pesquisa Focus do Banco Central."
    ),
    27575: (
        "Mediana das expectativas do mercado para a taxa Selic no fim "
        "do ano corrente. Pesquisa Focus do Banco Central."
    ),
}


# =============================================================================
# Funcoes auxiliares
# =============================================================================


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_serie(codigo: int, inicio: str, fim: str) -> pd.DataFrame:
    """Busca serie com cache do Streamlit (1 hora)."""
    try:
        df = sgs.get(codigo, start=inicio, end=fim)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar série {codigo}: {e}")
        return pd.DataFrame(columns=["valor"])


@st.cache_data(ttl=3600, show_spinner=False)
def buscar_serie_last(codigo: int, n: int) -> pd.DataFrame:
    """Busca ultimos N valores com cache."""
    try:
        df = sgs.get(codigo, last=n)
        return df
    except Exception as e:
        st.error(f"Erro ao buscar série {codigo}: {e}")
        return pd.DataFrame(columns=["valor"])


def calcular_datas(periodo_dias):
    """Retorna inicio e fim baseado no periodo selecionado."""
    fim = date.today()
    if periodo_dias is None:
        inicio = date(1960, 1, 1)
    else:
        inicio = fim - timedelta(days=periodo_dias)
    return inicio.isoformat(), fim.isoformat()


def formatar_valor(valor: float, unidade: str) -> str:
    """Formata valor com unidade."""
    if "R$" in unidade:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if "US$" in unidade:
        return f"US$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if "%" in unidade:
        return f"{valor:.4f}%"
    return f"{valor:.4f}"


def calcular_variacao(df: pd.DataFrame) -> dict:
    """Calcula variacoes da serie."""
    if df.empty or len(df) < 2:
        return {"ultimo": None, "var_abs": None, "var_pct": None}

    ultimo = df["valor"].iloc[-1]
    penultimo = df["valor"].iloc[-2]
    var_abs = ultimo - penultimo
    var_pct = (var_abs / penultimo * 100) if penultimo != 0 else 0

    return {"ultimo": ultimo, "var_abs": var_abs, "var_pct": var_pct}


def criar_grafico_serie(df: pd.DataFrame, nome: str, unidade: str, cor: str = CORES[0]):
    """Cria grafico Plotly para uma serie."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["valor"],
            mode="lines",
            name=nome,
            line=dict(color=cor, width=2),
            hovertemplate=f"<b>{nome}</b><br>"
            + "Data: %{x|%d/%m/%Y}<br>"
            + f"Valor: %{{y:.4f}} {unidade}<extra></extra>",
        )
    )
    fig.update_layout(
        title=dict(text=f"{nome} ({unidade})", font=dict(size=18)),
        xaxis_title="Data",
        yaxis_title=unidade,
        hovermode="x unified",
        template="plotly_white",
        height=450,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig


def criar_grafico_comparacao(series_data: list):
    """Cria grafico com multiplas series e eixo Y duplo se necessario."""
    unidades = list(set(item["unidade"] for item in series_data))
    usar_eixo_duplo = len(unidades) > 1

    if usar_eixo_duplo:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()

    for i, item in enumerate(series_data):
        cor = CORES[i % len(CORES)]
        secondary = usar_eixo_duplo and item["unidade"] == unidades[1]

        trace = go.Scatter(
            x=item["df"].index,
            y=item["df"]["valor"],
            mode="lines",
            name=f"{item['nome']} ({item['unidade']})",
            line=dict(color=cor, width=2),
            hovertemplate=f"<b>{item['nome']}</b><br>"
            + "Data: %{x|%d/%m/%Y}<br>"
            + f"Valor: %{{y:.4f}} {item['unidade']}<extra></extra>",
        )

        if usar_eixo_duplo:
            fig.add_trace(trace, secondary_y=secondary)
        else:
            fig.add_trace(trace)

    titulo = " vs ".join(item["nome"] for item in series_data)
    fig.update_layout(
        title=dict(text=titulo, font=dict(size=18)),
        hovermode="x unified",
        template="plotly_white",
        height=500,
        margin=dict(l=60, r=60, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    if usar_eixo_duplo:
        fig.update_yaxes(title_text=unidades[0], secondary_y=False)
        fig.update_yaxes(title_text=unidades[1], secondary_y=True)
    else:
        fig.update_yaxes(title_text=unidades[0])

    return fig


def df_para_excel(df: pd.DataFrame) -> bytes:
    """Converte DataFrame para bytes Excel."""
    output = io.BytesIO()
    df.to_excel(output, index=True, engine="openpyxl")
    return output.getvalue()


# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.title("📊 BacenData")
    st.caption("Indicadores do Banco Central do Brasil")
    st.divider()

    # Navegacao principal
    pagina = st.radio(
        "Navegação",
        ["Indicadores", "Comparar séries", "Sobre"],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()

    if pagina == "Indicadores":
        # Selecao por categoria
        categoria = st.selectbox(
            "Categoria",
            list(CATEGORIAS.keys()),
            index=0,
        )

        # Series da categoria
        codigos_cat = CATEGORIAS[categoria]
        opcoes = {f"{CATALOGO[c].nome} ({c})": c for c in codigos_cat}
        serie_selecionada = st.selectbox(
            "Série",
            list(opcoes.keys()),
            index=0,
        )
        codigo_selecionado = opcoes[serie_selecionada]

        # Descrição da série selecionada
        desc = DESCRICOES_DETALHADAS.get(codigo_selecionado, "")
        if desc:
            st.info(desc, icon="ℹ️")

    elif pagina == "Comparar séries":
        # Comparacao: ate 3 series
        st.markdown("**Selecione até 3 séries:**")
        todas_opcoes = {f"{s.nome} ({s.codigo})": s.codigo for s in listar()}
        series_comparar = st.multiselect(
            "Séries para comparar",
            list(todas_opcoes.keys()),
            default=list(todas_opcoes.keys())[:2],
            max_selections=3,
        )
        codigos_comparar = [todas_opcoes[s] for s in series_comparar]

    if pagina in ("Indicadores", "Comparar séries"):
        st.divider()

        # Determinar se a serie permite escala diaria
        permite_dias = True
        if pagina == "Indicadores":
            permite_dias = CATALOGO[codigo_selecionado].periodicidade in ("diária", "semanal")
        elif pagina == "Comparar séries" and codigos_comparar:
            permite_dias = all(
                CATALOGO[c].periodicidade in ("diária", "semanal") for c in codigos_comparar
            )

        # Seletor de periodo
        escalas = ["Dias", "Meses", "Anos"] if permite_dias else ["Meses", "Anos"]
        escala = st.radio("Escala", escalas, horizontal=True, index=len(escalas) - 1)

        if escala == "Dias":
            valor = st.slider("Período (dias)", 1, 30, 7)
            periodo_dias = valor
            periodo_label = f"{valor}d"
        elif escala == "Meses":
            valor = st.slider("Período (meses)", 1, 12, 3)
            periodo_dias = valor * 30
            periodo_label = f"{valor}m"
        else:
            opcoes_anos = list(range(1, 11)) + ["Máximo"]
            valor = st.select_slider("Período (anos)", options=opcoes_anos, value=1)
            if valor == "Máximo":
                periodo_dias = None
                periodo_label = "max"
            else:
                periodo_dias = valor * 365
                periodo_label = f"{valor}a"

        st.divider()

        # Media movel
        media_movel = st.checkbox("Média móvel", value=False)
        if media_movel:
            if permite_dias:
                janela_mm = st.slider("Janela (períodos/dias)", min_value=5, max_value=90, value=30)
            else:
                janela_mm = st.slider("Janela (meses)", min_value=2, max_value=24, value=6)

    st.divider()
    st.markdown(
        "**Dados:** [Banco Central — SGS](https://www3.bcb.gov.br/sgspub/)  \n"
        "**Wrapper:** `pip install bacendata`  \n"
        "**API REST:** [Documentação](/docs)  \n"
        "**GitHub:** [fmaignacio/bacendata](https://github.com/fmaignacio/bacendata)"
    )


# =============================================================================
# Conteudo principal
# =============================================================================

if pagina == "Indicadores":
    # =========================================================================
    # MODO: Serie unica
    # =========================================================================
    inicio, fim = calcular_datas(periodo_dias)
    info = CATALOGO[codigo_selecionado]

    st.header(f"{info.nome}", divider="blue")
    st.caption(
        f"Código SGS: {info.codigo} · Periodicidade: {info.periodicidade} · "
        f"Unidade: {info.unidade}"
    )

    # Buscar dados
    with st.spinner(f"Buscando {info.nome}..."):
        df = buscar_serie(codigo_selecionado, inicio, fim)

    if df.empty:
        st.warning(f"Nenhum dado encontrado para {info.nome} no período selecionado.")
        st.stop()

    # Cards com resumo
    stats = calcular_variacao(df)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Último valor",
            value=(formatar_valor(stats["ultimo"], info.unidade) if stats["ultimo"] else "—"),
        )

    with col2:
        if stats["var_abs"] is not None:
            st.metric(
                label="Variação",
                value=f"{stats['var_abs']:+.4f}",
                delta=f"{stats['var_pct']:+.2f}%",
            )

    with col3:
        st.metric(label="Registros", value=f"{len(df):,}".replace(",", "."))

    with col4:
        periodo_str = (
            f"{df.index[0].strftime('%d/%m/%Y')} a " f"{df.index[-1].strftime('%d/%m/%Y')}"
        )
        st.metric(label="Período", value=periodo_str)

    # Grafico
    fig = criar_grafico_serie(df, info.nome, info.unidade)

    # Media movel
    if media_movel and len(df) > janela_mm:
        df_mm = df["valor"].rolling(window=janela_mm).mean()
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df_mm,
                mode="lines",
                name=f"MM{janela_mm}",
                line=dict(color=CORES[1], width=1.5, dash="dash"),
            )
        )

    st.plotly_chart(fig, width="stretch")

    # Tabela e download
    st.subheader("Dados")

    col_tabela, col_download = st.columns([3, 1])

    with col_download:
        csv = df.to_csv()
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"bacendata_{info.codigo}_{periodo_label}.csv",
            mime="text/csv",
        )

        excel = df_para_excel(df)
        st.download_button(
            label="📥 Baixar Excel",
            data=excel,
            file_name=f"bacendata_{info.codigo}_{periodo_label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_tabela:
        df_display = df.copy()
        df_display.index = df_display.index.strftime("%d/%m/%Y")
        df_display = df_display.sort_index(ascending=False).head(50)
        df_display.columns = [f"Valor ({info.unidade})"]
        st.dataframe(df_display, width="stretch", height=400)

    # Info da serie
    with st.expander("Sobre esta série"):
        desc = DESCRICOES_DETALHADAS.get(info.codigo, info.descricao)
        st.markdown(desc)
        st.markdown(f"""
- **Código SGS:** {info.codigo}
- **Nome completo:** {info.descricao}
- **Periodicidade:** {info.periodicidade}
- **Unidade:** {info.unidade}
- **Aliases (wrapper):** `{', '.join(info.aliases)}`
- **Usar no Python:** `sgs.get({info.codigo})` ou `sgs.get("{info.aliases[0]}")`
        """)


elif pagina == "Comparar séries":
    # =========================================================================
    # MODO: Comparacao de series
    # =========================================================================
    inicio, fim = calcular_datas(periodo_dias)

    st.header("Comparar séries", divider="blue")

    if len(codigos_comparar) < 2:
        st.info("Selecione pelo menos 2 séries na barra lateral para comparar.")
        st.stop()

    # Buscar todas as series
    series_data = []
    with st.spinner("Buscando séries..."):
        for codigo in codigos_comparar:
            info = CATALOGO[codigo]
            df = buscar_serie(codigo, inicio, fim)
            if not df.empty:
                series_data.append(
                    {"codigo": codigo, "nome": info.nome, "unidade": info.unidade, "df": df}
                )

    if len(series_data) < 2:
        st.warning("Não foi possível obter dados suficientes para comparação.")
        st.stop()

    # Cards resumo
    cols = st.columns(len(series_data))
    for i, item in enumerate(series_data):
        stats = calcular_variacao(item["df"])
        with cols[i]:
            st.metric(
                label=item["nome"],
                value=(
                    formatar_valor(stats["ultimo"], item["unidade"]) if stats["ultimo"] else "—"
                ),
                delta=f"{stats['var_pct']:+.2f}%" if stats["var_pct"] is not None else None,
            )

    # Grafico de comparacao
    fig = criar_grafico_comparacao(series_data)

    # Media movel na comparação
    if media_movel:
        for i, item in enumerate(series_data):
            if len(item["df"]) > janela_mm:
                df_mm = item["df"]["valor"].rolling(window=janela_mm).mean()
                fig.add_trace(
                    go.Scatter(
                        x=item["df"].index,
                        y=df_mm,
                        mode="lines",
                        name=f"{item['nome']} MM{janela_mm}",
                        line=dict(color=CORES[i % len(CORES)], width=1.5, dash="dash"),
                        showlegend=True,
                    )
                )

    st.plotly_chart(fig, width="stretch")

    # Tabela combinada
    st.subheader("Dados comparados")

    df_combined = pd.DataFrame()
    for item in series_data:
        df_combined[f"{item['nome']} ({item['unidade']})"] = item["df"]["valor"]

    df_combined = df_combined.sort_index(ascending=False)

    col_tab, col_dl = st.columns([3, 1])

    with col_dl:
        csv = df_combined.to_csv()
        st.download_button(
            label="📥 Baixar CSV",
            data=csv,
            file_name=f"bacendata_comparacao_{periodo_label}.csv",
            mime="text/csv",
        )

        excel = df_para_excel(df_combined)
        st.download_button(
            label="📥 Baixar Excel",
            data=excel,
            file_name=f"bacendata_comparacao_{periodo_label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    with col_tab:
        df_display = df_combined.copy()
        df_display.index = df_display.index.strftime("%d/%m/%Y")
        st.dataframe(df_display.head(50), width="stretch", height=400)

    # Correlacao
    if len(series_data) >= 2:
        with st.expander("Correlação entre séries", expanded=True):
            df_corr = df_combined.dropna()
            if len(df_corr) > 10:
                corr = df_corr.corr()

                fig_corr = go.Figure(
                    data=go.Heatmap(
                        z=corr.values,
                        x=corr.columns,
                        y=corr.columns,
                        colorscale="RdBu_r",
                        zmin=-1,
                        zmax=1,
                        text=corr.round(3).values,
                        texttemplate="%{text}",
                        textfont=dict(size=14),
                    )
                )
                fig_corr.update_layout(
                    title="Matriz de Correlação de Pearson",
                    height=400,
                    template="plotly_white",
                )
                st.plotly_chart(fig_corr, width="stretch")

                st.caption(
                    "Correlação de Pearson: valores próximos de 1.0 indicam que as séries "
                    "se movem na mesma direção; próximos de -1.0 indicam direções opostas; "
                    "próximos de 0 indicam ausência de relação linear."
                )
            else:
                st.info("Dados insuficientes para calcular correlação neste período.")


elif pagina == "Sobre":
    # =========================================================================
    # PAGINA: Sobre o projeto
    # =========================================================================
    st.header("Sobre o BacenData", divider="blue")

    st.markdown("""
O **BacenData** é uma plataforma open source que simplifica o acesso a dados
públicos do Banco Central do Brasil. Oferecemos um wrapper Python, uma API REST
e este dashboard interativo.
    """)

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("O problema")
        st.markdown("""
Em março de 2025, o Banco Central impôs novas limitações à API SGS:

- Consultas limitadas a **10 anos** por requisição
- **Filtro de datas obrigatório** (antes era opcional)
- Portal de dados com UX deficiente
- Sem dashboards prontos para análise rápida

O BacenData resolve isso com **paginação automática** — consulte qualquer
período, de qualquer tamanho, em uma única chamada.
        """)

    with col_right:
        st.subheader("A solução")
        st.markdown("""
- **Wrapper Python** — `pip install bacendata` — consulte séries
  do BACEN em 1 linha de código
- **API REST** — endpoints JSON com autenticação, rate limiting
  e documentação automática (OpenAPI/Swagger)
- **Dashboard** — este painel interativo com gráficos, download
  de dados e comparação de séries
- **Paginação automática** — consultas de qualquer período são
  divididas automaticamente em chunks de 10 anos
        """)

    st.divider()

    st.subheader("Como usar o wrapper Python")
    st.code(
        """# Instalar
pip install bacendata

# Importar
from bacendata import sgs

# Série única (por código ou nome)
selic = sgs.get(11, start="2020-01-01")
selic = sgs.get("selic", start="2020-01-01")

# Últimos N valores
ipca = sgs.get("ipca", last=12)

# Múltiplas séries de uma vez
df = sgs.get({"Selic": 11, "IPCA": 433}, start="2015-01-01")

# Período longo (paginação automática > 10 anos)
dolar = sgs.get("dolar", start="1990-01-01")

# Metadados
meta = sgs.metadata(11)
""",
        language="python",
    )

    st.divider()

    st.subheader("Séries disponíveis")
    st.markdown(
        "O catálogo inclui as séries mais demandadas do mercado financeiro. "
        "Você também pode consultar qualquer série SGS pelo código numérico."
    )

    # Tabela de séries do catálogo
    dados_catalogo = []
    for serie in listar():
        dados_catalogo.append(
            {
                "Código": serie.codigo,
                "Nome": serie.nome,
                "Periodicidade": serie.periodicidade,
                "Unidade": serie.unidade,
                "Aliases": ", ".join(serie.aliases),
            }
        )
    df_cat = pd.DataFrame(dados_catalogo)
    st.dataframe(df_cat, width="stretch", hide_index=True)

    st.divider()

    st.subheader("Links")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
**Wrapper Python**
- [PyPI](https://pypi.org/project/bacendata/)
- `pip install bacendata`
        """)
    with col2:
        st.markdown("""
**API REST**
- Rode localmente: `uvicorn bacendata.api.app:create_app --factory`
- Docs: `/docs` (Swagger UI)
        """)
    with col3:
        st.markdown("""
**Código fonte**
- [GitHub](https://github.com/fmaignacio/bacendata)
- Licença MIT
        """)

    st.divider()
    st.caption(
        "BacenData — Dados abertos do Banco Central do Brasil, simplificados. "
        "Desenvolvido com Python, FastAPI e Streamlit."
    )
