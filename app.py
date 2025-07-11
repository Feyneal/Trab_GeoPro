# ============================
# 🔥 DASHBOARD DE REGIME DE FOGO EM TERRAS INDÍGENAS DA AMAZÔNIA
# ============================

# Bibliotecas
import os
import pandas as pd
import geopandas as gpd
import numpy as np
import streamlit as st
import folium
import branca.colormap as cm
import matplotlib.pyplot as plt
from streamlit_folium import st_folium

# ============================
# ⚙️ CONFIGURAÇÃO E CAMINHOS
# ============================
BASE_DIR = os.path.dirname(__file__)

TI_GEOJSON = os.path.join(BASE_DIR, "data", "TIS_amazonia.geojson")
CSV_ANUAL_AQ = os.path.join(BASE_DIR, "data", "CSV_Anual", "AreaQueimada_Anual")
CSV_ANUAL_FC = os.path.join(BASE_DIR, "data", "CSV_Anual", "FocosCalor_Anual")
CSV_TRIMESTRAL_AQ = os.path.join(BASE_DIR, "data", "CSV_Trimestral", "AQ_trimestral")
CSV_TRIMESTRAL_FC = os.path.join(BASE_DIR, "data", "CSV_Trimestral", "FC_trimestral")

trimestres_nome = {
    "1": "Começo da estação seca (Mai-Jun-Jul)",
    "2": "Estação seca (Ago-Set-Out)",
    "3": "Começo da estação húmida (Nov-Dez-Jan)",
    "4": "Estação húmida (Fev-Mar-Abr)"
}
mapa_trimestres = {
    "1": [5, 6, 7],
    "2": [8, 9, 10],
    "3": [11, 12, 1],
    "4": [2, 3, 4]
}

# ============================
# 🌍 CARREGAMENTO DOS DADOS
# ============================
try:
    gdf_tis = gpd.read_file(TI_GEOJSON)
    gdf_tis["TI_nome"] = gdf_tis["Nome_TI"].astype(str)
    gdf_tis = gdf_tis.to_crs(epsg=4326)
except Exception as e:
    st.error(f"Erro ao carregar o GeoJSON: {e}")
    st.stop()

# ============================
# 🖼️ INTERFACE DO USUÁRIO
# ============================
st.set_page_config(layout="wide")
st.title("🔥 Regime de fogo em Terras Indígenas da Amazônia ao longo dos anos")

# Títulos principais
col1, col2 = st.columns([2, 1])
with col1:
    st.header("📊 Tabela de Área de Incêndio Florestal e Focos de Calor")
with col2:
    st.header("📈 Evolução Temporal de Área Queimada (ha) e Focos de Calor")

# Barra lateral com filtros
st.sidebar.header("🎛️ Filtros de Análise")
ano = st.sidebar.selectbox("Selecione o ano", list(range(2012, 2024)), index=0)
trimestre_nome = st.sidebar.selectbox("Selecione o trimestre", list(trimestres_nome.values()))
trimestre = [k for k, v in trimestres_nome.items() if v == trimestre_nome][0]
ti_escolhida = st.sidebar.selectbox("Selecione a Terra Indígena", gdf_tis["TI_nome"])

# ============================
# 📊 TABELA DE DADOS
# ============================
dados_tabela = []
meses_trimestre = mapa_trimestres[trimestre]

