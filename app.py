import os
import pandas as pd
import geopandas as gpd
import numpy as np
import streamlit as st
import folium
import branca.colormap as cm
import matplotlib.pyplot as plt
from streamlit_folium import st_folium


# --- Caminhos base ---
BASE_DIR = os.path.dirname(__file__)
TI_GEOJSON = os.path.join(BASE_DIR, "data", "TIS_amazonia.geojson")
CSV_ANUAL_AQ = os.path.join(BASE_DIR, "data", "CSV_Anual", "AreaQueimada_Anual")
CSV_ANUAL_FC = os.path.join(BASE_DIR, "data", "CSV_Anual", "FocosCalor_Anual")
CSV_TRIMESTRAL_AQ = os.path.join(BASE_DIR, "data", "CSV_Trimestral", "AQ_trimestral")
CSV_TRIMESTRAL_FC = os.path.join(BASE_DIR, "data", "CSV_Trimestral", "FC_trimestral")

# --- Trimestres nomeados ---
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

# --- Carrega GeoJSON ---
try:
    gdf_tis = gpd.read_file(TI_GEOJSON)
    gdf_tis["TI_nome"] = gdf_tis["Nome_TI"].astype(str)
    gdf_tis = gdf_tis.to_crs(epsg=4326)
except Exception as e:
    st.error(f"Erro ao carregar o GeoJSON: {e}")
    st.stop()
    
# --- Interface ---
st.set_page_config(layout="wide")
st.title("🔥 Regime de fogo em Terras Indígenas da Amazônia ao longo dos anos")

# Seletor lado a lado
col1, col2 = st.columns([2,1])

with col1:
    st.header("📊 Tabela de Área de Incêndio Florestal e Focos de Calor")

with col2:
    st.header("📈 Evolução Temporal de Área Queimada (ha) e Focos de Calor")


col3, col4, col5 = st.columns(3)

with col3:
    ano = st.selectbox("Selecione o ano", list(range(2012, 2024)), index=0)

with col4:
    trimestre_nome = st.selectbox("Selecione o trimestre", list(trimestres_nome.values()))
    trimestre = [k for k, v in trimestres_nome.items() if v == trimestre_nome][0]    

with col5:
    ti_escolhida = st.selectbox("Selecione a Terra Indígena para análise temporal", gdf_tis["TI_nome"])

# --- Tabela combinada: área queimada e focos anuais + trimestrais ---
#st.header("📊 Tabela de Área de Incêndio Florestal e Focos de Calor (Anual e Trimestral)")

dados_tabela = []
meses_trimestre = mapa_trimestres[trimestre]