for ti in gdf_tis["TI_nome"]:
    try:
        # Caminhos dos CSVs
        aq_anual = pd.read_csv(os.path.join(CSV_ANUAL_AQ, f"area_queimada_anual_{ti}.csv"))
        fc_anual = pd.read_csv(os.path.join(CSV_ANUAL_FC, f"focos_calor_anual_{ti}.csv"))
        aq_trim = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano}.csv"))
        fc_trim = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano}.csv"))

        # Dados anuais
        area_anual = aq_anual.loc[aq_anual["Ano"] == ano, "Area_Queimada_Anual"].values
        focos_anual = fc_anual.loc[fc_anual["Ano"] == ano, "Focos_Anual"].values
        area_anual = area_anual[0] if len(area_anual) > 0 else "-"
        focos_anual = focos_anual[0] if len(focos_anual) > 0 else "-"

        # Trimestral - área
        aq_trim["Month"] = pd.to_numeric(aq_trim["Month"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            aq_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano - 1}.csv"))
            aq_prev["Month"] = pd.to_numeric(aq_prev["Month"], errors='coerce')
            aq_trim = pd.concat([aq_prev, aq_trim], ignore_index=True)
        area_trim = aq_trim[aq_trim["Month"].isin(meses_trimestre)]["Burned_Area_hectares"].sum()

        # Trimestral - focos
        fc_trim["Mes"] = pd.to_numeric(fc_trim["Mes"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            fc_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano - 1}.csv"))
            fc_prev["Mes"] = pd.to_numeric(fc_prev["Mes"], errors='coerce')
            fc_trim = pd.concat([fc_prev, fc_trim], ignore_index=True)
        focos_trim = fc_trim[fc_trim["Mes"].isin(meses_trimestre)]["Total_Focos"].sum()

    except Exception:
        area_anual = focos_anual = area_trim = focos_trim = "-"

    dados_tabela.append({
        "Terra Indígena": ti,
        "Área Queimada Anual (ha)": area_anual,
        "Focos de Calor Anual": focos_anual,
        "Área Queimada Trimestral (ha)": area_trim,
        "Focos de Calor Trimestral": focos_trim
    })

# ============================
# 📈 GRÁFICO TEMPORAL
# ============================
try:
    aq_df = pd.read_csv(os.path.join(CSV_ANUAL_AQ, f"area_queimada_anual_{ti_escolhida}.csv")).dropna()
    fc_df = pd.read_csv(os.path.join(CSV_ANUAL_FC, f"focos_calor_anual_{ti_escolhida}.csv")).dropna()

    anos = sorted(set(aq_df["Ano"]) & set(fc_df["Ano"]))
    aq_vals = aq_df[aq_df["Ano"].isin(anos)]["Area_Queimada_Anual"].values
    fc_vals = fc_df[fc_df["Ano"].isin(anos)]["Focos_Anual"].values

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(anos, aq_vals, color="red", marker='o', label="Área Queimada (ha)")
    ax.set_ylabel("Área Queimada (ha)", color="red")
    ax.tick_params(axis='y', labelcolor="red")
    ax.set_ylim(0, aq_vals.max() * 1.1)

    ax2 = ax.twinx()
    ax2.plot(anos, fc_vals, color="blue", marker='o', label="Focos de Calor")
    ax2.set_ylabel("Focos de Calor", color="blue")
    ax2.tick_params(axis='y', labelcolor="blue")
    ax2.set_ylim(0, fc_vals.max() * 1.1)

    ax.set_title(f"Comparativo Temporal em {ti_escolhida}")
    ax.set_xlabel("Ano")

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper center", bbox_to_anchor=(0.5, 1.025), ncol=2, frameon=False)

    ax.grid(True)
except Exception as e:
    st.warning(f"Erro ao carregar dados temporais: {e}")

# ============================
# 📋 TABELA + GRÁFICO
# ============================
col_tabela, col_grafico = st.columns([2, 1])
col_tabela.dataframe(pd.DataFrame(dados_tabela))
col_grafico.pyplot(fig)

# ============================
# 🗺️ MAPA TRIMESTRAL
# ============================
st.header("🗺️ Visualização Trimestral no Mapa")

col_areas = []
pontos_focos = []

for _, row in gdf_tis.iterrows():
    try:
        ti = row["TI_nome"]
        geom = row["geometry"]

        # Dados trimestrais de área
        aq_csv = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano}.csv"))
        aq_csv["Month"] = pd.to_numeric(aq_csv["Month"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            aq_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano - 1}.csv"))
            aq_prev["Month"] = pd.to_numeric(aq_prev["Month"], errors='coerce')
            aq_csv = pd.concat([aq_prev, aq_csv], ignore_index=True)
        area_trim = aq_csv[aq_csv["Month"].isin(meses_trimestre)]["Burned_Area_hectares"].sum()

        # Dados trimestrais de focos
        fc_csv = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano}.csv"))
        fc_csv["Mes"] = pd.to_numeric(fc_csv["Mes"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            fc_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano - 1}.csv"))
            fc_prev["Mes"] = pd.to_numeric(fc_prev["Mes"], errors='coerce')
            fc_csv = pd.concat([fc_prev, fc_csv], ignore_index=True)
        focos_trim = fc_csv[fc_csv["Mes"].isin(meses_trimestre)]["Total_Focos"].sum()

        area_ti_km2 = geom.area * (111.32**2)  # área da TI em km²
        area_trim_km2 = area_trim / 100        # área queimada em km²
        proporcao = (area_trim_km2 / area_ti_km2) *100 if area_ti_km2 > 0 else 0

        col_areas.append(proporcao)

        centroid = geom.centroid
        pontos_focos.append({"lat": centroid.y, "lon": centroid.x, "focos": focos_trim})

    except Exception:
        col_areas.append(0)
        centroid = row["geometry"].centroid
        pontos_focos.append({"lat": centroid.y, "lon": centroid.x, "focos": 0})

gdf_tis["rel_area_queimada"] = col_areas

# Mapa folium
centro_y = gdf_tis.geometry.centroid.y.mean()
centro_x = gdf_tis.geometry.centroid.x.mean()
m = folium.Map(location=[centro_y, centro_x], zoom_start=5, tiles="CartoDB positron")

colormap = cm.linear.YlOrRd_09.scale(gdf_tis["rel_area_queimada"].min(), gdf_tis["rel_area_queimada"].max())
colormap.caption = "Área queimada relativa (%)"

# Polígonos coloridos
folium.GeoJson(
    gdf_tis,
    style_function=lambda f: {
        "fillColor": colormap(f["properties"]["rel_area_queimada"]),
        "color": "black",
        "weight": 0.8,
        "fillOpacity": 0.7
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["TI_nome", "rel_area_queimada"],
        aliases=["TI", "Área queimada (%)"],
        localize=True,
        sticky=False
    )
).add_to(m)

# Marcadores de focos
for pt in pontos_focos:
    folium.CircleMarker(
        location=(pt["lat"], pt["lon"]),
        radius=2 + pt["focos"]**0.5,
        color="blue",
        fill=True,
        fill_opacity=0.6,
        tooltip=f"{pt['focos']} focos de calor"
    ).add_to(m)

colormap.add_to(m)
folium.LayerControl().add_to(m)

# Legenda de focos (customizada para tema escuro ou claro)
tema_escuro = st.get_option("theme.base") == "dark"
bg = "#1e1e1e" if tema_escuro else "white"
txt = "white" if tema_escuro else "black"
bord = "#888" if tema_escuro else "#444"

legenda_focos = f"""
<div style='position: fixed; top: 505px; left: 1000px; width: 200px;
     z-index:9999; font-size:13px; background-color: {bg}; color: {txt};
     padding: 10px; border:2px solid {bord}; border-radius:5px; box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>
<b>🔵 Focos de Calor</b><br>
<span>Tamanho proporcional à quantidade<br>de focos no trimestre selecionado.</span>
</div>
"""
m.get_root().html.add_child(folium.Element(legenda_focos))

st_folium(m, width=1000, height=600)