for ti in gdf_tis["TI_nome"]:
    aq_anual_path = os.path.join(CSV_ANUAL_AQ, f"area_queimada_anual_{ti}.csv")
    fc_anual_path = os.path.join(CSV_ANUAL_FC, f"focos_calor_anual_{ti}.csv")
    aq_trim_path = os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano}.csv")
    fc_trim_path = os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano}.csv")

    area_anual = focos_anual = area_trim = focos_trim = "-"

    try:
        # --- Anual ---
        aq_df = pd.read_csv(aq_anual_path)
        fc_df = pd.read_csv(fc_anual_path)
        area_val = aq_df.loc[aq_df["Ano"] == ano, "Area_Queimada_Anual"].values
        focos_val = fc_df.loc[fc_df["Ano"] == ano, "Focos_Anual"].values

        if len(area_val) > 0:
            area_anual = area_val[0].item() if isinstance(area_val[0], np.generic) else area_val[0]
        if len(focos_val) > 0:
            focos_anual = focos_val[0].item() if isinstance(focos_val[0], np.generic) else focos_val[0]

        # --- Trimestral ---
        aq_df_t = pd.read_csv(aq_trim_path)
        aq_df_t["Month"] = pd.to_numeric(aq_df_t["Month"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            aq_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano - 1}.csv"))
            aq_prev["Month"] = pd.to_numeric(aq_prev["Month"], errors='coerce')
            aq_df_t = pd.concat([aq_prev, aq_df_t], ignore_index=True)
        area_trim = aq_df_t[aq_df_t["Month"].isin(meses_trimestre)]["Burned_Area_hectares"].sum()

        fc_df_t = pd.read_csv(fc_trim_path)
        fc_df_t["Mes"] = pd.to_numeric(fc_df_t["Mes"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            fc_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano - 1}.csv"))
            fc_prev["Mes"] = pd.to_numeric(fc_prev["Mes"], errors='coerce')
            fc_df_t = pd.concat([fc_prev, fc_df_t], ignore_index=True)
        focos_trim = fc_df_t[fc_df_t["Mes"].isin(meses_trimestre)]["Total_Focos"].sum()

    except Exception as e:
        pass

    dados_tabela.append({
        "Terra Indígena": ti,
        "Área Queimada Anual (ha)": area_anual,
        "Focos de Calor Anual": focos_anual,
        "Área Queimada Trimestral (ha)": area_trim,
        "Focos de Calor Trimestral": focos_trim
    })

# Exibe a tabela
#st.dataframe(pd.DataFrame(dados_tabela))

# --- Gráfico de série temporal por TI com dois eixos y (AQ em ha, FC absoluto) ---
#st.header("📈 Evolução Temporal de Área Queimada (ha) e Focos de Calor (absoluto)")

#ti_escolhida = st.selectbox("Selecione a Terra Indígena para análise temporal", gdf_tis["TI_nome"])

csv_aq = os.path.join(CSV_ANUAL_AQ, f"area_queimada_anual_{ti_escolhida}.csv")
csv_fc = os.path.join(CSV_ANUAL_FC, f"focos_calor_anual_{ti_escolhida}.csv")

try:
    aq_df = pd.read_csv(csv_aq)
    fc_df = pd.read_csv(csv_fc)

    aq_df = aq_df.dropna(subset=["Area_Queimada_Anual"])
    fc_df = fc_df.dropna(subset=["Focos_Anual"])

    anos = sorted(set(aq_df["Ano"]) & set(fc_df["Ano"]))

    # Valores absolutos em hectares
    aq_vals_ha = aq_df[aq_df["Ano"].isin(anos)]["Area_Queimada_Anual"].values
    # Valores absolutos focos de calor
    fc_vals = fc_df[fc_df["Ano"].isin(anos)]["Focos_Anual"].values

    fig, ax = plt.subplots(figsize=(10, 5))

    # Eixo principal para AQ em hectares
    ax.plot(anos, aq_vals_ha, color="red", marker='o', label="Área Queimada (ha)")
    ax.set_ylabel("Área Queimada (ha)", color="red")
    ax.tick_params(axis='y', labelcolor="red")
    ax.set_ylim(0, aq_vals_ha.max() * 1.1)  # Limite 10% acima do máximo

    # Eixo secundário para FC absoluto
    ax2 = ax.twinx()
    ax2.plot(anos, fc_vals, color="blue", marker='o', label="Focos de Calor (número)")
    ax2.set_ylabel("Focos de Calor", color="blue")
    ax2.tick_params(axis='y', labelcolor="blue")
    ax2.set_ylim(0, fc_vals.max() * 1.1)

    ax.set_title(f"Comparativo Temporal em {ti_escolhida}")
    ax.set_xlabel("Ano")

    # Legenda combinada
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(
    lines + lines2,
    labels + labels2,
    loc="upper center",
    bbox_to_anchor=(0.5, 1.05),
    ncol=2,
    frameon=False)


    ax.grid(True)

    #st.pyplot(fig)

except Exception as e:
    st.warning(f"Erro ao carregar dados de {ti_escolhida}: {e}")


col6, col7 = st.columns([2,1])

with col6:
    st.dataframe(pd.DataFrame(dados_tabela))
    
with col7:
    st.pyplot(fig)

# --- Mapa Interativo ---
st.header("🗺️ Visualização Trimestral no Mapa")

col_areas = []
pontos_focos = []
meses_trimestre = mapa_trimestres[trimestre]

for _, row in gdf_tis.iterrows():
    ti = row["TI_nome"]
    geom = row["geometry"]
    try:
        # ÁREA QUEIMADA
        aq_csv = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano}.csv"))
        aq_csv["Month"] = pd.to_numeric(aq_csv["Month"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            aq_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_AQ, f"{ti}_{ano - 1}.csv"))
            aq_prev["Month"] = pd.to_numeric(aq_prev["Month"], errors='coerce')
            aq_csv = pd.concat([aq_prev, aq_csv], ignore_index=True)
        area_trimestre = aq_csv[aq_csv["Month"].isin(meses_trimestre)]["Burned_Area_hectares"].sum()

        # FOCOS DE CALOR
        fc_csv = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano}.csv"))
        fc_csv["Mes"] = pd.to_numeric(fc_csv["Mes"], errors='coerce')
        if 1 in meses_trimestre and ano > 2012:
            fc_prev = pd.read_csv(os.path.join(CSV_TRIMESTRAL_FC, f"{ti}_{ano - 1}.csv"))
            fc_prev["Mes"] = pd.to_numeric(fc_prev["Mes"], errors='coerce')
            fc_csv = pd.concat([fc_prev, fc_csv], ignore_index=True)
        focos_trimestre = fc_csv[fc_csv["Mes"].isin(meses_trimestre)]["Total_Focos"].sum()

        # Área relativa normalizada
        area_ti = geom.area * (111.32**2)
        rel = area_trimestre / area_ti if area_ti > 0 else 0
        col_areas.append(rel)

        centroid = geom.centroid
        pontos_focos.append({
            "lat": centroid.y,
            "lon": centroid.x,
            "focos": focos_trimestre
        })

    except Exception as e:
        col_areas.append(0)
        centroid = geom.centroid
        pontos_focos.append({"lat": centroid.y, "lon": centroid.x, "focos": 0})

gdf_tis["rel_area_queimada"] = col_areas

# --- Mapa folium ---
centro_y = gdf_tis.geometry.centroid.y.mean()
centro_x = gdf_tis.geometry.centroid.x.mean()
m = folium.Map(location=[centro_y, centro_x], zoom_start=5, tiles="CartoDB positron")

# Multiplica a proporção para converter em %
gdf_tis["rel_area_queimada"] = gdf_tis["rel_area_queimada"] * 100

# Criar colormap em porcentagem
colormap = cm.linear.YlOrRd_09.scale(
    gdf_tis["rel_area_queimada"].min(),
    gdf_tis["rel_area_queimada"].max()
)
colormap.caption = "Área queimada relativa (%)"

# Adiciona camada GeoJson colorida
folium.GeoJson(
    gdf_tis,
    name="TI",
    style_function=lambda feature: {
        "fillColor": colormap(feature["properties"]["rel_area_queimada"]),
        "color": "black",
        "weight": 0.8,
        "fillOpacity": 0.7
    },
    tooltip=folium.GeoJsonTooltip(
        fields=["TI_nome", "rel_area_queimada"],
        aliases=["TI", "Área queimada (%)"],
        localize=True,
        sticky=False,
        labels=True,
        style="""
            background-color: #F0EFEF;
            border: 1px solid #CCC;
            border-radius: 3px;
            box-shadow: 3px;
        """
    )
).add_to(m)

# Pontos de focos de calor
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

# Detecta tema atual
tema_escuro = st.get_option("theme.base") == "dark"
bg_color = "#1e1e1e" if tema_escuro else "white"
text_color = "white" if tema_escuro else "black"
border_color = "#888" if tema_escuro else "#444"

legend_html = f"""
<div style='position: fixed;
     top: 505px; left: 1000px; width: 200px; height: auto;
     z-index:9999; font-size:13px;
     background-color: {bg_color};
     color: {text_color};
     padding: 10px;
     border:2px solid {border_color};
     border-radius:5px;
     box-shadow: 2px 2px 5px rgba(0,0,0,0.3);'>

<b style="color:{text_color};">🔵 Focos de Calor</b><br>
<span style="color:{text_color};">
Tamanho proporcional<br>
à quantidade de focos<br>
no trimestre selecionado.
</span>
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))


st_folium(m, width=1000, height=600)

