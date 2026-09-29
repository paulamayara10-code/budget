from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


# =========================================================
# CONFIGURAÇÃO GERAL
# =========================================================
st.set_page_config(
    page_title="First Budget | Planejamento",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_YEAR = 2027
TZ = ZoneInfo("America/Sao_Paulo")

NAVY = "#071B33"
NAVY_2 = "#0B2F55"
BLUE = "#1261A0"
CYAN = "#4F9AD1"
LIGHT = "#F3F6FA"
WHITE = "#FFFFFF"
GRAY = "#667085"
BORDER = "#DDE7F0"
RED = "#B42318"
GREEN = "#067647"

LINES = ["MICROTECH", "LOCACAO", "VENDAS", "ENDOSCOPIA"]
LINE_LABELS = {
    "MICROTECH": "Microtech",
    "LOCACAO": "Locação",
    "VENDAS": "Vendas",
    "ENDOSCOPIA": "Endoscopia",
    "CONSOLIDADO": "Consolidado",
}
MANAGER_LINE_MAP = {
    "CELSO": "MICROTECH",
    "RENATO": "VENDAS",
    "AMAURI": "LOCACAO",
    "RONALDO": "ENDOSCOPIA",
}

MONTHS = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez",
}
PROBABILITY_WEIGHTS = {"Alta": 0.90, "Média": 0.60, "Baixa": 0.30}
TABLE_CACHE_TTL = 20  # reduz chamadas ao GitHub sem esconder alterações por muito tempo
NEW_CLIENT_OPTION = "➕ Novo cliente"
NEW_PRODUCT_OPTION = "➕ Novo equipamento / produto / oportunidade"

FORECAST_COLUMNS = [
    "ID", "Ano", "Linha", "Competencia", "Cliente", "Tipo_Cliente",
    "Tipo_Receita", "Produto_Linha", "Numero_Contrato", "Itens_Contrato_JSON",
    "Quantidade", "Valor_Unitario", "Data_Inicio_Contrato", "Prazo_Contrato_Meses",
    "Data_Fim_Contrato", "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Meses_No_Ano",
    "Receita_Prevista", "Probabilidade", "Peso_Probabilidade",
    "Receita_Ponderada", "Observacao", "Status", "Criado_Por",
    "Criado_Em", "Atualizado_Por", "Atualizado_Em",
]
CONTRACT_ITEM_COLUMNS = ["Equipamento", "Quantidade", "Valor_Mensal_Unitario", "Observacao_Item"]
HISTORY_COLUMNS = [
    "Historico_ID", "Forecast_ID", "Ano", "Linha", "Acao", "Usuario",
    "Data_Hora", "Antes_JSON", "Depois_JSON",
]

BUDGET_REVENUE_COLUMNS = [
    "Ano", "Linha", "Competencia", "Budget_Proposto", "Budget_Aprovado",
    "Status", "Justificativa", "Atualizado_Por", "Atualizado_Em",
]
BUDGET_REVENUE_HISTORY_COLUMNS = [
    "Historico_ID", "Ano", "Linha", "Acao", "Usuario", "Data_Hora",
    "Antes_JSON", "Depois_JSON",
]

ACTIVE_CONTRACT_OVERRIDE_COLUMNS = [
    "Contrato_Key", "Status_2027", "Meses_2027", "Valor_Mensal_Ajustado",
    "Linha_Budget", "Observacao_2027", "Atualizado_Por", "Atualizado_Em",
]
ACTIVE_CONTRACT_STATUS = [
    "REVISAR", "VALIDADO 12 MESES", "VIGENTE PARCIAL", "EM RENOVAÇÃO", "NÃO CONSIDERAR",
]


# =========================================================
# VISUAL
# =========================================================
st.markdown(
    f"""
    <style>
    .stApp {{ background:{LIGHT}; }}
    .block-container {{ max-width:1500px; padding-top:1.05rem; padding-bottom:1.5rem; }}
    [data-testid="stSidebar"] {{ background:linear-gradient(180deg,{NAVY} 0%,{NAVY_2} 100%); }}
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {{ color:#F4F8FC !important; }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3, [data-testid="stSidebar"] h4 {{ color:#FFFFFF !important; }}
    [data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] input {{ background:#FFFFFF; color:{NAVY}; border-radius:10px; }}
    [data-testid="stSidebar"] [data-baseweb="select"] span,
    [data-testid="stSidebar"] input {{ color:{NAVY} !important; }}
    div[data-testid="stButton"] button, div[data-testid="stDownloadButton"] button {{ border-radius:11px; font-weight:800; }}
    div[data-testid="stForm"] {{ background:#FFFFFF; border:1px solid {BORDER}; border-radius:18px; padding:1rem 1.1rem; box-shadow:0 10px 26px rgba(7,27,51,.06); }}
    div[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:14px; overflow:hidden; }}
    [data-testid="stPlotlyChart"] {{ background:#FFFFFF; border:1px solid {BORDER}; border-radius:18px; padding:4px 7px; box-shadow:0 8px 22px rgba(7,27,51,.05); }}

    .first-sidebar {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.11); border-radius:16px; padding:15px 16px; margin-bottom:10px; }}
    .first-sidebar .brand {{ color:#FFFFFF; font-size:1.26rem; font-weight:950; letter-spacing:.14em; line-height:1; }}
    .first-sidebar .brand small {{ display:block; color:#B9D9F0; font-size:.58rem; letter-spacing:.27em; margin-top:6px; }}

    .login-brand {{ text-align:center; margin:3.8rem auto 1.2rem auto; }}
    .login-brand .logo {{ color:{NAVY}; font-size:1.55rem; font-weight:950; letter-spacing:.15em; }}
    .login-brand .logo span {{ color:{BLUE}; }}
    .login-brand p {{ color:{GRAY}; margin:.45rem 0 0; font-size:.82rem; }}

    .hero {{ position:relative; overflow:hidden; background:linear-gradient(120deg,{NAVY} 0%,#0E3762 58%,#1B5D97 120%); color:white; border-radius:22px; padding:22px 24px; margin:4px 0 12px; box-shadow:0 18px 38px rgba(7,27,51,.16); }}
    .hero h1 {{ font-size:1.75rem; margin:5px 0 2px; letter-spacing:-.02em; }}
    .hero p {{ margin:0; opacity:.82; font-size:.87rem; }}
    .hero .eyebrow {{ font-size:.70rem; font-weight:900; letter-spacing:.24em; color:#B9D9F0; text-transform:uppercase; }}

    .kpi {{ background:#FFFFFF; border:1px solid {BORDER}; border-radius:17px; padding:13px 14px; min-height:105px; box-shadow:0 8px 22px rgba(7,27,51,.045); }}
    .kpi .label {{ color:{GRAY}; font-size:.68rem; font-weight:900; letter-spacing:.05em; text-transform:uppercase; }}
    .kpi .value {{ color:{NAVY}; font-size:1.35rem; font-weight:950; margin-top:10px; white-space:nowrap; }}
    .kpi .note {{ color:{GRAY}; font-size:.72rem; margin-top:8px; line-height:1.35; }}

    .section {{ color:{NAVY}; font-size:1.08rem; font-weight:900; margin:15px 0 7px; padding-bottom:7px; border-bottom:1px solid {BORDER}; }}
    .pill {{ display:inline-flex; align-items:center; border-radius:999px; padding:5px 9px; background:#EAF3FA; color:{BLUE}; font-size:.68rem; font-weight:900; }}
    .user-pill {{ display:flex; align-items:center; justify-content:space-between; gap:10px; background:rgba(255,255,255,.09); border:1px solid rgba(255,255,255,.12); border-radius:13px; padding:9px 10px; margin:6px 0 10px; }}
    .user-pill b {{ color:#FFFFFF; font-size:.82rem; display:block; }}
    .user-pill small {{ color:#D8E7F3; font-size:.68rem; display:block; margin-top:2px; }}
    .storage-note {{ background:#EDF4FA; border:1px solid #C9DDED; border-radius:12px; padding:10px 12px; color:#234F74; font-size:.76rem; line-height:1.42; }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# FUNÇÕES GERAIS
# =========================================================
def norm(value: object) -> str:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    import unicodedata
    import re
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\s+", " ", text).strip().upper()
    return text


def brl(value: float) -> str:
    value = float(value or 0)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def pct(value: float) -> str:
    return f"{float(value or 0) * 100:,.1f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def now_text() -> str:
    return datetime.now(TZ).strftime("%d/%m/%Y %H:%M:%S")


def line_label(value: str) -> str:
    return LINE_LABELS.get(norm(value), str(value).title())


def month_label_from_comp(value: str) -> str:
    try:
        p = pd.Period(value, freq="M")
        return f"{MONTHS[p.month]}/{str(p.year)[2:]}"
    except Exception:
        return str(value)


def date_br(value: object) -> str:
    if value is None or str(value).strip() in {"", "nan", "NaT"}:
        return ""
    try:
        return pd.Timestamp(value).strftime("%d/%m/%Y")
    except Exception:
        return str(value)


def _optional_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    lookup = {norm(c): c for c in df.columns}
    for candidate in candidates:
        if norm(candidate) in lookup:
            return lookup[norm(candidate)]
    return None


def _master_base_path() -> Path | None:
    """Localiza a BASE BI no mesmo repositório do Budget, sem acoplar o app ao Intelligence."""
    here = Path(__file__).resolve().parent
    preferred = [
        "BASE BI.xlsx", "BASE BI.xlsm", "BASE BI(1).xlsx",
        "base_bi.xlsx", "rev2026 Base bi.xlsx", "rev2026 Base bi.xlsm",
    ]
    for name in preferred:
        candidate = here / name
        if candidate.exists() and not candidate.name.startswith("~$"):
            return candidate
    candidates = []
    for path in here.glob("*.xls*"):
        if path.name.startswith("~$"):
            continue
        key = norm(path.stem)
        if "BASE" in key and "BI" in key:
            candidates.append(path)
    if not candidates:
        return None
    candidates.sort(key=lambda x: ("REV2026" in norm(x.stem), x.name.casefold()))
    return candidates[0]



def _to_number_series(series: pd.Series) -> pd.Series:
    """Converte valores monetários/números em formatos PT-BR e padrão numérico."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0.0)
    txt = series.astype(str).str.strip().str.replace(r"R\$\s*", "", regex=True).str.replace(" ", "", regex=False)
    both = txt.str.contains(",", na=False) & txt.str.contains(r"\.", na=False)
    txt.loc[both] = txt.loc[both].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    only_comma = txt.str.contains(",", na=False) & ~txt.str.contains(r"\.", na=False)
    txt.loc[only_comma] = txt.loc[only_comma].str.replace(",", ".", regex=False)
    return pd.to_numeric(txt, errors="coerce").fillna(0.0)


def _to_month_period_series(series: pd.Series) -> pd.Series:
    """Converte datas, seriais Excel e rótulos como ago/26 ou 08/2026 em período mensal."""
    dates = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    numeric = pd.to_numeric(series, errors="coerce")
    excel_mask = numeric.notna() & numeric.between(20000, 80000)
    if excel_mask.any():
        dates.loc[excel_mask] = pd.to_datetime(numeric.loc[excel_mask], unit="D", origin="1899-12-30", errors="coerce")
    if (~excel_mask).any():
        dates.loc[~excel_mask] = pd.to_datetime(series.loc[~excel_mask], errors="coerce", dayfirst=True)

    missing = dates.isna()
    if missing.any():
        aliases = {
            "JAN": 1, "JANEIRO": 1, "FEV": 2, "FEVEREIRO": 2, "MAR": 3, "MARCO": 3,
            "ABR": 4, "ABRIL": 4, "MAI": 5, "MAIO": 5, "JUN": 6, "JUNHO": 6,
            "JUL": 7, "JULHO": 7, "AGO": 8, "AGOSTO": 8, "SET": 9, "SETEMBRO": 9,
            "OUT": 10, "OUTUBRO": 10, "NOV": 11, "NOVEMBRO": 11, "DEZ": 12, "DEZEMBRO": 12,
        }
        import re
        for idx, raw in series.loc[missing].items():
            txt = norm(raw)
            if not txt:
                continue
            month = None
            year = None
            numeric_match = re.search(r"\b(0?[1-9]|1[0-2])[\s/\-.]+(20\d{2}|\d{2})\b", txt)
            if numeric_match:
                month = int(numeric_match.group(1))
                year = int(numeric_match.group(2))
            else:
                for token, m in aliases.items():
                    if re.search(rf"\b{token}\b", txt):
                        month = m
                        break
                year_match = re.search(r"\b(20\d{2}|\d{2})\b", txt)
                if year_match:
                    year = int(year_match.group(1))
            if month is not None:
                if year is None:
                    year = APP_YEAR - 1
                if year < 100:
                    year += 2000
                try:
                    dates.loc[idx] = pd.Timestamp(year=year, month=month, day=1)
                except ValueError:
                    pass
    return dates.dt.to_period("M")


@st.cache_data(show_spinner=False, ttl=300)
def _read_sulamita_purchase_history(path_text: str, modified_ns: int) -> dict[str, object]:
    """Calcula a base histórica mensal dos clientes atendidos por Sulamita na BASE BI.

    A média usa até os 12 últimos meses disponíveis antes de 2027 e inclui meses sem compra
    no denominador. Isso evita superestimar distribuidores que compram de forma esporádica.
    """
    path = Path(path_text)
    empty = {
        "detail": pd.DataFrame(), "monthly": pd.DataFrame(), "source": path.name,
        "warning": "", "start": "", "end": "", "months": 0,
        "avg_monthly": 0.0, "annual_projection": 0.0, "clients": 0,
    }
    try:
        header = pd.read_excel(path, sheet_name="BANCO DE DADOS FATURAMENTO", engine="openpyxl", nrows=0)
        client_col = _optional_col(header, ["NOME DO CLIENTE", "CLIENTE", "RAZÃO SOCIAL", "RAZAO SOCIAL"])
        seller_col = _optional_col(header, ["VENDEDOR / REPRESENTANTE", "VENDEDOR", "REPRESENTANTE"])
        month_col = _optional_col(header, ["MÊS", "MES", "COMPETENCIA", "COMPETÊNCIA"])
        date_col = _optional_col(header, ["DT Emissao", "DT EMISSÃO", "DATA EMISSÃO", "DATA EMISSAO"])
        value_col = _optional_col(header, ["VALOR BRUTO", "VALOR ", "VALOR", "FATURAMENTO"])
        manager_col = _optional_col(header, ["GERENTE"])
        segment_col = _optional_col(header, ["SEGMENTO"])
        required = [client_col, seller_col, value_col]
        if any(col is None for col in required) or (month_col is None and date_col is None):
            missing = []
            if client_col is None: missing.append("cliente")
            if seller_col is None: missing.append("vendedor/representante")
            if value_col is None: missing.append("valor")
            if month_col is None and date_col is None: missing.append("mês/data")
            empty["warning"] = "Não foi possível calcular a média Sulamita: faltam colunas de " + ", ".join(missing) + "."
            return empty
        usecols = []
        for col in [client_col, seller_col, month_col, date_col, value_col, manager_col, segment_col]:
            if col and col not in usecols:
                usecols.append(col)
        df = pd.read_excel(path, sheet_name="BANCO DE DADOS FATURAMENTO", engine="openpyxl", usecols=usecols)
    except Exception as exc:
        empty["warning"] = f"Não foi possível ler o histórico Sulamita: {exc}"
        return empty

    seller_n = df[seller_col].fillna("").astype(str).map(norm)
    sulamita = df[seller_n.str.contains("SULAMITA", regex=False, na=False)].copy()
    if sulamita.empty:
        empty["warning"] = "Nenhum faturamento da Sulamita foi localizado na BASE BI."
        return empty

    official = _to_month_period_series(sulamita[month_col]) if month_col else pd.Series(pd.NaT, index=sulamita.index)
    if date_col:
        fallback = _to_month_period_series(sulamita[date_col])
        official = official.where(official.notna(), fallback)
    sulamita["_MES"] = official
    sulamita["_VALOR"] = _to_number_series(sulamita[value_col])
    sulamita["_CLIENTE"] = sulamita[client_col].fillna("").astype(str).str.strip()
    sulamita = sulamita[
        sulamita["_MES"].notna()
        & sulamita["_CLIENTE"].map(norm).ne("")
        & sulamita["_MES"].map(lambda p: p.year if isinstance(p, pd.Period) else 9999).lt(APP_YEAR)
    ].copy()
    if sulamita.empty:
        empty["warning"] = f"Não há histórico Sulamita anterior a {APP_YEAR} com competência válida."
        return empty

    end = sulamita["_MES"].max()
    start = max(sulamita["_MES"].min(), end - 11)
    window = pd.period_range(start=start, end=end, freq="M")
    months_count = len(window)
    sulamita = sulamita[sulamita["_MES"].isin(window)].copy()

    monthly_client = (
        sulamita.groupby(["_CLIENTE", "_MES"], as_index=False)["_VALOR"].sum()
        .rename(columns={"_CLIENTE": "Cliente", "_MES": "Competencia", "_VALOR": "Valor"})
    )
    clients = sorted(monthly_client["Cliente"].dropna().astype(str).unique(), key=norm)
    grid = pd.MultiIndex.from_product([clients, list(window)], names=["Cliente", "Competencia"]).to_frame(index=False)
    grid = grid.merge(monthly_client, on=["Cliente", "Competencia"], how="left")
    grid["Valor"] = pd.to_numeric(grid["Valor"], errors="coerce").fillna(0.0)

    recent_window = list(window[-3:]) if months_count >= 3 else list(window)
    detail_rows = []
    for client, grp in grid.groupby("Cliente", sort=False):
        total = float(grp["Valor"].sum())
        active_months = int(grp["Valor"].gt(0).sum())
        avg = total / months_count if months_count else 0.0
        recent = grp[grp["Competencia"].isin(recent_window)]
        recent_avg = float(recent["Valor"].sum()) / len(recent_window) if recent_window else 0.0
        frequency = active_months / months_count if months_count else 0.0
        if total == 0 and active_months == 0:
            continue
        detail_rows.append({
            "Cliente": client,
            "Total_Historico": total,
            "Meses_Com_Compra": active_months,
            "Meses_Base": months_count,
            "Frequencia_Compra": frequency,
            "Media_Mensal": avg,
            "Media_3M": recent_avg,
            "Projecao_2027": avg * 12,
        })
    detail = pd.DataFrame(detail_rows)
    if not detail.empty:
        detail = detail.sort_values("Projecao_2027", ascending=False).reset_index(drop=True)

    monthly = grid.groupby("Competencia", as_index=False)["Valor"].sum().rename(columns={"Valor": "Faturamento_Sulamita"})
    avg_monthly = float(monthly["Faturamento_Sulamita"].sum()) / months_count if months_count else 0.0
    return {
        "detail": detail,
        "monthly": monthly,
        "source": path.name,
        "warning": "",
        "start": str(start),
        "end": str(end),
        "months": months_count,
        "avg_monthly": avg_monthly,
        "annual_projection": avg_monthly * 12,
        "clients": int(len(detail)),
    }


@st.cache_data(show_spinner=False, ttl=300)
def _read_master_catalog(path_text: str, modified_ns: int) -> dict[str, object]:
    """Lê clientes e catálogo de produtos da BASE BI com metadados para busca em várias camadas."""
    path = Path(path_text)
    try:
        book = pd.ExcelFile(path, engine="openpyxl")
        if "BANCO DE DADOS FATURAMENTO" not in book.sheet_names:
            return {
                "clients": [], "products": [], "client_records": [], "product_records": [],
                "source": path.name, "warning": "A aba BANCO DE DADOS FATURAMENTO não foi localizada."
            }
        header = pd.read_excel(path, sheet_name="BANCO DE DADOS FATURAMENTO", engine="openpyxl", nrows=0)
        candidate_groups = [
            ["NOME DO CLIENTE", "CLIENTE", "RAZÃO SOCIAL", "RAZAO SOCIAL"],
            ["COD CLIENTE", "CÓD CLIENTE", "CODIGO CLIENTE", "CÓDIGO CLIENTE", "COD. CLIENTE", "CLIENTE CODIGO", "CLIENTE"],
            ["VENDEDOR / REPRESENTANTE", "VENDEDOR", "REPRESENTANTE"], ["GERENTE"],
            ["CIDADE", "MUNICIPIO", "MUNICÍPIO"], ["UF", "ESTADO"], ["SEGMENTO"],
            ["PRODUTO", "ITEM", "CÓDIGO PRODUTO", "CODIGO PRODUTO", "COD PRODUTO", "CÓD PRODUTO"],
            ["DESCRIÇÃO", "DESCRICAO", "DESC PRODUTO", "DESCRIÇÃO PRODUTO"],
            ["LINHA DE PRODUTO", "LINHA PRODUTO", "LINHA"],
            ["GRUPO", "GRUPO PRODUTO", "GRUPO DE PRODUTO", "CATEGORIA", "FAMILIA", "FAMÍLIA"],
            ["FORNECEDOR", "FABRICANTE", "MARCA"], ["NCM", "COD NCM", "CÓDIGO NCM", "CODIGO NCM"],
        ]
        needed_cols = []
        for group in candidate_groups:
            found = _optional_col(header, group)
            if found and found not in needed_cols:
                needed_cols.append(found)
        df = pd.read_excel(
            path,
            sheet_name="BANCO DE DADOS FATURAMENTO",
            engine="openpyxl",
            usecols=needed_cols or None,
        )
    except Exception as exc:
        return {
            "clients": [], "products": [], "client_records": [], "product_records": [],
            "source": path.name, "warning": f"Não foi possível ler a BASE BI: {exc}"
        }

    # Clientes: nome + código + vendedor/gerente + UF/cidade/segmento quando disponíveis.
    client_name_col = _optional_col(df, ["NOME DO CLIENTE", "CLIENTE", "RAZÃO SOCIAL", "RAZAO SOCIAL"])
    client_code_col = _optional_col(df, ["COD CLIENTE", "CÓD CLIENTE", "CODIGO CLIENTE", "CÓDIGO CLIENTE", "COD. CLIENTE", "CLIENTE CODIGO", "CLIENTE"])
    seller_col = _optional_col(df, ["VENDEDOR / REPRESENTANTE", "VENDEDOR", "REPRESENTANTE"])
    manager_col = _optional_col(df, ["GERENTE"])
    city_col = _optional_col(df, ["CIDADE", "MUNICIPIO", "MUNICÍPIO"])
    uf_col = _optional_col(df, ["UF", "ESTADO"])
    segment_col = _optional_col(df, ["SEGMENTO"])

    client_records_by_key: dict[str, dict[str, object]] = {}
    if client_name_col:
        for _, row in df.iterrows():
            name = str(row.get(client_name_col, "") or "").strip()
            if not name or norm(name) in {"NAO INFORMADO", "NAN", "NONE"}:
                continue
            key = norm(name)
            rec = client_records_by_key.setdefault(key, {
                "value": name, "code": set(), "seller": set(), "manager": set(),
                "city": set(), "uf": set(), "segment": set(),
            })
            for field, col in [
                ("code", client_code_col), ("seller", seller_col), ("manager", manager_col),
                ("city", city_col), ("uf", uf_col), ("segment", segment_col),
            ]:
                if col:
                    value = str(row.get(col, "") or "").strip()
                    if value and norm(value) not in {"NAO INFORMADO", "NAN", "NONE"}:
                        rec[field].add(value)

    client_records = []
    for rec in client_records_by_key.values():
        clean = {k: (" / ".join(sorted(v, key=norm)) if isinstance(v, set) else v) for k, v in rec.items()}
        clean["search_blob"] = " | ".join(str(clean.get(k, "")) for k in ["value", "code", "seller", "manager", "city", "uf", "segment"])
        clean["_search_blob_n"] = norm(clean["search_blob"])
        clean["_value_n"] = norm(clean.get("value", ""))
        clean["_code_n"] = norm(clean.get("code", ""))
        clean["_description_n"] = ""
        client_records.append(clean)
    client_records.sort(key=lambda r: norm(r["value"]))
    clients = [r["value"] for r in client_records]

    # Produtos: código + descrição + linha + grupo/categoria + segmento + fornecedor + NCM.
    product_col = _optional_col(df, ["PRODUTO", "ITEM", "CÓDIGO PRODUTO", "CODIGO PRODUTO", "COD PRODUTO", "CÓD PRODUTO"])
    desc_col = _optional_col(df, ["DESCRIÇÃO", "DESCRICAO", "DESC PRODUTO", "DESCRIÇÃO PRODUTO"])
    line_col = _optional_col(df, ["LINHA DE PRODUTO", "LINHA PRODUTO", "LINHA"])
    group_col = _optional_col(df, ["GRUPO", "GRUPO PRODUTO", "GRUPO DE PRODUTO", "CATEGORIA", "FAMILIA", "FAMÍLIA"])
    supplier_col = _optional_col(df, ["FORNECEDOR", "FABRICANTE", "MARCA"])
    ncm_col = _optional_col(df, ["NCM", "COD NCM", "CÓDIGO NCM", "CODIGO NCM"])

    product_records_by_key: dict[str, dict[str, object]] = {}
    for _, row in df.iterrows():
        code = str(row.get(product_col, "") or "").strip() if product_col else ""
        desc = str(row.get(desc_col, "") or "").strip() if desc_col else ""
        if norm(code) in {"NAN", "NONE", "NAO INFORMADO"}:
            code = ""
        if norm(desc) in {"NAN", "NONE", "NAO INFORMADO"}:
            desc = ""
        canonical = f"{code} | {desc}" if code and desc and norm(code) != norm(desc) else (code or desc)
        if not canonical:
            continue
        key = norm(canonical)
        rec = product_records_by_key.setdefault(key, {
            "value": canonical, "code": code, "description": desc,
            "line": set(), "group": set(), "segment": set(), "supplier": set(), "ncm": set(),
        })
        for field, col in [
            ("line", line_col), ("group", group_col), ("segment", segment_col),
            ("supplier", supplier_col), ("ncm", ncm_col),
        ]:
            if col:
                value = str(row.get(col, "") or "").strip()
                if value and norm(value) not in {"NAO INFORMADO", "NAN", "NONE"}:
                    rec[field].add(value)

    product_records = []
    for rec in product_records_by_key.values():
        clean = {k: (" / ".join(sorted(v, key=norm)) if isinstance(v, set) else v) for k, v in rec.items()}
        extras = []
        if clean.get("line"):
            extras.append(f"Linha: {clean['line']}")
        if clean.get("group"):
            extras.append(f"Grupo: {clean['group']}")
        clean["display"] = clean["value"] + (" · " + " · ".join(extras) if extras else "")
        clean["search_blob"] = " | ".join(str(clean.get(k, "")) for k in [
            "value", "code", "description", "line", "group", "segment", "supplier", "ncm"
        ])
        clean["_search_blob_n"] = norm(clean["search_blob"])
        clean["_value_n"] = norm(clean.get("value", ""))
        clean["_code_n"] = norm(clean.get("code", ""))
        clean["_description_n"] = norm(clean.get("description", ""))
        product_records.append(clean)
    product_records.sort(key=lambda r: norm(r["value"]))
    products = [r["value"] for r in product_records]

    return {
        "clients": clients, "products": products,
        "client_records": client_records, "product_records": product_records,
        "source": path.name, "warning": "",
    }


def build_input_catalog(forecast_df: pd.DataFrame) -> dict[str, object]:
    """Combina cadastro mestre da BASE BI com nomes já utilizados no First Budget."""
    path = _master_base_path()
    master = {
        "clients": [], "products": [], "client_records": [], "product_records": [],
        "source": "", "warning": "BASE BI não localizada no repositório do Budget."
    }
    if path is not None:
        master = _read_master_catalog(str(path), path.stat().st_mtime_ns)

    master_clients = list(master.get("clients", []))
    master_products = list(master.get("products", []))
    client_records = [dict(x) for x in master.get("client_records", [])]
    product_records = [dict(x) for x in master.get("product_records", [])]
    forecast_clients: list[str] = []
    forecast_products: list[str] = []
    if forecast_df is not None and not forecast_df.empty:
        if "Cliente" in forecast_df.columns:
            forecast_clients = [str(x).strip() for x in forecast_df["Cliente"].dropna().tolist() if str(x).strip()]
        if "Produto_Linha" in forecast_df.columns:
            forecast_products.extend([str(x).strip() for x in forecast_df["Produto_Linha"].dropna().tolist() if str(x).strip()])
        if "Itens_Contrato_JSON" in forecast_df.columns:
            for raw in forecast_df["Itens_Contrato_JSON"].dropna().astype(str):
                try:
                    payload = json.loads(raw) if raw.strip() else []
                    if isinstance(payload, list):
                        forecast_products.extend(str(item.get("Equipamento", "")).strip() for item in payload if str(item.get("Equipamento", "")).strip())
                except Exception:
                    pass

    def unique_labels(values: list[str]) -> list[str]:
        out: dict[str, str] = {}
        for value in values:
            label = str(value).strip()
            key = norm(label)
            if label and key and key not in out:
                out[key] = label
        return sorted(out.values(), key=lambda x: norm(x))

    clients = unique_labels(master_clients + forecast_clients)
    products = unique_labels(master_products + forecast_products)

    known_client = {norm(r.get("value", "")) for r in client_records}
    for value in clients:
        if norm(value) not in known_client:
            client_records.append({"value": value, "search_blob": value, "_search_blob_n": norm(value), "_value_n": norm(value), "_code_n": "", "_description_n": ""})

    known_product = {norm(r.get("value", "")) for r in product_records}
    for value in products:
        if norm(value) not in known_product:
            product_records.append({"value": value, "display": value, "search_blob": value, "_search_blob_n": norm(value), "_value_n": norm(value), "_code_n": "", "_description_n": ""})

    client_records.sort(key=lambda r: norm(r.get("value", "")))
    product_records.sort(key=lambda r: norm(r.get("value", "")))
    master_keys = {norm(x) for x in master_clients}
    client_types = {name: ("Atual" if norm(name) in master_keys else "Novo") for name in clients}
    return {
        "clients": clients, "products": products, "client_types": client_types,
        "client_records": client_records, "product_records": product_records,
        "master_client_count": len(master_clients), "master_product_count": len(master_products),
        "source": str(master.get("source", "")), "warning": str(master.get("warning", "")),
    }


def resolve_catalog_choice(selected: str, manual: str, new_option: str) -> str:
    return str(manual or "").strip() if selected == new_option else str(selected or "").strip()


def _search_records(records: list[dict[str, object]], query: str, output_field: str = "value", limit: int = 120) -> list[str]:
    """Pesquisa por múltiplas camadas e exige que todos os termos digitados estejam presentes."""
    q = norm(query)
    tokens = [token for token in q.split() if token]
    if not q:
        values = []
        seen = set()
        for rec in records:
            output = str(rec.get(output_field, rec.get("value", "")) or "").strip()
            key = norm(output)
            if output and key and key not in seen:
                seen.add(key)
                values.append(output)
        return sorted(values, key=norm)[:limit]
    ranked: list[tuple[int, int, str, str]] = []
    for rec in records:
        output = str(rec.get(output_field, rec.get("value", "")) or "").strip()
        if not output:
            continue
        blob = str(rec.get("_search_blob_n") or norm(rec.get("search_blob", output)))
        if tokens and not all(token in blob for token in tokens):
            continue
        value_norm = str(rec.get("_value_n") or norm(rec.get("value", output)))
        code_norm = str(rec.get("_code_n") or norm(rec.get("code", "")))
        desc_norm = str(rec.get("_description_n") or norm(rec.get("description", "")))
        # Código exato/prefixo primeiro, depois descrição/nome, depois demais camadas.
        if q and (code_norm == q or value_norm == q):
            tier = 0
        elif q and (code_norm.startswith(q) or value_norm.startswith(q)):
            tier = 1
        elif q and (q in desc_norm or q in value_norm):
            tier = 2
        else:
            tier = 3
        ranked.append((tier, len(blob), value_norm, output))
    ranked.sort(key=lambda row: (row[0], row[1], row[2]))
    return [row[3] for row in ranked[:limit]]


def filter_catalog_options(options: list[str], query: str, limit: int = 120) -> list[str]:
    """Fallback para cadastros sem metadados: busca em qualquer parte do rótulo."""
    records = [{"value": str(x), "search_blob": str(x)} for x in options if str(x).strip()]
    return _search_records(records, query, "value", limit)


def filter_dataframe_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Busca livre em todas as colunas de uma tabela, inclusive JSON, contrato, cliente e produto."""
    if df is None or df.empty or not str(query or "").strip():
        return df.copy() if isinstance(df, pd.DataFrame) else df
    tokens = [token for token in norm(query).split() if token]
    if not tokens:
        return df.copy()
    text_cols = []
    for col in df.columns:
        try:
            text_cols.append(df[col].fillna("").astype(str))
        except Exception:
            pass
    if not text_cols:
        return df.copy()
    blob = text_cols[0]
    for series in text_cols[1:]:
        blob = blob.str.cat(series, sep=" | ")
    blob_n = blob.map(norm)
    mask = pd.Series(True, index=df.index)
    for token in tokens:
        mask &= blob_n.str.contains(token, regex=False, na=False)
    return df.loc[mask].copy()


def filter_budget_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Busca geral: texto da linha + metadados do cadastro mestre de clientes/produtos."""
    if df is None or df.empty or not str(query or "").strip():
        return df.copy() if isinstance(df, pd.DataFrame) else df

    # Correspondência direta em qualquer coluna da base exibida.
    direct = filter_dataframe_search(df, query)
    matched_idx = set(direct.index.tolist())

    # Correspondência indireta: ex. usuário busca pelo grupo/linha, mas o forecast guarda só código/descrição.
    product_records = globals().get("PRODUCT_RECORDS", [])
    client_records = globals().get("CLIENT_RECORDS", [])
    matched_products = set(norm(x) for x in _search_records(product_records, query, "value", limit=5000))
    matched_clients = set(norm(x) for x in _search_records(client_records, query, "value", limit=5000))

    for idx, row in df.iterrows():
        if idx in matched_idx:
            continue
        client = norm(row.get("Cliente", ""))
        if client and client in matched_clients:
            matched_idx.add(idx)
            continue

        product_keys = {
            norm(row.get("Produto_Linha", "")),
            norm(row.get("Linha_Produto", "")),
        }
        raw_items = str(row.get("Itens_Contrato_JSON", "") or "").strip()
        if raw_items:
            try:
                payload = json.loads(raw_items)
                if isinstance(payload, list):
                    product_keys.update(norm(item.get("Equipamento", "")) for item in payload if isinstance(item, dict))
            except Exception:
                pass
        product_keys.discard("")
        if product_keys.intersection(matched_products):
            matched_idx.add(idx)

    return df.loc[df.index.isin(matched_idx)].copy()


def _editor_selected_equipment_values(key: str) -> list[str]:
    """Preserva opções já escolhidas quando a busca do catálogo é refinada no data_editor."""
    state = st.session_state.get(key, {})
    found: list[str] = []
    if not isinstance(state, dict):
        return found
    edited = state.get("edited_rows", {})
    if isinstance(edited, dict):
        for payload in edited.values():
            if isinstance(payload, dict) and payload.get("Equipamento"):
                found.append(str(payload["Equipamento"]))
    added = state.get("added_rows", [])
    if isinstance(added, list):
        for payload in added:
            if isinstance(payload, dict) and payload.get("Equipamento"):
                found.append(str(payload["Equipamento"]))
    return found


def _active_contracts_path() -> Path | None:
    """Localiza a planilha operacional de contratos ativos no repositório do Budget."""
    here = Path(__file__).resolve().parent
    preferred = [
        "PLANILHA DE CONTRATOS.xlsx",
        "PLANILHA DE CONTRATOS.xlsm",
        "Cópia de PLANILHA DE CONTRATOS - 25.09.26.xlsx",
        "Copia de PLANILHA DE CONTRATOS - 25.09.26.xlsx",
    ]
    for name in preferred:
        path = here / name
        if path.exists() and not path.name.startswith("~$"):
            return path
    candidates = []
    for path in here.glob("*.xls*"):
        if path.name.startswith("~$"):
            continue
        key = norm(path.stem)
        if "CONTRAT" in key and "BASE BI" not in key:
            candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda p: p.stat().st_mtime_ns, reverse=True)[0]


def _money_value(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    txt = str(value).strip().upper()
    if txt in {"", "S/FAT", "S/ FAT", "SEM FAT", "SEM FATURAMENTO", "NAN", "NONE"}:
        return 0.0
    txt = txt.replace("R$", "").replace(" ", "")
    if "," in txt:
        txt = txt.replace(".", "").replace(",", ".")
    try:
        return float(txt)
    except Exception:
        return 0.0


def _contract_budget_line(manager: object, product_line: object) -> str:
    """Sugere a linha do Budget preservando os gestores oficiais do Intelligence."""
    mgr = norm(manager)
    prod = norm(product_line)
    if "AMAURI" in mgr:
        return "LOCACAO"
    if "RONALDO" in mgr:
        return "ENDOSCOPIA"
    if "RENATO" in mgr:
        return "VENDAS"
    if "ENDOSCOP" in prod:
        return "ENDOSCOPIA"
    if "OXIGENO" in prod:
        return "VENDAS"
    if "AMAURI" in prod:
        return "LOCACAO"
    return "LOCACAO"


@st.cache_data(show_spinner=False, ttl=300)
def _read_active_contracts(path_text: str, modified_ns: int) -> dict[str, object]:
    """Lê a carteira vigente e padroniza somente os campos necessários ao Budget."""
    path = Path(path_text)
    try:
        book = pd.ExcelFile(path, engine="openpyxl")
        sheet_name = "CT" if "CT" in book.sheet_names else book.sheet_names[0]
        raw = pd.read_excel(path, sheet_name=sheet_name, engine="openpyxl")
    except Exception as exc:
        return {"data": pd.DataFrame(), "source": path.name, "warning": f"Não foi possível ler a planilha de contratos: {exc}"}

    raw.columns = [str(c).strip() for c in raw.columns]
    def col(candidates):
        return _optional_col(raw, candidates)

    mapping = {
        "Numero_Contrato": col(["Nº CT", "N° CT", "NUMERO CT", "CONTRATO"]),
        "Origem": col(["ORIGEM"]),
        "SLA_Horas": col(["SLA EM HORAS", "SLA EM HORAS "]),
        "Titulo_Card": col(["TITULO DO CARD", "TÍTULO DO CARD"]),
        "Codigo_Cliente": col(["COD. CLIENTE", "COD CLIENTE", "CODIGO CLIENTE"]),
        "Loja": col(["LOJA"]),
        "CNPJ_CPF": col(["CNPJ/CPF", "CNPJ CPF"]),
        "Cliente": col(["RAZÃO SOCIAL", "RAZAO SOCIAL", "CLIENTE"]),
        "Data_Inicio": col(["INICIO", "INÍCIO", "DATA INICIO", "DATA INÍCIO"]),
        "Data_Fim": col(["FIM", "TÉRMINO", "TERMINO", "DATA FIM", "VIGÊNCIA FINAL", "VIGENCIA FINAL"]),
        "Meses_2027_Base": col(["MESES 2027", "MESES EM 2027", "QTD MESES 2027"]),
        "Valor_Mensal_Base": col(["VALOR FATURAMENTO", "VALOR FATURAMENTO ", "VALOR"]),
        "Vendedor": col(["VENDEDOR"]),
        "Gerente": col(["GERENTE"]),
        "Linha_Produto": col(["LINHA DE PRODUTO", "LINHA PRODUTO"]),
        "Dia_Faturamento": col(["DIA"]),
        "Qtd_Equipamentos": col(["QTD EQ", "QTD. EQ", "QUANTIDADE EQUIPAMENTOS"]),
    }

    out = pd.DataFrame(index=raw.index)
    for target, source in mapping.items():
        out[target] = raw[source] if source else ""

    # Descarta linhas separadoras/vazias sem contrato, cliente e CNPJ.
    identity = (
        out["Numero_Contrato"].fillna("").astype(str).str.strip()
        + out["Cliente"].fillna("").astype(str).str.strip()
        + out["CNPJ_CPF"].fillna("").astype(str).str.strip()
    )
    out = out.loc[identity.ne("")].copy()
    out["Valor_Mensal_Base"] = out["Valor_Mensal_Base"].map(_money_value)
    out["Data_Inicio"] = pd.to_datetime(out["Data_Inicio"], errors="coerce", dayfirst=True)
    out["Data_Fim"] = pd.to_datetime(out["Data_Fim"], errors="coerce", dayfirst=True)
    out["Meses_2027_Base"] = pd.to_numeric(out["Meses_2027_Base"], errors="coerce")
    out["Qtd_Equipamentos"] = pd.to_numeric(out["Qtd_Equipamentos"], errors="coerce").fillna(0.0)
    out["Linha_Sugerida"] = out.apply(lambda r: _contract_budget_line(r.get("Gerente"), r.get("Linha_Produto")), axis=1)
    out["Fonte_Linha"] = np.where(out["Gerente"].fillna("").astype(str).str.strip().ne(""), "Gerente", "Linha de produto")
    out["Linha_Fonte"] = np.arange(2, len(out) + 2)

    # Chave estável sem usar valor mensal, permitindo reajuste do faturamento sem perder a revisão 2027.
    def make_key(row):
        raw_key = "|".join(norm(row.get(c, "")) for c in [
            "Numero_Contrato", "Codigo_Cliente", "Loja", "CNPJ_CPF", "Cliente", "Gerente", "Linha_Produto"
        ])
        return hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:16].upper()
    out["Contrato_Key"] = out.apply(make_key, axis=1)
    out["Sem_Valor"] = out["Valor_Mensal_Base"].le(0)
    return {"data": out.reset_index(drop=True), "source": path.name, "warning": ""}


def active_contracts_source() -> dict[str, object]:
    path = _active_contracts_path()
    if path is None:
        return {"data": pd.DataFrame(), "source": "", "warning": "Planilha de contratos ativos não localizada no repositório do Budget."}
    return _read_active_contracts(str(path), path.stat().st_mtime_ns)


def active_contract_overrides_file() -> str:
    return f"carteira_ativa_{APP_YEAR}.csv"


def load_active_contract_overrides() -> pd.DataFrame:
    df = load_table(active_contract_overrides_file(), ACTIVE_CONTRACT_OVERRIDE_COLUMNS)
    for col in ["Meses_2027", "Valor_Mensal_Ajustado"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _contract_periods_2027(row: dict | pd.Series) -> list[pd.Period]:
    """Retorna as competências efetivamente contratadas em 2027, respeitando início, fim e meses revisados."""
    year_start = pd.Period(f"{APP_YEAR}-01", freq="M")
    year_end = pd.Period(f"{APP_YEAR}-12", freq="M")
    if float(pd.to_numeric(pd.Series([row.get("Valor_Mensal_Base", 0)]), errors="coerce").fillna(0).iloc[0]) <= 0:
        return []

    start_raw = pd.to_datetime(row.get("Data_Inicio"), errors="coerce", dayfirst=True)
    end_raw = pd.to_datetime(row.get("Data_Fim"), errors="coerce", dayfirst=True)
    start_period = max(start_raw.to_period("M"), year_start) if pd.notna(start_raw) else year_start
    end_period = min(end_raw.to_period("M"), year_end) if pd.notna(end_raw) else year_end
    if end_period < start_period:
        return []

    periods = list(pd.period_range(start_period, end_period, freq="M"))
    explicit = pd.to_numeric(pd.Series([row.get("Meses_2027_Base")]), errors="coerce").iloc[0]
    if pd.notna(explicit):
        qty = int(max(0, min(12, round(float(explicit)))))
        periods = periods[:qty]
    return periods


def build_active_contracts_budget() -> tuple[pd.DataFrame, dict[str, object]]:
    """Usa a planilha revisada de contratos como fonte oficial da receita contratada de 2027."""
    source = active_contracts_source()
    base = source.get("data", pd.DataFrame()).copy()
    if base.empty:
        return base, source

    base["Linha_Budget"] = base["Linha_Sugerida"].fillna("LOCACAO").astype(str)
    base["Valor_Mensal_Ajustado"] = pd.to_numeric(base["Valor_Mensal_Base"], errors="coerce").fillna(0.0)

    base["Meses_2027"] = base.apply(lambda row: len(_contract_periods_2027(row)), axis=1)
    base["Receita_2027_Planejada"] = base["Valor_Mensal_Ajustado"] * base["Meses_2027"]
    base["Receita_2027_Validada"] = base["Receita_2027_Planejada"]
    base["Receita_2027_Preliminar"] = base["Receita_2027_Planejada"]
    base["Validado"] = True
    base["Status_2027"] = "BASE ATUALIZADA"
    return base, source


@st.cache_data(show_spinner=False, ttl=120)
def expand_active_contracts_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Transforma a carteira contratada em receita mensal, sem alterar a planilha fonte."""
    columns = ["Contrato_Key", "Numero_Contrato", "Linha", "Competencia", "Cliente", "Linha_Produto", "Receita_Contratada"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columns)
    rows: list[dict] = []
    for _, contract in df.iterrows():
        monthly = float(pd.to_numeric(pd.Series([contract.get("Valor_Mensal_Ajustado", contract.get("Valor_Mensal_Base", 0))]), errors="coerce").fillna(0).iloc[0])
        if monthly <= 0:
            continue
        for period in _contract_periods_2027(contract):
            rows.append({
                "Contrato_Key": str(contract.get("Contrato_Key", "")),
                "Numero_Contrato": str(contract.get("Numero_Contrato", "") or ""),
                "Linha": norm(contract.get("Linha_Budget", contract.get("Linha_Sugerida", "LOCACAO"))) or "LOCACAO",
                "Competencia": str(period),
                "Cliente": str(contract.get("Cliente", "") or ""),
                "Linha_Produto": str(contract.get("Linha_Produto", "") or ""),
                "Receita_Contratada": monthly,
            })
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(show_spinner=False, ttl=120)
def build_revenue_summary_monthly(contract_monthly: pd.DataFrame, forecast_monthly: pd.DataFrame) -> pd.DataFrame:
    """Consolida Carteira Ativa + Forecast Comercial sem misturar as duas origens."""
    parts: list[pd.DataFrame] = []
    if contract_monthly is not None and not contract_monthly.empty:
        c = contract_monthly.groupby(["Linha", "Competencia"], as_index=False)["Receita_Contratada"].sum()
        c["Forecast_Bruto"] = 0.0
        c["Forecast_Ponderado"] = 0.0
        parts.append(c)
    if forecast_monthly is not None and not forecast_monthly.empty:
        f = forecast_monthly.groupby(["Linha", "Competencia"], as_index=False).agg(
            Forecast_Bruto=("Receita_Prevista", "sum"),
            Forecast_Ponderado=("Receita_Ponderada", "sum"),
        )
        f["Receita_Contratada"] = 0.0
        parts.append(f)
    if not parts:
        return pd.DataFrame(columns=["Linha", "Competencia", "Receita_Contratada", "Forecast_Bruto", "Forecast_Ponderado", "Receita_Projetada_Bruta", "Receita_Projetada_Ponderada"])
    out = pd.concat(parts, ignore_index=True).groupby(["Linha", "Competencia"], as_index=False).agg(
        Receita_Contratada=("Receita_Contratada", "sum"),
        Forecast_Bruto=("Forecast_Bruto", "sum"),
        Forecast_Ponderado=("Forecast_Ponderado", "sum"),
    )
    out["Receita_Projetada_Bruta"] = out["Receita_Contratada"] + out["Forecast_Bruto"]
    out["Receita_Projetada_Ponderada"] = out["Receita_Contratada"] + out["Forecast_Ponderado"]
    return out


@st.cache_data(show_spinner=False, ttl=120)
def build_budget_revenue_basis(
    contract_monthly: pd.DataFrame,
    forecast_monthly: pd.DataFrame,
    sulamita_detail: pd.DataFrame,
    sulamita_avg_monthly: float,
) -> pd.DataFrame:
    """Monta a base sugerida do Budget de Receita sem alterar as fontes operacionais.

    Regras:
    - Locação: carteira contratada + forecast ponderado de novos contratos.
    - Microtech: média histórica mensal dos clientes Sulamita + forecast ponderado dos
      demais clientes. Forecast de clientes Sulamita já presentes no histórico fica
      destacado e fora da base sugerida para evitar dupla contagem.
    - Vendas/Endoscopia: forecast comercial ponderado.
    """
    grid = pd.MultiIndex.from_product(
        [LINES, [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]],
        names=["Linha", "Competencia"],
    ).to_frame(index=False)

    contracted = pd.DataFrame(columns=["Linha", "Competencia", "Receita_Contratada"])
    if contract_monthly is not None and not contract_monthly.empty:
        contracted = contract_monthly.groupby(["Linha", "Competencia"], as_index=False)["Receita_Contratada"].sum()

    forecast = pd.DataFrame(columns=[
        "Linha", "Competencia", "Forecast_Bruto", "Forecast_Ponderado",
        "Forecast_Ponderado_Considerado", "Forecast_Sulamita_Excluido",
    ])
    if forecast_monthly is not None and not forecast_monthly.empty:
        f = forecast_monthly.copy()
        f["_CLIENTE_N"] = f.get("Cliente", "").fillna("").astype(str).map(norm)
        sulamita_clients = set()
        if sulamita_detail is not None and not sulamita_detail.empty and "Cliente" in sulamita_detail.columns:
            sulamita_clients = {norm(x) for x in sulamita_detail["Cliente"].dropna().astype(str) if norm(x)}
        f["_SULAMITA_HIST"] = f["Linha"].astype(str).map(norm).eq("MICROTECH") & f["_CLIENTE_N"].isin(sulamita_clients)
        f["_FORECAST_CONSIDERADO"] = np.where(f["_SULAMITA_HIST"], 0.0, pd.to_numeric(f["Receita_Ponderada"], errors="coerce").fillna(0.0))
        f["_FORECAST_SULAMITA_EXCLUIDO"] = np.where(f["_SULAMITA_HIST"], pd.to_numeric(f["Receita_Ponderada"], errors="coerce").fillna(0.0), 0.0)
        forecast = f.groupby(["Linha", "Competencia"], as_index=False).agg(
            Forecast_Bruto=("Receita_Prevista", "sum"),
            Forecast_Ponderado=("Receita_Ponderada", "sum"),
            Forecast_Ponderado_Considerado=("_FORECAST_CONSIDERADO", "sum"),
            Forecast_Sulamita_Excluido=("_FORECAST_SULAMITA_EXCLUIDO", "sum"),
        )

    out = grid.merge(contracted, on=["Linha", "Competencia"], how="left")
    out = out.merge(forecast, on=["Linha", "Competencia"], how="left")
    numeric_cols = [
        "Receita_Contratada", "Forecast_Bruto", "Forecast_Ponderado",
        "Forecast_Ponderado_Considerado", "Forecast_Sulamita_Excluido",
    ]
    for col in numeric_cols:
        if col not in out.columns:
            out[col] = 0.0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0.0)

    out["Referencia_Historica"] = 0.0
    out.loc[out["Linha"].eq("MICROTECH"), "Referencia_Historica"] = max(float(sulamita_avg_monthly or 0.0), 0.0)
    out["Base_Sugerida"] = out["Receita_Contratada"] + out["Referencia_Historica"] + out["Forecast_Ponderado_Considerado"]
    return out


def merge_budget_revenue_overrides(basis: pd.DataFrame, saved: pd.DataFrame) -> pd.DataFrame:
    """Aplica o orçamento gravado sobre a base dinâmica sem congelar as fontes."""
    out = basis.copy()
    if saved is not None and not saved.empty:
        cols = [c for c in BUDGET_REVENUE_COLUMNS if c in saved.columns and c not in {"Ano"}]
        out = out.merge(saved[cols], on=["Linha", "Competencia"], how="left")
    for col in ["Budget_Proposto", "Budget_Aprovado"]:
        if col not in out.columns:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")
    # Enquanto a Controladoria ainda não gravou uma proposta, a base sugerida é o ponto de partida visual.
    out["Budget_Proposto_Visual"] = out["Budget_Proposto"].where(out["Budget_Proposto"].notna(), out["Base_Sugerida"])
    out["Budget_Aprovado"] = out["Budget_Aprovado"].fillna(0.0)
    if "Status" not in out.columns:
        out["Status"] = ""
    out["Status"] = out["Status"].fillna("").astype(str).replace("", "EM ELABORAÇÃO")
    if "Justificativa" not in out.columns:
        out["Justificativa"] = ""
    out["Justificativa"] = out["Justificativa"].fillna("").astype(str)
    return out


def save_active_contract_override(user: dict, row: pd.Series, status: str, months: int, monthly: float, line: str, note: str) -> None:
    latest = load_active_contract_overrides()
    key = str(row.get("Contrato_Key", ""))
    payload = {
        "Contrato_Key": key,
        "Status_2027": status,
        "Meses_2027": int(months),
        "Valor_Mensal_Ajustado": float(monthly),
        "Linha_Budget": norm(line),
        "Observacao_2027": str(note or "").strip(),
        "Atualizado_Por": user["nome"],
        "Atualizado_Em": now_text(),
    }
    if latest.empty or not latest["Contrato_Key"].astype(str).eq(key).any():
        latest = pd.concat([latest, pd.DataFrame([payload])], ignore_index=True)
    else:
        idx = latest.index[latest["Contrato_Key"].astype(str).eq(key)][0]
        for k, v in payload.items():
            latest.at[idx, k] = v
    save_table(active_contract_overrides_file(), latest[ACTIVE_CONTRACT_OVERRIDE_COLUMNS], f"First Budget: revisão carteira {key}")


def scope_active_contracts(df: pd.DataFrame, line: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    target_col = "Linha_Budget" if "Linha_Budget" in df.columns else "Linha_Sugerida"
    if not is_director:
        return df[df[target_col].astype(str).map(norm).eq(user["linha"])].copy()
    if line != "CONSOLIDADO":
        return df[df[target_col].astype(str).map(norm).eq(line)].copy()
    return df.copy()


def rental_projection(start_value: object, months_value: object, monthly_value: object) -> dict[str, object]:
    """Calcula a vigência e a receita de locação que efetivamente pertence ao ano do Budget."""
    try:
        start = pd.Timestamp(start_value).normalize()
        months = max(int(float(months_value)), 0)
        monthly = max(float(monthly_value), 0.0)
    except Exception:
        return {"valid": False, "months": [], "months_in_year": 0, "revenue_year": 0.0, "contract_total": 0.0, "end": None, "first_comp": ""}
    if pd.isna(start) or months <= 0 or monthly <= 0:
        return {"valid": False, "months": [], "months_in_year": 0, "revenue_year": 0.0, "contract_total": 0.0, "end": None, "first_comp": ""}

    periods = list(pd.period_range(start=start.to_period("M"), periods=months, freq="M"))
    periods_year = [p for p in periods if p.year == APP_YEAR]
    end = start + pd.DateOffset(months=months) - pd.Timedelta(days=1)
    first_comp = str(periods_year[0]) if periods_year else str(start.to_period("M"))
    return {
        "valid": True,
        "months": periods_year,
        "months_in_year": len(periods_year),
        "revenue_year": monthly * len(periods_year),
        "contract_total": monthly * months,
        "end": end,
        "first_comp": first_comp,
    }


def contract_items_from_row(row: dict | pd.Series) -> pd.DataFrame:
    """Lê os itens de um contrato e mantém compatibilidade com locações criadas na versão anterior."""
    raw = str(row.get("Itens_Contrato_JSON", "") or "").strip()
    if raw:
        try:
            payload = json.loads(raw)
            if isinstance(payload, list):
                frame = pd.DataFrame(payload)
                for col in CONTRACT_ITEM_COLUMNS:
                    if col not in frame.columns:
                        frame[col] = "" if col in {"Equipamento", "Observacao_Item"} else 0.0
                frame["Quantidade"] = pd.to_numeric(frame["Quantidade"], errors="coerce").fillna(0.0)
                frame["Valor_Mensal_Unitario"] = pd.to_numeric(frame["Valor_Mensal_Unitario"], errors="coerce").fillna(0.0)
                return frame[CONTRACT_ITEM_COLUMNS].copy()
        except Exception:
            pass

    # Compatibilidade: na versão anterior Valor_Mensal_Contrato era o total mensal do contrato.
    if norm(row.get("Tipo_Receita")) == "LOCACAO":
        monthly_total = float(pd.to_numeric(pd.Series([row.get("Valor_Mensal_Contrato")]), errors="coerce").fillna(0).iloc[0])
        qty = float(pd.to_numeric(pd.Series([row.get("Quantidade")]), errors="coerce").fillna(0).iloc[0])
        qty = qty if qty > 0 else 1.0
        equipment = str(row.get("Produto_Linha", "") or "").strip() or "Equipamento"
        if monthly_total > 0:
            return pd.DataFrame([{
                "Equipamento": equipment,
                "Quantidade": qty,
                "Valor_Mensal_Unitario": monthly_total / qty,
                "Observacao_Item": "",
            }], columns=CONTRACT_ITEM_COLUMNS)
    return pd.DataFrame(columns=CONTRACT_ITEM_COLUMNS)


def contract_items_metrics(editor_value: object) -> dict[str, object]:
    """Valida a grade de equipamentos e calcula quantidade e mensalidade total do contrato."""
    frame = pd.DataFrame(editor_value).copy() if editor_value is not None else pd.DataFrame(columns=CONTRACT_ITEM_COLUMNS)
    for col in CONTRACT_ITEM_COLUMNS:
        if col not in frame.columns:
            frame[col] = "" if col in {"Equipamento", "Observacao_Item"} else 0.0
    if "Equipamento_Novo" not in frame.columns:
        frame["Equipamento_Novo"] = ""
    frame = frame[CONTRACT_ITEM_COLUMNS + ["Equipamento_Novo"]].copy()
    frame["Equipamento"] = frame["Equipamento"].fillna("").astype(str).str.strip()
    frame["Equipamento_Novo"] = frame["Equipamento_Novo"].fillna("").astype(str).str.strip()
    frame["Observacao_Item"] = frame["Observacao_Item"].fillna("").astype(str).str.strip()
    frame["Quantidade"] = pd.to_numeric(frame["Quantidade"], errors="coerce").fillna(0.0)
    frame["Valor_Mensal_Unitario"] = pd.to_numeric(frame["Valor_Mensal_Unitario"], errors="coerce").fillna(0.0)

    is_new_equipment = frame["Equipamento"].eq(NEW_PRODUCT_OPTION)
    frame.loc[is_new_equipment, "Equipamento"] = frame.loc[is_new_equipment, "Equipamento_Novo"]
    # O seletor de locação pode exibir Linha/Grupo para melhorar a busca, mas gravamos o nome canônico.
    display_map = globals().get("PRODUCT_DISPLAY_TO_VALUE", {})
    frame["Equipamento"] = frame["Equipamento"].map(lambda value: display_map.get(str(value), str(value)))

    # Remove apenas linhas totalmente vazias; linhas parcialmente preenchidas devem gerar validação.
    blank = (frame["Equipamento"].eq("") & frame["Quantidade"].eq(0) & frame["Valor_Mensal_Unitario"].eq(0) & frame["Observacao_Item"].eq(""))
    frame = frame.loc[~blank].reset_index(drop=True)
    if frame.empty:
        return {"valid": False, "error": "Inclua pelo menos um equipamento no contrato.", "df": frame}
    if frame["Equipamento"].eq("").any():
        return {"valid": False, "error": "Informe o equipamento em todas as linhas do contrato. Para item novo, preencha a coluna Novo equipamento.", "df": frame}
    if frame["Quantidade"].le(0).any():
        return {"valid": False, "error": "A quantidade de cada equipamento deve ser maior que zero.", "df": frame}
    if frame["Valor_Mensal_Unitario"].le(0).any():
        return {"valid": False, "error": "Informe um valor mensal unitário maior que zero para cada equipamento.", "df": frame}

    frame["Valor_Mensal_Total"] = frame["Quantidade"] * frame["Valor_Mensal_Unitario"]
    records = []
    for _, item in frame.iterrows():
        records.append({
            "Equipamento": item["Equipamento"],
            "Quantidade": float(item["Quantidade"]),
            "Valor_Mensal_Unitario": float(item["Valor_Mensal_Unitario"]),
            "Valor_Mensal_Total": float(item["Valor_Mensal_Total"]),
            "Observacao_Item": item["Observacao_Item"],
        })
    names = frame["Equipamento"].tolist()
    summary = "; ".join(names[:3])
    if len(names) > 3:
        summary += f" +{len(names) - 3} item(ns)"
    return {
        "valid": True,
        "error": "",
        "df": frame,
        "item_count": int(len(frame)),
        "total_units": float(frame["Quantidade"].sum()),
        "monthly_total": float(frame["Valor_Mensal_Total"].sum()),
        "summary": summary,
        "json": json.dumps(records, ensure_ascii=False),
    }


def contract_item_count(row: dict | pd.Series) -> int:
    try:
        return int(len(contract_items_from_row(row)))
    except Exception:
        return 0


def forecast_period_label(row: pd.Series) -> str:
    if norm(row.get("Tipo_Receita")) == "LOCACAO" and str(row.get("Data_Inicio_Contrato", "")).strip():
        try:
            prazo = int(float(row.get("Prazo_Contrato_Meses", 0) or 0))
        except Exception:
            prazo = 0
        return f"{date_br(row.get('Data_Inicio_Contrato'))} a {date_br(row.get('Data_Fim_Contrato'))} · {prazo}m"
    return month_label_from_comp(str(row.get("Competencia", "")))


@st.cache_data(show_spinner=False, ttl=120)
def expand_monthly_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """Expande contratos de locação por competência sem duplicar os registros gravados."""
    if df is None or df.empty:
        return pd.DataFrame(columns=FORECAST_COLUMNS)
    rows: list[dict] = []
    for _, source in df.iterrows():
        row = source.to_dict()
        if norm(row.get("Tipo_Receita")) == "LOCACAO":
            proj = rental_projection(
                row.get("Data_Inicio_Contrato"),
                row.get("Prazo_Contrato_Meses"),
                row.get("Valor_Mensal_Contrato"),
            )
            if proj["valid"] and proj["months"]:
                peso = float(pd.to_numeric(pd.Series([row.get("Peso_Probabilidade")]), errors="coerce").fillna(0).iloc[0])
                valor_mensal = float(pd.to_numeric(pd.Series([row.get("Valor_Mensal_Contrato")]), errors="coerce").fillna(0).iloc[0])
                for period in proj["months"]:
                    item = row.copy()
                    item["Competencia"] = str(period)
                    item["Receita_Prevista"] = valor_mensal
                    item["Receita_Ponderada"] = valor_mensal * peso
                    rows.append(item)
                continue
        rows.append(row)
    out = pd.DataFrame(rows)
    for col in FORECAST_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    for col in ["Quantidade", "Valor_Unitario", "Prazo_Contrato_Meses", "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Meses_No_Ano", "Receita_Prevista", "Peso_Probabilidade", "Receita_Ponderada"]:
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    return out


def hero(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class='hero'>
          <div class='eyebrow'>First Medical · Planejamento & Controladoria</div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"<div class='kpi'><div class='label'>{label}</div><div class='value'>{value}</div><div class='note'>{note}</div></div>",
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    st.markdown(f"<div class='section'>{title}</div>", unsafe_allow_html=True)


def plot_layout(fig: go.Figure, height: int = 350) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=18, r=18, t=55, b=42),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FBFDFF",
        font=dict(family="Arial", color="#344054", size=11),
        legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0),
        hovermode="x unified",
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, title_text="")
    fig.update_yaxes(showgrid=False, zeroline=False, title_text="")
    return fig


# =========================================================
# AUTENTICAÇÃO — MESMA REGRA DO FIRST INTELLIGENCE
# =========================================================
def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


DEFAULT_USERS = {
    "diretoria": {
        "nome": "Diretoria", "usuario": "diretoria", "email": "",
        "senha_hash": "cbae32987728a10b19e2528695dbf676c9b8de0f539bab08b5789c2e9f0d8599",
        "perfil": "DIRETORIA", "linha": "CONSOLIDADO",
    },
    "paula": {
        "nome": "Paula", "usuario": "paula", "email": "paulamayara10@gmail.com",
        "senha_hash": "ad27a22ae449782700c94a3acfa95e19cb5b3a3907b7da088d11569d32bfe800",
        "perfil": "CONTROLADORIA", "linha": "CONSOLIDADO",
    },
    "celso": {
        "nome": "Celso", "usuario": "celso", "email": "",
        "senha_hash": "35a4526e8b23c095c14d926e1f4e5614f70c20069200d3cf4f8ef4da80cb240a",
        "perfil": "GESTOR", "linha": "MICROTECH",
    },
    "renato": {
        "nome": "Renato", "usuario": "renato", "email": "",
        "senha_hash": "353b16f690d6dadaa2a675f73963bdd60ddc36979922100340761dd3f712341a",
        "perfil": "GESTOR", "linha": "VENDAS",
    },
    "amauri": {
        "nome": "Amauri", "usuario": "amauri", "email": "",
        "senha_hash": "5bda933352db6ef4569709d432a7d1ac793977c82fb982c5bae65651015493c5",
        "perfil": "GESTOR", "linha": "LOCACAO",
    },
    "ronaldo": {
        "nome": "Ronaldo", "usuario": "ronaldo", "email": "",
        "senha_hash": "21ce9c880661ca01dc3af90a1803b32244e1743ba8fef495e83ef10204546fc2",
        "perfil": "GESTOR", "linha": "ENDOSCOPIA",
    },
}


def secret_users() -> dict[str, dict]:
    users = {key: dict(value) for key, value in DEFAULT_USERS.items()}
    try:
        raw = st.secrets.get("usuarios", {})
        for key, value in raw.items():
            users[str(key)] = dict(value)
    except Exception:
        pass
    return users


def authenticate() -> dict[str, str]:
    users = secret_users()
    if "auth_user" not in st.session_state:
        profile_order = ["diretoria", "paula", "celso", "renato", "amauri", "ronaldo"]
        available = [key for key in profile_order if key in users] + [key for key in users if key not in profile_order]
        profile_labels = {
            "diretoria": "Diretoria",
            "paula": "Paula · Controladoria",
            "celso": "Celso · Microtech",
            "renato": "Renato · Vendas",
            "amauri": "Amauri · Locação",
            "ronaldo": "Ronaldo · Endoscopia",
        }
        _, center, _ = st.columns([1, 1.05, 1])
        with center:
            st.markdown(
                """
                <div class='login-brand'>
                  <div class='logo'>FIRST <span>BUDGET</span></div>
                  <p>Planejamento, Forecast & Orçamento</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.form("login_form", clear_on_submit=False):
                selected = st.selectbox(
                    "Perfil de acesso",
                    available,
                    format_func=lambda key: profile_labels.get(key, users[key].get("nome", key)),
                )
                password = st.text_input("Senha", type="password")
                submitted = st.form_submit_button("Acessar First Budget", width="stretch")
            if submitted:
                cfg = users[selected]
                expected = str(cfg.get("senha_hash", ""))
                valid = bool(expected) and password_hash(password) == expected
                if not valid and cfg.get("senha") is not None:
                    valid = password == str(cfg.get("senha"))
                if valid:
                    st.session_state["auth_user"] = {
                        "nome": str(cfg.get("nome", selected)),
                        "email": str(cfg.get("email", "")),
                        "perfil": norm(cfg.get("perfil", "GESTOR")),
                        "linha": norm(cfg.get("linha", "VENDAS")),
                    }
                    st.rerun()
                st.error("Senha incorreta para o perfil selecionado.")
        st.stop()
    return st.session_state["auth_user"]


# =========================================================
# PERSISTÊNCIA — GITHUB OPCIONAL / LOCAL CONTINGÊNCIA
# =========================================================
LOCAL_DATA_DIR = Path(__file__).resolve().parent / "budget_data"
LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)


def storage_config() -> dict:
    cfg = {"mode": "local", "repo": "", "branch": "main", "token": "", "folder": "budget_data"}
    try:
        raw = st.secrets.get("budget_storage", {})
        for key in cfg:
            if key in raw:
                cfg[key] = str(raw.get(key, cfg[key]))
    except Exception:
        pass
    env_map = {
        "repo": "FIRST_BUDGET_GITHUB_REPO",
        "branch": "FIRST_BUDGET_GITHUB_BRANCH",
        "token": "FIRST_BUDGET_GITHUB_TOKEN",
        "folder": "FIRST_BUDGET_GITHUB_FOLDER",
    }
    for key, env_name in env_map.items():
        if os.getenv(env_name):
            cfg[key] = os.getenv(env_name, cfg[key])
    if cfg["repo"] and cfg["token"]:
        cfg["mode"] = "github"
    return cfg


def _remote_path(name: str) -> str:
    cfg = storage_config()
    folder = cfg.get("folder", "budget_data").strip("/")
    return f"{folder}/{name}" if folder else name


def _github_headers() -> dict:
    cfg = storage_config()
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_read_bytes(name: str) -> bytes | None:
    if requests is None:
        raise RuntimeError("Biblioteca requests não disponível para persistência no GitHub.")
    cfg = storage_config()
    path = _remote_path(name)
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{path}"
    resp = requests.get(url, headers=_github_headers(), params={"ref": cfg["branch"]}, timeout=20)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    payload = resp.json()
    return base64.b64decode(payload["content"])


def github_write_bytes(name: str, data: bytes, message: str) -> None:
    if requests is None:
        raise RuntimeError("Biblioteca requests não disponível para persistência no GitHub.")
    cfg = storage_config()
    path = _remote_path(name)
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{path}"

    for _ in range(3):
        current = requests.get(url, headers=_github_headers(), params={"ref": cfg["branch"]}, timeout=20)
        sha = current.json().get("sha") if current.status_code == 200 else None
        payload = {
            "message": message,
            "content": base64.b64encode(data).decode("ascii"),
            "branch": cfg["branch"],
        }
        if sha:
            payload["sha"] = sha
        put = requests.put(url, headers=_github_headers(), json=payload, timeout=25)
        if put.status_code in (200, 201):
            return
        if put.status_code not in (409, 422):
            put.raise_for_status()
    raise RuntimeError("Conflito ao gravar no GitHub. Atualize a tela e tente novamente.")


def _load_table_uncached(name: str, columns: list[str]) -> pd.DataFrame:
    cfg = storage_config()
    raw: bytes | None = None
    try:
        if cfg["mode"] == "github":
            raw = github_read_bytes(name)
        else:
            path = LOCAL_DATA_DIR / name
            raw = path.read_bytes() if path.exists() else None
    except Exception:
        return pd.DataFrame(columns=columns)

    if not raw:
        return pd.DataFrame(columns=columns)
    try:
        df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    except Exception:
        return pd.DataFrame(columns=columns)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    return df[columns].copy()


def _storage_signature() -> str:
    cfg = storage_config()
    return "|".join(str(cfg.get(k, "")) for k in ["mode", "repo", "branch", "folder"])


@st.cache_data(show_spinner=False, ttl=TABLE_CACHE_TTL)
def _load_table_cached(name: str, columns: tuple[str, ...], storage_signature: str) -> pd.DataFrame:
    return _load_table_uncached(name, list(columns))


def load_table(name: str, columns: list[str], fresh: bool = False) -> pd.DataFrame:
    if fresh:
        return _load_table_uncached(name, columns)
    return _load_table_cached(name, tuple(columns), _storage_signature()).copy()


def save_table(name: str, df: pd.DataFrame, message: str) -> None:
    data = df.to_csv(index=False).encode("utf-8-sig")
    cfg = storage_config()
    if cfg["mode"] == "github":
        github_write_bytes(name, data, message)
    else:
        path = LOCAL_DATA_DIR / name
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
    _load_table_cached.clear()


def forecast_file() -> str:
    return f"forecast_comercial_{APP_YEAR}.csv"


def history_file() -> str:
    return f"historico_forecast_{APP_YEAR}.csv"


def budget_revenue_file() -> str:
    return f"budget_receita_{APP_YEAR}.csv"


def budget_revenue_history_file() -> str:
    return f"historico_budget_receita_{APP_YEAR}.csv"


def load_forecast(fresh: bool = False) -> pd.DataFrame:
    df = load_table(forecast_file(), FORECAST_COLUMNS, fresh=fresh)
    numeric = [
        "Ano", "Quantidade", "Valor_Unitario", "Prazo_Contrato_Meses",
        "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Meses_No_Ano",
        "Receita_Prevista", "Peso_Probabilidade", "Receita_Ponderada",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_history(fresh: bool = False) -> pd.DataFrame:
    return load_table(history_file(), HISTORY_COLUMNS, fresh=fresh)


def load_budget_revenue(fresh: bool = False) -> pd.DataFrame:
    df = load_table(budget_revenue_file(), BUDGET_REVENUE_COLUMNS, fresh=fresh)
    for col in ["Ano", "Budget_Proposto", "Budget_Aprovado"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["Ano"] = df["Ano"].fillna(APP_YEAR).astype(int)
    return df


def load_budget_revenue_history(fresh: bool = False) -> pd.DataFrame:
    return load_table(budget_revenue_history_file(), BUDGET_REVENUE_HISTORY_COLUMNS, fresh=fresh)


def append_budget_revenue_history(action: str, user: dict, line: str, before: list[dict], after: list[dict]) -> None:
    hist = load_budget_revenue_history(fresh=True)
    row = {
        "Historico_ID": uuid.uuid4().hex[:12].upper(),
        "Ano": APP_YEAR,
        "Linha": norm(line),
        "Acao": action,
        "Usuario": user["nome"],
        "Data_Hora": now_text(),
        "Antes_JSON": json.dumps(before or [], ensure_ascii=False, default=str),
        "Depois_JSON": json.dumps(after or [], ensure_ascii=False, default=str),
    }
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    save_table(budget_revenue_history_file(), hist[BUDGET_REVENUE_HISTORY_COLUMNS], f"First Budget: {action.lower()} budget receita {line}")


def save_budget_revenue_line(user: dict, line: str, edited: pd.DataFrame, action: str = "SALVAR PROPOSTA") -> None:
    """Grava somente a linha selecionada para não sobrescrever outras áreas."""
    line = norm(line)
    latest = load_budget_revenue(fresh=True)
    before_df = latest[latest["Linha"].astype(str).map(norm).eq(line)].copy() if not latest.empty else pd.DataFrame(columns=BUDGET_REVENUE_COLUMNS)
    before = before_df.to_dict("records")

    keep = latest[~latest["Linha"].astype(str).map(norm).eq(line)].copy() if not latest.empty else pd.DataFrame(columns=BUDGET_REVENUE_COLUMNS)
    rows = []
    stamp = now_text()
    for _, row in edited.iterrows():
        rows.append({
            "Ano": APP_YEAR,
            "Linha": line,
            "Competencia": str(row.get("Competencia", "")),
            "Budget_Proposto": float(pd.to_numeric(pd.Series([row.get("Budget_Proposto")]), errors="coerce").fillna(0).iloc[0]),
            "Budget_Aprovado": float(pd.to_numeric(pd.Series([row.get("Budget_Aprovado")]), errors="coerce").fillna(0).iloc[0]),
            "Status": str(row.get("Status", "EM ELABORAÇÃO") or "EM ELABORAÇÃO"),
            "Justificativa": str(row.get("Justificativa", "") or "").strip(),
            "Atualizado_Por": user["nome"],
            "Atualizado_Em": stamp,
        })
    new_line = pd.DataFrame(rows, columns=BUDGET_REVENUE_COLUMNS)
    combined = pd.concat([keep, new_line], ignore_index=True)
    save_table(budget_revenue_file(), combined[BUDGET_REVENUE_COLUMNS], f"First Budget: {action.lower()} {line}")
    append_budget_revenue_history(action, user, line, before, new_line.to_dict("records"))


def set_budget_revenue_status(user: dict, line: str, basis_view: pd.DataFrame, approved: bool) -> None:
    line = norm(line)
    frame = basis_view[basis_view["Linha"].astype(str).map(norm).eq(line)].copy()
    if frame.empty:
        raise RuntimeError("Não há base mensal para esta linha.")
    if approved:
        frame["Budget_Proposto"] = pd.to_numeric(frame["Budget_Proposto_Visual"], errors="coerce").fillna(0.0)
        frame["Budget_Aprovado"] = frame["Budget_Proposto"]
        frame["Status"] = "APROVADO"
        action = "APROVAR BUDGET"
    else:
        frame["Budget_Proposto"] = pd.to_numeric(frame["Budget_Proposto_Visual"], errors="coerce").fillna(0.0)
        frame["Status"] = "EM ELABORAÇÃO"
        action = "REABRIR BUDGET"
    save_budget_revenue_line(user, line, frame, action=action)


def append_history(action: str, user: dict, forecast_id: str, line: str, before: dict | None, after: dict | None) -> None:
    hist = load_history(fresh=True)
    row = {
        "Historico_ID": uuid.uuid4().hex[:12].upper(),
        "Forecast_ID": forecast_id,
        "Ano": APP_YEAR,
        "Linha": line,
        "Acao": action,
        "Usuario": user["nome"],
        "Data_Hora": now_text(),
        "Antes_JSON": json.dumps(before or {}, ensure_ascii=False, default=str),
        "Depois_JSON": json.dumps(after or {}, ensure_ascii=False, default=str),
    }
    hist = pd.concat([hist, pd.DataFrame([row])], ignore_index=True)
    save_table(history_file(), hist, f"First Budget: {action.lower()} {forecast_id}")


def commit_forecast(action: str, user: dict, forecast_id: str, line: str, before: dict | None, after: dict | None) -> None:
    """Grava sobre a versão mais recente e bloqueia sobrescrita silenciosa de edição concorrente."""
    latest = load_forecast(fresh=True)

    if action == "INCLUSÃO":
        if not latest.empty and latest["ID"].astype(str).eq(forecast_id).any():
            raise RuntimeError("Este lançamento já existe. Atualize a tela e tente novamente.")
        latest = pd.concat([latest, pd.DataFrame([after or {}])], ignore_index=True)
    else:
        matches = latest.index[latest["ID"].astype(str).eq(forecast_id)].tolist()
        if not matches:
            raise RuntimeError("O lançamento não existe mais. Atualize a tela antes de continuar.")
        idx = matches[0]
        current = latest.loc[idx].to_dict()
        expected_stamp = str((before or {}).get("Atualizado_Em", ""))
        current_stamp = str(current.get("Atualizado_Em", ""))
        if expected_stamp and current_stamp and expected_stamp != current_stamp:
            raise RuntimeError("Este forecast foi alterado por outro usuário. Atualize a tela para carregar a versão mais recente.")
        for key, value in (after or {}).items():
            if key in latest.columns:
                latest.at[idx, key] = value

    save_table(forecast_file(), latest[FORECAST_COLUMNS], f"First Budget: {action.lower()} {forecast_id}")
    append_history(action, user, forecast_id, line, before, after)


# =========================================================
# EXPORTAÇÃO
# =========================================================
def rental_items_export(forecast: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    if forecast is None or forecast.empty:
        return pd.DataFrame()
    rental = forecast[forecast["Tipo_Receita"].astype(str).map(norm).eq("LOCACAO")].copy()
    for _, contract in rental.iterrows():
        items = contract_items_from_row(contract)
        months_in_year = int(float(contract.get("Meses_No_Ano", 0) or 0))
        term = int(float(contract.get("Prazo_Contrato_Meses", 0) or 0))
        for _, item in items.iterrows():
            qty = float(item.get("Quantidade", 0) or 0)
            unit = float(item.get("Valor_Mensal_Unitario", 0) or 0)
            monthly = qty * unit
            rows.append({
                "Forecast ID": contract.get("ID", ""),
                "Linha": line_label(str(contract.get("Linha", ""))),
                "Cliente": contract.get("Cliente", ""),
                "Contrato": contract.get("Numero_Contrato", ""),
                "Início": date_br(contract.get("Data_Inicio_Contrato", "")),
                "Fim": date_br(contract.get("Data_Fim_Contrato", "")),
                "Prazo (meses)": term,
                "Equipamento": item.get("Equipamento", ""),
                "Quantidade": qty,
                "Valor mensal unitário": unit,
                "Valor mensal item": monthly,
                f"Forecast item {APP_YEAR}": monthly * months_in_year,
                "Valor item contrato": monthly * term,
                "Observação do item": item.get("Observacao_Item", ""),
            })
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False, ttl=120)
def export_excel(forecast: pd.DataFrame, history: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    itens_locacao_export = rental_items_export(forecast)
    f = forecast.copy()
    if not f.empty:
        f["Competência"] = f["Competencia"].map(month_label_from_comp)
        f["Linha"] = f["Linha"].map(line_label)
        f["Início Contrato"] = f["Data_Inicio_Contrato"].map(date_br)
        f["Fim Contrato"] = f["Data_Fim_Contrato"].map(date_br)
        f["Qtd Itens Contrato"] = forecast.apply(contract_item_count, axis=1).values
        for col in ["Valor_Unitario", "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Receita_Prevista", "Receita_Ponderada"]:
            f[col] = pd.to_numeric(f[col], errors="coerce").fillna(0)
        if "Itens_Contrato_JSON" in f.columns:
            f = f.drop(columns=["Itens_Contrato_JSON"])

    active_raw = forecast[forecast["Status"].astype(str).str.upper().eq("ATIVO")].copy() if not forecast.empty else forecast.copy()
    active_monthly = expand_monthly_forecast(active_raw)
    mensal_detalhe = active_monthly.copy()
    if not mensal_detalhe.empty:
        mensal_detalhe["Linha"] = mensal_detalhe["Linha"].map(line_label)
        mensal_detalhe["Mês"] = mensal_detalhe["Competencia"].map(month_label_from_comp)
        mensal_detalhe = mensal_detalhe[[
            "ID", "Linha", "Mês", "Cliente", "Tipo_Receita", "Produto_Linha",
            "Receita_Prevista", "Receita_Ponderada", "Probabilidade"
        ]].rename(columns={
            "Tipo_Receita": "Tipo Receita", "Produto_Linha": "Produto / Oportunidade",
            "Receita_Prevista": "Forecast Bruto", "Receita_Ponderada": "Forecast Ponderado",
        })

    resumo_linha = pd.DataFrame()
    resumo_mes = pd.DataFrame()
    if not active_monthly.empty:
        resumo_linha = active_monthly.groupby("Linha", as_index=False).agg(
            Forecast_Bruto=("Receita_Prevista", "sum"),
            Forecast_Ponderado=("Receita_Ponderada", "sum"),
        )
        resumo_linha["Linha"] = resumo_linha["Linha"].map(line_label)
        registros = active_raw.groupby("Linha", as_index=False).agg(Registros=("ID", "nunique"))
        registros["Linha"] = registros["Linha"].map(line_label)
        resumo_linha = resumo_linha.merge(registros, on="Linha", how="left")
        resumo_mes = active_monthly.groupby("Competencia", as_index=False).agg(
            Forecast_Bruto=("Receita_Prevista", "sum"),
            Forecast_Ponderado=("Receita_Ponderada", "sum"),
        )
        resumo_mes["Mês"] = resumo_mes["Competencia"].map(month_label_from_comp)
        resumo_mes = resumo_mes[["Mês", "Forecast_Bruto", "Forecast_Ponderado"]]

    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        f.to_excel(writer, index=False, sheet_name="Forecast")
        mensal_detalhe.to_excel(writer, index=False, sheet_name="Projeção Mensal")
        itens_locacao_export.to_excel(writer, index=False, sheet_name="Itens Locação")
        resumo_linha.to_excel(writer, index=False, sheet_name="Resumo Linha")
        resumo_mes.to_excel(writer, index=False, sheet_name="Resumo Mensal")
        history.to_excel(writer, index=False, sheet_name="Histórico")
        wb = writer.book
        header = wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY})
        money = wb.add_format({"num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00'})
        frames = [("Forecast", f), ("Projeção Mensal", mensal_detalhe), ("Itens Locação", itens_locacao_export), ("Resumo Linha", resumo_linha), ("Resumo Mensal", resumo_mes), ("Histórico", history)]
        for ws_name, frame in frames:
            ws = writer.sheets[ws_name]
            for idx, col in enumerate(frame.columns):
                ws.write(0, idx, col, header)
                width = min(max(len(str(col)) + 3, 13), 38)
                if any(x in norm(col) for x in ["VALOR", "RECEITA", "FORECAST"]):
                    ws.set_column(idx, idx, max(width, 18), money)
                else:
                    ws.set_column(idx, idx, width)
    return out.getvalue()


@st.cache_data(show_spinner=False, ttl=120)
def export_revenue_excel(revenue_monthly: pd.DataFrame, contracts: pd.DataFrame, forecast: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    detail = revenue_monthly.copy()
    if not detail.empty:
        detail["Mês"] = detail["Competencia"].map(month_label_from_comp)
        detail["Linha"] = detail["Linha"].map(line_label)
        detail = detail[["Linha", "Mês", "Receita_Contratada", "Forecast_Bruto", "Forecast_Ponderado", "Receita_Projetada_Bruta", "Receita_Projetada_Ponderada"]]
    annual = pd.DataFrame()
    if not revenue_monthly.empty:
        annual = revenue_monthly.groupby("Linha", as_index=False).agg(
            Receita_Contratada=("Receita_Contratada", "sum"),
            Forecast_Bruto=("Forecast_Bruto", "sum"),
            Forecast_Ponderado=("Forecast_Ponderado", "sum"),
            Receita_Projetada_Bruta=("Receita_Projetada_Bruta", "sum"),
            Receita_Projetada_Ponderada=("Receita_Projetada_Ponderada", "sum"),
        )
        annual["Cobertura_Contratada"] = np.where(annual["Receita_Projetada_Ponderada"] > 0, annual["Receita_Contratada"] / annual["Receita_Projetada_Ponderada"], 0.0)
        annual["Linha"] = annual["Linha"].map(line_label)
    contracts_export = contracts.copy()
    forecast_export = forecast.copy()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        annual.to_excel(writer, index=False, sheet_name="Resumo Receita")
        detail.to_excel(writer, index=False, sheet_name="Receita Mensal")
        contracts_export.to_excel(writer, index=False, sheet_name="Carteira Ativa")
        forecast_export.to_excel(writer, index=False, sheet_name="Forecast Comercial")
        wb = writer.book
        header = wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY})
        money = wb.add_format({"num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00'})
        percent = wb.add_format({"num_format": "0.0%"})
        for ws_name, frame in [("Resumo Receita", annual), ("Receita Mensal", detail), ("Carteira Ativa", contracts_export), ("Forecast Comercial", forecast_export)]:
            ws = writer.sheets[ws_name]
            for idx, col in enumerate(frame.columns):
                ws.write(0, idx, col, header)
                width = min(max(len(str(col)) + 3, 13), 40)
                if "COBERTURA" in norm(col):
                    ws.set_column(idx, idx, max(width, 16), percent)
                elif any(x in norm(col) for x in ["VALOR", "RECEITA", "FORECAST"]):
                    ws.set_column(idx, idx, max(width, 18), money)
                else:
                    ws.set_column(idx, idx, width)
    return out.getvalue()


@st.cache_data(show_spinner=False, ttl=120)
def export_budget_revenue_excel(view: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    detail = view.copy()
    if not detail.empty:
        detail["Mês"] = detail["Competencia"].map(month_label_from_comp)
        detail["Linha"] = detail["Linha"].map(line_label)
        detail["Variação proposta x base"] = np.where(
            detail["Base_Sugerida"].ne(0),
            detail["Budget_Proposto_Visual"] / detail["Base_Sugerida"] - 1,
            0.0,
        )
    annual = pd.DataFrame()
    if not view.empty:
        annual = view.groupby("Linha", as_index=False).agg(
            Receita_Contratada=("Receita_Contratada", "sum"),
            Referencia_Historica=("Referencia_Historica", "sum"),
            Forecast_Considerado=("Forecast_Ponderado_Considerado", "sum"),
            Forecast_Sulamita_Excluido=("Forecast_Sulamita_Excluido", "sum"),
            Base_Sugerida=("Base_Sugerida", "sum"),
            Budget_Proposto=("Budget_Proposto_Visual", "sum"),
            Budget_Aprovado=("Budget_Aprovado", "sum"),
        )
        annual["Linha"] = annual["Linha"].map(line_label)
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        annual.to_excel(writer, index=False, sheet_name="Resumo Budget")
        detail.to_excel(writer, index=False, sheet_name="Budget Mensal")
        wb = writer.book
        header = wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY})
        money = wb.add_format({"num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00'})
        percent = wb.add_format({"num_format": "0.0%"})
        for ws_name, frame in [("Resumo Budget", annual), ("Budget Mensal", detail)]:
            ws = writer.sheets[ws_name]
            for idx, col in enumerate(frame.columns):
                ws.write(0, idx, col, header)
                width = min(max(len(str(col)) + 3, 13), 42)
                if "VARIACAO" in norm(col):
                    ws.set_column(idx, idx, max(width, 18), percent)
                elif any(x in norm(col) for x in ["VALOR", "RECEITA", "FORECAST", "BUDGET", "BASE", "REFERENCIA"]):
                    ws.set_column(idx, idx, max(width, 18), money)
                else:
                    ws.set_column(idx, idx, width)
    return out.getvalue()


# =========================================================
# ACESSO E ESCOPO
# =========================================================
user = authenticate()
is_controladoria = user["perfil"] in {"CONTROLADORIA", "ADMIN"}
is_director = user["perfil"] in {"DIRETORIA", "ADMIN", "CONTROLADORIA"}
can_edit_all = is_controladoria
can_edit = user["perfil"] in {"GESTOR", "CONTROLADORIA", "ADMIN"}


def allowed_line(requested: str | None = None) -> str:
    if is_director:
        return norm(requested or "CONSOLIDADO")
    return user["linha"] if user["linha"] in LINES else "VENDAS"


def scope_df(df: pd.DataFrame, line: str = "CONSOLIDADO") -> pd.DataFrame:
    if df.empty:
        return df.copy()
    if not is_director:
        return df[df["Linha"].astype(str).map(norm).eq(user["linha"])].copy()
    if line != "CONSOLIDADO":
        return df[df["Linha"].astype(str).map(norm).eq(line)].copy()
    return df.copy()


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown(
        """
        <div class='first-sidebar'>
          <div class='brand'>FIRST<small>BUDGET & FORECAST</small></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    access = "Controladoria" if is_controladoria else ("Diretoria" if user["perfil"] == "DIRETORIA" else line_label(user["linha"]))
    st.markdown(
        f"<div class='user-pill'><div><b>{user['nome']}</b><small>{user['perfil'].title()}</small></div><span>{access}</span></div>",
        unsafe_allow_html=True,
    )
    if st.button("Sair", width="stretch"):
        st.session_state.pop("auth_user", None)
        st.rerun()

    st.markdown(f"#### Planejamento · {APP_YEAR}")
    if is_director:
        scope_choice = st.selectbox("Escopo", ["CONSOLIDADO"] + LINES, format_func=line_label)
    else:
        scope_choice = user["linha"]
        st.caption(f"Escopo: {line_label(scope_choice)}")

    pages = ["Visão Geral", "Receita 2027", "Budget de Receita", "Carteira Ativa", "Forecast Comercial", "Consolidação", "Histórico"]
    page = st.radio("Navegação", pages, label_visibility="collapsed")

    cfg = storage_config()
    st.divider()
    if st.button("↻ Atualizar dados", width="stretch", help="Força uma nova leitura das bases e do GitHub."):
        _load_table_cached.clear()
        _read_master_catalog.clear()
        _read_sulamita_purchase_history.clear()
        _read_active_contracts.clear()
        expand_monthly_forecast.clear()
        expand_active_contracts_monthly.clear()
        build_revenue_summary_monthly.clear()
        build_budget_revenue_basis.clear()
        export_budget_revenue_excel.clear()
        st.rerun()
    if cfg["mode"] == "github":
        st.caption(f"Persistência: GitHub ✓ · cache {TABLE_CACHE_TTL}s")
    else:
        st.caption("Persistência: Local · desenvolvimento")


# =========================================================
# DADOS
# =========================================================
forecast = load_forecast()
history = load_history() if page in {"Histórico", "Consolidação"} else pd.DataFrame(columns=HISTORY_COLUMNS)
budget_revenue_saved = load_budget_revenue() if page in {"Budget de Receita", "Visão Geral"} else pd.DataFrame(columns=BUDGET_REVENUE_COLUMNS)
budget_revenue_history = load_budget_revenue_history() if page == "Histórico" else pd.DataFrame(columns=BUDGET_REVENUE_HISTORY_COLUMNS)
active = forecast[forecast["Status"].astype(str).str.upper().eq("ATIVO")].copy() if not forecast.empty else forecast.copy()
input_catalog = build_input_catalog(forecast) if page not in {"Histórico", "Budget de Receita"} else {
    "clients": [], "products": [], "client_types": {}, "client_records": [], "product_records": [],
    "master_client_count": 0, "master_product_count": 0, "source": "", "warning": "",
}
CLIENT_OPTIONS = list(input_catalog.get("clients", []))
PRODUCT_OPTIONS = list(input_catalog.get("products", []))
CLIENT_TYPES = dict(input_catalog.get("client_types", {}))
CLIENT_RECORDS = [dict(x) for x in input_catalog.get("client_records", [])]
PRODUCT_RECORDS = [dict(x) for x in input_catalog.get("product_records", [])]

if page in {"Receita 2027", "Budget de Receita", "Carteira Ativa", "Forecast Comercial"}:
    active_contracts, active_contracts_meta = build_active_contracts_budget()
else:
    active_contracts = pd.DataFrame()
    active_contracts_meta = {"source": "", "warning": ""}
if not active_contracts.empty:
    contract_clients = [str(x).strip() for x in active_contracts["Cliente"].dropna().tolist() if str(x).strip()]
    contract_products = [str(x).strip() for x in active_contracts["Linha_Produto"].dropna().tolist() if str(x).strip()]
    CLIENT_OPTIONS = sorted({*CLIENT_OPTIONS, *contract_clients}, key=lambda x: norm(x))
    PRODUCT_OPTIONS = sorted({*PRODUCT_OPTIONS, *contract_products}, key=lambda x: norm(x))
    master_client_keys = {norm(x) for x in contract_clients}
    for name in CLIENT_OPTIONS:
        if norm(name) in master_client_keys:
            CLIENT_TYPES[name] = "Atual"

    known_client_records = {norm(r.get("value", "")) for r in CLIENT_RECORDS}
    for value in contract_clients:
        if norm(value) not in known_client_records:
            CLIENT_RECORDS.append({"value": value, "search_blob": value, "_search_blob_n": norm(value), "_value_n": norm(value), "_code_n": "", "_description_n": ""})
            known_client_records.add(norm(value))

    known_product_records = {norm(r.get("value", "")) for r in PRODUCT_RECORDS}
    for value in contract_products:
        if norm(value) not in known_product_records:
            PRODUCT_RECORDS.append({"value": value, "display": value, "search_blob": value, "_search_blob_n": norm(value), "_value_n": norm(value), "_code_n": "", "_description_n": ""})
            known_product_records.add(norm(value))

CLIENT_RECORDS.sort(key=lambda r: norm(r.get("value", "")))
PRODUCT_RECORDS.sort(key=lambda r: norm(r.get("value", "")))

# Referência histórica específica da Microtech / Sulamita. Só é carregada nas telas em que agrega valor.
sulamita_history = {
    "detail": pd.DataFrame(), "monthly": pd.DataFrame(), "source": "", "warning": "",
    "start": "", "end": "", "months": 0, "avg_monthly": 0.0, "annual_projection": 0.0, "clients": 0,
}
if page in {"Receita 2027", "Budget de Receita", "Forecast Comercial"} and scope_choice in {"CONSOLIDADO", "MICROTECH"}:
    master_path_for_history = _master_base_path()
    if master_path_for_history is not None:
        sulamita_history = _read_sulamita_purchase_history(str(master_path_for_history), master_path_for_history.stat().st_mtime_ns)
    else:
        sulamita_history["warning"] = "BASE BI não localizada no repositório do Budget."

CLIENT_VALUE_TO_DISPLAY: dict[str, str] = {}
PRODUCT_VALUE_TO_DISPLAY: dict[str, str] = {}
PRODUCT_DISPLAY_TO_VALUE: dict[str, str] = {}
PRODUCT_DISPLAY_OPTIONS: list[str] = []
if page == "Forecast Comercial":
    for r in CLIENT_RECORDS:
        value = str(r.get("value", "") or "").strip()
        if not value:
            continue
        extras = []
        if str(r.get("code", "") or "").strip() and norm(r.get("code", "")) != norm(value):
            extras.append(f"Cód: {r.get('code')}")
        location = " / ".join(x for x in [str(r.get("city", "") or "").strip(), str(r.get("uf", "") or "").strip()] if x)
        if location:
            extras.append(location)
        CLIENT_VALUE_TO_DISPLAY[value] = value + (" · " + " · ".join(extras) if extras else "")
    PRODUCT_VALUE_TO_DISPLAY = {str(r.get("value", "")): str(r.get("display", r.get("value", ""))) for r in PRODUCT_RECORDS if str(r.get("value", "")).strip()}
    PRODUCT_DISPLAY_TO_VALUE = {display: value for value, display in PRODUCT_VALUE_TO_DISPLAY.items()}
    PRODUCT_DISPLAY_OPTIONS = [PRODUCT_VALUE_TO_DISPLAY.get(value, value) for value in PRODUCT_OPTIONS]

active_scope = scope_df(active, scope_choice)
needs_forecast_monthly = page in {"Visão Geral", "Receita 2027", "Budget de Receita", "Consolidação"}
active_monthly = expand_monthly_forecast(active) if needs_forecast_monthly else pd.DataFrame(columns=FORECAST_COLUMNS)
active_monthly_scope = scope_df(active_monthly, scope_choice) if needs_forecast_monthly else pd.DataFrame(columns=FORECAST_COLUMNS)



def render_sulamita_history_reference(expanded: bool = False) -> None:
    """Exibe a referência histórica dos clientes Sulamita sem somá-la ao forecast atual."""
    detail = sulamita_history.get("detail", pd.DataFrame())
    warning = str(sulamita_history.get("warning", "") or "")
    with st.expander("Microtech · referência histórica dos clientes Sulamita", expanded=expanded):
        st.caption(
            "Base automática para planejamento: média mensal dos últimos meses disponíveis, incluindo meses sem compra. "
            "Esta referência não é somada ao forecast comercial, evitando duplicidade antes da definição do Budget de Receita."
        )
        if warning:
            st.warning(warning)
            return
        if detail is None or detail.empty:
            st.info("Ainda não há histórico suficiente para calcular a referência Sulamita.")
            return

        months = int(sulamita_history.get("months", 0) or 0)
        period_text = f"{month_label_from_comp(str(sulamita_history.get('start', '')))} a {month_label_from_comp(str(sulamita_history.get('end', '')))}"
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi("Média mensal Sulamita", brl(float(sulamita_history.get("avg_monthly", 0.0))), f"{months} mês(es) na base")
        with c2:
            kpi("Referência anual 2027", brl(float(sulamita_history.get("annual_projection", 0.0))), "Média mensal × 12")
        with c3:
            kpi("Clientes com histórico", f"{int(sulamita_history.get('clients', 0) or 0)}", "Clientes atendidos pela Sulamita")
        with c4:
            kpi("Período analisado", period_text, "Últimos meses disponíveis")

        q = st.text_input(
            "🔎 Buscar cliente na referência Sulamita",
            key=f"sulamita_reference_search_{'expanded' if expanded else 'collapsed'}",
            placeholder="Nome ou parte do cliente...",
        )
        show = detail.copy()
        if q:
            tokens = [t for t in norm(q).split() if t]
            mask = show["Cliente"].fillna("").astype(str).map(norm).map(lambda x: all(t in x for t in tokens))
            show = show.loc[mask].copy()
        show = show.rename(columns={
            "Total_Historico": "Histórico no período",
            "Meses_Com_Compra": "Meses com compra",
            "Meses_Base": "Meses base",
            "Frequencia_Compra": "Frequência",
            "Media_Mensal": "Média mensal",
            "Media_3M": "Média últimos 3 meses",
            "Projecao_2027": "Referência 2027",
        })
        st.dataframe(
            show,
            hide_index=True,
            width="stretch",
            column_config={
                "Histórico no período": st.column_config.NumberColumn(format="R$ %.2f"),
                "Frequência": st.column_config.NumberColumn(format="%.1f%%"),
                "Média mensal": st.column_config.NumberColumn(format="R$ %.2f"),
                "Média últimos 3 meses": st.column_config.NumberColumn(format="R$ %.2f"),
                "Referência 2027": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )
        st.caption(
            "Critério: para cada cliente, o total do período é dividido por todos os meses da janela, inclusive meses sem compra. "
            "A coluna de 3 meses é apenas um sinal de tendência; a referência 2027 usa a média mensal integral."
        )

# =========================================================
# PÁGINA: VISÃO GERAL
# =========================================================
if page == "Visão Geral":
    hero("First Budget 2027", "Forecast comercial como ponto de partida do orçamento anual.")

    overview_search = st.text_input(
        "🔎 Busca inteligente",
        key="overview_smart_search",
        placeholder="Cliente, contrato, código, descrição, linha, grupo, segmento, vendedor...",
        help="A busca cruza os lançamentos com os metadados do cadastro mestre. Você pode combinar vários termos.",
    )
    if overview_search:
        active_scope = filter_budget_search(active_scope, overview_search)
        allowed_ids = set(active_scope["ID"].astype(str)) if not active_scope.empty else set()
        active_monthly_scope = active_monthly_scope[active_monthly_scope["ID"].astype(str).isin(allowed_ids)].copy()

    bruto = float(active_monthly_scope["Receita_Prevista"].sum()) if not active_monthly_scope.empty else 0.0
    ponderado = float(active_monthly_scope["Receita_Ponderada"].sum()) if not active_monthly_scope.empty else 0.0
    clientes = int(active_scope["Cliente"].replace("", np.nan).nunique()) if not active_scope.empty else 0
    registros = int(len(active_scope))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Forecast bruto", brl(bruto), f"{line_label(scope_choice)} · {APP_YEAR}")
    with c2:
        kpi("Forecast ponderado", brl(ponderado), "Aplicação da probabilidade informada")
    with c3:
        kpi("Cobertura ponderada", pct(ponderado / bruto if bruto else 0), "Ponderado ÷ bruto")
    with c4:
        kpi("Clientes previstos", f"{clientes}", f"{registros} lançamentos ativos")

    if budget_revenue_saved is not None and not budget_revenue_saved.empty:
        budget_scope_saved = budget_revenue_saved.copy()
        if not is_director:
            budget_scope_saved = budget_scope_saved[budget_scope_saved["Linha"].astype(str).map(norm).eq(user["linha"])]
        elif scope_choice != "CONSOLIDADO":
            budget_scope_saved = budget_scope_saved[budget_scope_saved["Linha"].astype(str).map(norm).eq(scope_choice)]
        if not budget_scope_saved.empty:
            proposed_saved = float(pd.to_numeric(budget_scope_saved["Budget_Proposto"], errors="coerce").fillna(0).sum())
            approved_saved = float(pd.to_numeric(budget_scope_saved["Budget_Aprovado"], errors="coerce").fillna(0).sum())
            approved_lines = int(budget_scope_saved.loc[budget_scope_saved["Status"].astype(str).str.upper().eq("APROVADO"), "Linha"].nunique())
            section("Budget de Receita")
            b1, b2, b3 = st.columns(3)
            with b1:
                kpi("Budget proposto gravado", brl(proposed_saved), "Propostas já salvas pela Controladoria")
            with b2:
                kpi("Budget aprovado", brl(approved_saved), "Última versão oficial aprovada")
            with b3:
                kpi("Linhas aprovadas", f"{approved_lines}", "Das quatro linhas de negócio")

    section("Evolução mensal")
    if active_monthly_scope.empty:
        st.info("Ainda não existem lançamentos de forecast para este escopo.")
    else:
        monthly = active_monthly_scope.groupby("Competencia", as_index=False).agg(
            Bruto=("Receita_Prevista", "sum"),
            Ponderado=("Receita_Ponderada", "sum"),
        )
        all_comp = pd.DataFrame({"Competencia": [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]})
        monthly = all_comp.merge(monthly, on="Competencia", how="left").fillna(0)
        monthly["Mês"] = monthly["Competencia"].map(month_label_from_comp)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["Mês"], y=monthly["Bruto"], name="Forecast bruto", marker_color=BLUE))
        fig.add_trace(go.Scatter(x=monthly["Mês"], y=monthly["Ponderado"], name="Forecast ponderado", mode="lines+markers", line=dict(color=NAVY, width=3)))
        fig.update_layout(title="Forecast mensal · 2027")
        st.plotly_chart(plot_layout(fig), width="stretch", config={"displayModeBar": False})

        if is_director and scope_choice == "CONSOLIDADO":
            section("Participação por linha")
            by_line = active_monthly_scope.groupby("Linha", as_index=False).agg(
                Bruto=("Receita_Prevista", "sum"), Ponderado=("Receita_Ponderada", "sum")
            )
            by_line["Linha_Label"] = by_line["Linha"].map(line_label)
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=by_line["Linha_Label"], y=by_line["Bruto"], name="Bruto", marker_color=CYAN))
            fig2.add_trace(go.Bar(x=by_line["Linha_Label"], y=by_line["Ponderado"], name="Ponderado", marker_color=NAVY_2))
            fig2.update_layout(title="Forecast por linha de negócio", barmode="group")
            st.plotly_chart(plot_layout(fig2, 330), width="stretch", config={"displayModeBar": False})


    section("Carteira ativa · base contratada")
    carteira_scope = scope_active_contracts(active_contracts, scope_choice)
    if overview_search:
        carteira_scope = filter_budget_search(carteira_scope, overview_search)
    if carteira_scope.empty:
        st.info("A planilha de contratos ativos ainda não foi localizada no repositório do Budget.")
    else:
        receita_contratada = float(carteira_scope["Receita_2027_Planejada"].sum())
        mensal = float(carteira_scope["Valor_Mensal_Base"].sum())
        sem_valor = int(carteira_scope["Valor_Mensal_Base"].le(0).sum())
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            kpi("Receita contratada 2027", brl(receita_contratada), "Base atualizada de contratos ativos")
        with a2:
            kpi("Faturamento mensal", brl(mensal), "Somatório dos valores mensais da carteira")
        with a3:
            kpi("Contratos / linhas", f"{len(carteira_scope)}", "Registros ativos na base")
        with a4:
            kpi("Sem valor mensal", f"{sem_valor}", "Não compõem receita enquanto estiverem zerados")


# =========================================================
# PÁGINA: RECEITA 2027
# =========================================================
elif page == "Receita 2027":
    hero("Receita 2027", "Carteira ativa + novas receitas previstas, mantendo claramente separado o que já está contratado do que ainda depende do comercial.")

    contracts_scope = scope_active_contracts(active_contracts, scope_choice)
    forecast_scope = scope_df(active, scope_choice)
    revenue_search = st.text_input(
        "🔎 Buscar na receita",
        key="revenue_smart_search",
        placeholder="Cliente, contrato, código, descrição, produto, linha, grupo, gerente...",
        help="A busca é aplicada simultaneamente à carteira contratada e ao forecast comercial.",
    )
    if revenue_search:
        contracts_scope = filter_budget_search(contracts_scope, revenue_search)
        forecast_scope = filter_budget_search(forecast_scope, revenue_search)

    contract_monthly_scope = expand_active_contracts_monthly(contracts_scope)
    forecast_monthly_scope = expand_monthly_forecast(forecast_scope)
    revenue_monthly = build_revenue_summary_monthly(contract_monthly_scope, forecast_monthly_scope)

    receita_contratada = float(revenue_monthly["Receita_Contratada"].sum()) if not revenue_monthly.empty else 0.0
    forecast_bruto = float(revenue_monthly["Forecast_Bruto"].sum()) if not revenue_monthly.empty else 0.0
    forecast_pond = float(revenue_monthly["Forecast_Ponderado"].sum()) if not revenue_monthly.empty else 0.0
    proj_pond = float(revenue_monthly["Receita_Projetada_Ponderada"].sum()) if not revenue_monthly.empty else 0.0
    cobertura = receita_contratada / proj_pond if proj_pond else 0.0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Receita contratada", brl(receita_contratada), f"Carteira ativa considerada em {APP_YEAR}")
    with c2:
        kpi("Forecast novo · bruto", brl(forecast_bruto), "Novas vendas, serviços e contratos")
    with c3:
        kpi("Forecast novo · ponderado", brl(forecast_pond), "Aplicação da probabilidade comercial")
    with c4:
        kpi("Projeção 2027", brl(proj_pond), f"Contratada + forecast ponderado · {pct(cobertura)} já contratado")

    if scope_choice in {"CONSOLIDADO", "MICROTECH"}:
        render_sulamita_history_reference(expanded=(scope_choice == "MICROTECH"))

    if revenue_monthly.empty:
        st.info("Não há receita contratada nem forecast comercial para este escopo/busca.")
    else:
        section("Composição mensal da receita")
        monthly = revenue_monthly.groupby("Competencia", as_index=False).agg(
            Contratada=("Receita_Contratada", "sum"),
            Forecast_Ponderado=("Forecast_Ponderado", "sum"),
            Projecao=("Receita_Projetada_Ponderada", "sum"),
        )
        all_comp = pd.DataFrame({"Competencia": [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]})
        monthly = all_comp.merge(monthly, on="Competencia", how="left").fillna(0)
        monthly["Mês"] = monthly["Competencia"].map(month_label_from_comp)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=monthly["Mês"], y=monthly["Contratada"], name="Carteira contratada", marker_color=NAVY))
        fig.add_trace(go.Bar(x=monthly["Mês"], y=monthly["Forecast_Ponderado"], name="Forecast novo ponderado", marker_color=CYAN))
        fig.update_layout(title="Receita projetada por mês · 2027", barmode="stack")
        st.plotly_chart(plot_layout(fig, 370), width="stretch", config={"displayModeBar": False})

        section("Resumo anual por linha")
        annual = revenue_monthly.groupby("Linha", as_index=False).agg(
            Receita_Contratada=("Receita_Contratada", "sum"),
            Forecast_Bruto=("Forecast_Bruto", "sum"),
            Forecast_Ponderado=("Forecast_Ponderado", "sum"),
            Receita_Projetada_Bruta=("Receita_Projetada_Bruta", "sum"),
            Receita_Projetada_Ponderada=("Receita_Projetada_Ponderada", "sum"),
        )
        annual["Cobertura_Contratada"] = np.where(
            annual["Receita_Projetada_Ponderada"] > 0,
            annual["Receita_Contratada"] / annual["Receita_Projetada_Ponderada"],
            0.0,
        )
        annual["Linha"] = annual["Linha"].map(line_label)
        st.dataframe(
            annual,
            hide_index=True,
            width="stretch",
            column_config={
                "Receita_Contratada": st.column_config.NumberColumn("Receita contratada", format="R$ %.2f"),
                "Forecast_Bruto": st.column_config.NumberColumn("Forecast bruto", format="R$ %.2f"),
                "Forecast_Ponderado": st.column_config.NumberColumn("Forecast ponderado", format="R$ %.2f"),
                "Receita_Projetada_Bruta": st.column_config.NumberColumn("Projeção bruta", format="R$ %.2f"),
                "Receita_Projetada_Ponderada": st.column_config.NumberColumn("Projeção ponderada", format="R$ %.2f"),
                "Cobertura_Contratada": st.column_config.NumberColumn("% já contratado", format="%.1f%%"),
            },
        )

        section("Matriz mensal · projeção ponderada")
        matrix = revenue_monthly.pivot_table(index="Linha", columns="Competencia", values="Receita_Projetada_Ponderada", aggfunc="sum", fill_value=0)
        for comp in [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]:
            if comp not in matrix.columns:
                matrix[comp] = 0.0
        matrix = matrix[[f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]].reset_index()
        matrix["Linha"] = matrix["Linha"].map(line_label)
        matrix = matrix.rename(columns={f"{APP_YEAR}-{m:02d}": MONTHS[m] for m in range(1, 13)})
        matrix["Total"] = matrix[[MONTHS[m] for m in range(1, 13)]].sum(axis=1)
        st.dataframe(
            matrix,
            hide_index=True,
            width="stretch",
            column_config={col: st.column_config.NumberColumn(format="R$ %.2f") for col in [MONTHS[m] for m in range(1, 13)] + ["Total"]},
        )

        section("Exportação da receita")
        revenue_xlsx = export_revenue_excel(revenue_monthly, contracts_scope, forecast_scope)
        st.download_button(
            "Baixar Receita 2027 em Excel",
            data=revenue_xlsx,
            file_name=f"First_Budget_Receita_{APP_YEAR}_{norm(scope_choice).replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


# =========================================================
# PÁGINA: BUDGET DE RECEITA
# =========================================================
elif page == "Budget de Receita":
    hero("Budget de Receita 2027", "Transforma as bases já existentes em proposta orçamentária sem alterar Carteira Ativa ou Forecast Comercial.")

    all_contract_monthly = expand_active_contracts_monthly(active_contracts)
    all_forecast_monthly = expand_monthly_forecast(active)
    sulamita_detail_budget = sulamita_history.get("detail", pd.DataFrame()) if isinstance(sulamita_history, dict) else pd.DataFrame()
    sulamita_avg_budget = float(sulamita_history.get("avg_monthly", 0.0) or 0.0) if isinstance(sulamita_history, dict) else 0.0
    budget_basis_all = build_budget_revenue_basis(
        all_contract_monthly, all_forecast_monthly, sulamita_detail_budget, sulamita_avg_budget
    )
    budget_view_all = merge_budget_revenue_overrides(budget_basis_all, budget_revenue_saved)

    if not is_director:
        budget_view = budget_view_all[budget_view_all["Linha"].eq(user["linha"])].copy()
    elif scope_choice != "CONSOLIDADO":
        budget_view = budget_view_all[budget_view_all["Linha"].eq(scope_choice)].copy()
    else:
        budget_view = budget_view_all.copy()

    budget_suggested = float(budget_view["Base_Sugerida"].sum()) if not budget_view.empty else 0.0
    budget_proposed = float(budget_view["Budget_Proposto_Visual"].sum()) if not budget_view.empty else 0.0
    budget_approved = float(budget_view["Budget_Aprovado"].sum()) if not budget_view.empty else 0.0
    budget_gap = budget_proposed - budget_suggested

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Base sugerida", brl(budget_suggested), "Contratos + referência histórica aplicável + forecast considerado")
    with c2:
        kpi("Budget proposto", brl(budget_proposed), "Valor em elaboração pela Controladoria")
    with c3:
        kpi("Budget aprovado", brl(budget_approved), "Última versão aprovada")
    with c4:
        kpi("Ajuste vs. base", brl(budget_gap), pct(budget_gap / budget_suggested) if budget_suggested else "Sem base comparável")

    section("Composição da base sugerida")
    annual_budget = budget_view.groupby("Linha", as_index=False).agg(
        Receita_Contratada=("Receita_Contratada", "sum"),
        Referencia_Historica=("Referencia_Historica", "sum"),
        Forecast_Considerado=("Forecast_Ponderado_Considerado", "sum"),
        Forecast_Sulamita_Excluido=("Forecast_Sulamita_Excluido", "sum"),
        Base_Sugerida=("Base_Sugerida", "sum"),
        Budget_Proposto=("Budget_Proposto_Visual", "sum"),
        Budget_Aprovado=("Budget_Aprovado", "sum"),
    ) if not budget_view.empty else pd.DataFrame()
    if not annual_budget.empty:
        status_by_line = (budget_view.groupby("Linha")["Status"].apply(lambda s: "APROVADO" if len(s) and s.astype(str).str.upper().eq("APROVADO").all() else "EM ELABORAÇÃO").to_dict())
        annual_budget["Status"] = annual_budget["Linha"].map(status_by_line)
        annual_budget["Ajuste_vs_Base"] = np.where(annual_budget["Base_Sugerida"].ne(0), annual_budget["Budget_Proposto"] / annual_budget["Base_Sugerida"] - 1, 0.0)
        annual_budget["Linha"] = annual_budget["Linha"].map(line_label)
        st.dataframe(
            annual_budget, hide_index=True, width="stretch",
            column_config={
                "Receita_Contratada": st.column_config.NumberColumn("Contratada", format="R$ %.2f"),
                "Referencia_Historica": st.column_config.NumberColumn("Ref. histórica", format="R$ %.2f"),
                "Forecast_Considerado": st.column_config.NumberColumn("Forecast considerado", format="R$ %.2f"),
                "Forecast_Sulamita_Excluido": st.column_config.NumberColumn("Forecast Sulamita separado", format="R$ %.2f"),
                "Base_Sugerida": st.column_config.NumberColumn("Base sugerida", format="R$ %.2f"),
                "Budget_Proposto": st.column_config.NumberColumn("Budget proposto", format="R$ %.2f"),
                "Budget_Aprovado": st.column_config.NumberColumn("Budget aprovado", format="R$ %.2f"),
                "Ajuste_vs_Base": st.column_config.NumberColumn("Ajuste x base", format="%.1f%%"),
            },
        )

    st.markdown(
        "<div class='storage-note'><b>Regra Microtech:</b> a média histórica dos clientes Sulamita entra como base recorrente. "
        "Forecast lançado para um cliente Sulamita que já possui histórico fica separado da base sugerida para evitar dupla contagem. "
        "Se o forecast for realmente incremental, a Controladoria incorpora o aumento no Budget Proposto.</div>",
        unsafe_allow_html=True,
    )

    section("Planejamento mensal")
    available_budget_lines = [ln for ln in LINES if not budget_view_all[budget_view_all["Linha"].eq(ln)].empty]
    if is_director and scope_choice in LINES:
        available_budget_lines = [scope_choice]
    if is_director:
        default_line = scope_choice if scope_choice in LINES else (available_budget_lines[0] if available_budget_lines else "MICROTECH")
        detail_line = st.selectbox("Linha para detalhar", available_budget_lines or LINES, index=(available_budget_lines or LINES).index(default_line) if default_line in (available_budget_lines or LINES) else 0, format_func=line_label)
    else:
        detail_line = user["linha"]
        st.caption(f"Linha: {line_label(detail_line)}")

    line_view = budget_view_all[budget_view_all["Linha"].eq(detail_line)].sort_values("Competencia").copy()
    line_status = "APROVADO" if not line_view.empty and line_view["Status"].astype(str).str.upper().eq("APROVADO").all() else "EM ELABORAÇÃO"
    st.markdown(f"<span class='pill'>{line_label(detail_line)} · {line_status}</span>", unsafe_allow_html=True)

    monthly_edit = line_view[[
        "Competencia", "Receita_Contratada", "Referencia_Historica",
        "Forecast_Ponderado_Considerado", "Forecast_Sulamita_Excluido",
        "Base_Sugerida", "Budget_Proposto_Visual", "Budget_Aprovado", "Status", "Justificativa"
    ]].copy()
    monthly_edit["Mês"] = monthly_edit["Competencia"].map(month_label_from_comp)
    monthly_edit = monthly_edit.rename(columns={"Budget_Proposto_Visual": "Budget_Proposto"})
    monthly_edit["Ajuste_%"] = np.where(
        monthly_edit["Base_Sugerida"].ne(0), monthly_edit["Budget_Proposto"] / monthly_edit["Base_Sugerida"] - 1, 0.0
    )
    monthly_edit = monthly_edit[[
        "Competencia", "Mês", "Receita_Contratada", "Referencia_Historica",
        "Forecast_Ponderado_Considerado", "Forecast_Sulamita_Excluido",
        "Base_Sugerida", "Budget_Proposto", "Ajuste_%", "Budget_Aprovado", "Status", "Justificativa"
    ]]

    if is_controladoria and line_status != "APROVADO":
        edited_budget = st.data_editor(
            monthly_edit, hide_index=True, width="stretch", key=f"budget_revenue_editor_{detail_line}",
            disabled=[
                "Competencia", "Mês", "Receita_Contratada", "Referencia_Historica",
                "Forecast_Ponderado_Considerado", "Forecast_Sulamita_Excluido",
                "Base_Sugerida", "Ajuste_%", "Budget_Aprovado", "Status",
            ],
            column_config={
                "Competencia": None,
                "Receita_Contratada": st.column_config.NumberColumn("Contratada", format="R$ %.2f"),
                "Referencia_Historica": st.column_config.NumberColumn("Ref. histórica", format="R$ %.2f"),
                "Forecast_Ponderado_Considerado": st.column_config.NumberColumn("Forecast considerado", format="R$ %.2f"),
                "Forecast_Sulamita_Excluido": st.column_config.NumberColumn("Sulamita separado", format="R$ %.2f"),
                "Base_Sugerida": st.column_config.NumberColumn("Base sugerida", format="R$ %.2f"),
                "Budget_Proposto": st.column_config.NumberColumn("Budget proposto", min_value=0.0, step=1000.0, format="R$ %.2f"),
                "Ajuste_%": st.column_config.NumberColumn("Ajuste x base", format="%.1f%%"),
                "Budget_Aprovado": st.column_config.NumberColumn("Aprovado", format="R$ %.2f"),
                "Justificativa": st.column_config.TextColumn("Justificativa / premissa"),
            },
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("Salvar proposta", width="stretch", type="secondary"):
                payload = edited_budget.copy()
                payload["Status"] = "EM ELABORAÇÃO"
                try:
                    save_budget_revenue_line(user, detail_line, payload, action="SALVAR PROPOSTA")
                    st.success("Budget proposto salvo sem alterar as bases de origem.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível salvar o Budget: {exc}")
        with b2:
            approve_confirm = st.checkbox("Confirmo a aprovação desta linha", key=f"approve_budget_{detail_line}")
            if st.button("Aprovar Budget da linha", width="stretch", type="primary", disabled=not approve_confirm):
                payload = edited_budget.copy()
                payload["Status"] = "APROVADO"
                payload["Budget_Aprovado"] = pd.to_numeric(payload["Budget_Proposto"], errors="coerce").fillna(0.0)
                try:
                    save_budget_revenue_line(user, detail_line, payload, action="APROVAR BUDGET")
                    st.success(f"Budget de {line_label(detail_line)} aprovado.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível aprovar o Budget: {exc}")
    else:
        st.dataframe(
            monthly_edit, hide_index=True, width="stretch",
            column_config={
                "Competencia": None,
                "Receita_Contratada": st.column_config.NumberColumn("Contratada", format="R$ %.2f"),
                "Referencia_Historica": st.column_config.NumberColumn("Ref. histórica", format="R$ %.2f"),
                "Forecast_Ponderado_Considerado": st.column_config.NumberColumn("Forecast considerado", format="R$ %.2f"),
                "Forecast_Sulamita_Excluido": st.column_config.NumberColumn("Sulamita separado", format="R$ %.2f"),
                "Base_Sugerida": st.column_config.NumberColumn("Base sugerida", format="R$ %.2f"),
                "Budget_Proposto": st.column_config.NumberColumn("Budget proposto", format="R$ %.2f"),
                "Ajuste_%": st.column_config.NumberColumn("Ajuste x base", format="%.1f%%"),
                "Budget_Aprovado": st.column_config.NumberColumn("Aprovado", format="R$ %.2f"),
            },
        )
        if is_controladoria and line_status == "APROVADO":
            if st.button("Reabrir Budget desta linha", width="stretch", type="secondary"):
                try:
                    set_budget_revenue_status(user, detail_line, budget_view_all, approved=False)
                    st.success("Budget reaberto para edição. A última versão aprovada permanece registrada até nova aprovação.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível reabrir: {exc}")

    section("Exportação")
    budget_export_scope = budget_view.copy()
    budget_xlsx = export_budget_revenue_excel(budget_export_scope)
    st.download_button(
        "Baixar Budget de Receita em Excel",
        data=budget_xlsx,
        file_name=f"First_Budget_Receita_Oficial_{APP_YEAR}_{norm(scope_choice).replace(' ', '_')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


# =========================================================
# PÁGINA: CARTEIRA ATIVA
# =========================================================
elif page == "Carteira Ativa":
    hero("Carteira Ativa 2027", "A base revisada de contratos existentes forma automaticamente a receita contratada do orçamento.")

    source_name = str(active_contracts_meta.get("source", "") or "")
    warning = str(active_contracts_meta.get("warning", "") or "")
    if source_name:
        st.caption(f"Fonte operacional: {source_name}")
    if warning:
        st.warning(warning)

    carteira_scope = scope_active_contracts(active_contracts, scope_choice)
    carteira_search = st.text_input(
        "🔎 Buscar na carteira",
        key="active_contracts_smart_search",
        placeholder="Contrato, cliente, código, descrição, linha, grupo, gerente, vendedor...",
        help="Use um ou vários termos. A busca também consulta os metadados do cadastro de produtos.",
    )
    if carteira_search:
        carteira_scope = filter_budget_search(carteira_scope, carteira_search)
    if carteira_scope.empty:
        st.info("Nenhum contrato encontrado para este escopo/busca ou a planilha de contratos ativos ainda não foi carregada.")
    else:
        monthly_runrate = float(carteira_scope["Valor_Mensal_Base"].sum())
        receita_2027 = float(carteira_scope["Receita_2027_Planejada"].sum())
        sem_valor = int(carteira_scope["Valor_Mensal_Base"].le(0).sum())
        clientes_carteira = int(carteira_scope["Cliente"].fillna("").astype(str).str.strip().replace("", np.nan).nunique())

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            kpi("Receita contratada 2027", brl(receita_2027), "Calculada diretamente da base atualizada")
        with c2:
            kpi("Faturamento mensal", brl(monthly_runrate), "Valor mensal atual da carteira")
        with c3:
            kpi("Contratos / linhas", f"{len(carteira_scope)}", f"{clientes_carteira} clientes na carteira")
        with c4:
            kpi("Sem valor mensal", f"{sem_valor}", "Registros zerados não entram na receita")

        st.markdown(
            "<div class='storage-note'><b>Base oficial:</b> os contratos carregados nesta tela já são considerados revisados. "
            "Quando a planilha trouxer término ou meses de vigência em 2027, o Budget respeita essa informação; nos demais casos, considera a vigência até dezembro de 2027.</div>",
            unsafe_allow_html=True,
        )

        section("Contratos existentes")
        view = carteira_scope.copy()
        view["Contrato"] = view["Numero_Contrato"].fillna("").astype(str)
        view["Cliente"] = view["Cliente"].fillna("").astype(str)
        view["Início"] = view["Data_Inicio"].map(date_br)
        view["Fim"] = view["Data_Fim"].map(date_br) if "Data_Fim" in view.columns else ""
        view["Linha"] = view["Linha_Budget"].map(line_label)
        view["Valor mensal"] = view["Valor_Mensal_Base"]
        view["Receita 2027"] = view["Receita_2027_Planejada"]
        view["Meses 2027"] = view["Meses_2027"].astype(int)
        view["Produto / linha"] = view["Linha_Produto"].fillna("").astype(str)
        view["Qtd. eq."] = view["Qtd_Equipamentos"]
        display_cols = ["Contrato", "Cliente", "Linha", "Produto / linha", "Início", "Fim", "Valor mensal", "Meses 2027", "Receita 2027", "Qtd. eq."]
        st.dataframe(
            view[display_cols], hide_index=True, width="stretch",
            column_config={
                "Valor mensal": st.column_config.NumberColumn(format="R$ %.2f"),
                "Receita 2027": st.column_config.NumberColumn(format="R$ %.2f"),
                "Qtd. eq.": st.column_config.NumberColumn(format="%.0f"),
            },
        )


# =========================================================
# PÁGINA: FORECAST COMERCIAL
# =========================================================
elif page == "Forecast Comercial":
    hero("Forecast Comercial 2027", "Venda e serviço são lançados por competência; locação é projetada automaticamente pelo prazo do contrato.")

    source_name = str(input_catalog.get("source", "") or "")
    if source_name:
        st.caption(
            f"Cadastros carregados de {source_name}: "
            f"{int(input_catalog.get('master_client_count', 0)):,} clientes e "
            f"{int(input_catalog.get('master_product_count', 0)):,} produtos.".replace(",", ".")
        )
    else:
        st.caption("BASE BI não localizada neste repositório. As listas usam apenas clientes e produtos já gravados no Budget.")

    if scope_choice in {"CONSOLIDADO", "MICROTECH"}:
        render_sulamita_history_reference(expanded=(scope_choice == "MICROTECH"))

    if can_edit:
        section("Novo lançamento")
        default_rev_idx = 1 if (not can_edit_all and user.get("linha") == "LOCACAO") else 0
        new_revenue_type = st.radio(
            "Tipo de receita",
            ["Venda", "Locação", "Serviço"],
            index=default_rev_idx,
            horizontal=True,
            key="new_revenue_type",
            help="Na locação, informe início, prazo e os equipamentos. O sistema soma as mensalidades dos itens e distribui a receita nas competências de 2027.",
        )

        # Busca única para Venda, Serviço e Locação. O produto pode ser localizado por
        # código, descrição, linha, grupo, segmento, fornecedor ou NCM.
        st.markdown("**Localizar cadastro**")
        s1, s2 = st.columns(2)
        with s1:
            client_search = st.text_input(
                "🔎 Buscar cliente", key="new_client_smart_search",
                placeholder="Nome, código, cidade, UF, vendedor, gerente...",
                help="Digite um ou vários termos. A busca cruza todas as camadas disponíveis do cadastro.",
            )
            sales_client_options = _search_records(CLIENT_RECORDS, client_search, "value", limit=120)
            if not CLIENT_RECORDS:
                sales_client_options = filter_catalog_options(CLIENT_OPTIONS, client_search)
            st.caption(f"{len(sales_client_options)} cliente(s) exibido(s)" + (" · refine a busca" if len(sales_client_options) >= 120 else ""))
        with s2:
            product_search = st.text_input(
                "🔎 Buscar equipamento / produto", key="new_product_smart_search",
                placeholder="Código, descrição, linha, grupo, segmento, fornecedor, NCM...",
                help="Ex.: 'monitor microtech', um código parcial ou o nome do grupo. Todos os termos digitados precisam aparecer em alguma camada do cadastro.",
            )
            sales_product_options = _search_records(PRODUCT_RECORDS, product_search, "value", limit=120)
            rental_product_options = _search_records(PRODUCT_RECORDS, product_search, "display", limit=120)
            if not PRODUCT_RECORDS:
                sales_product_options = filter_catalog_options(PRODUCT_OPTIONS, product_search)
                rental_product_options = sales_product_options
            st.caption(f"{len(sales_product_options)} produto(s) exibido(s)" + (" · refine a busca" if len(sales_product_options) >= 120 else ""))

        with st.form("new_forecast_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            with a:
                if can_edit_all:
                    new_line = st.selectbox("Linha de negócio", LINES, format_func=line_label)
                else:
                    new_line = user["linha"]
                    st.text_input("Linha de negócio", value=line_label(new_line), disabled=True)
                base_client_choices = sales_client_options
                client_choices = base_client_choices + [NEW_CLIENT_OPTION]
                cliente_selecionado = st.selectbox(
                    "Cliente *", client_choices,
                    index=0 if base_client_choices else len(client_choices) - 1,
                    format_func=lambda value: CLIENT_VALUE_TO_DISPLAY.get(value, value),
                    help="Use a busca acima para reduzir a lista. Você também pode digitar dentro desta seleção.",
                )
                novo_cliente = st.text_input("Novo cliente", placeholder="Preencha somente se escolher + Novo cliente")
                tipo_cliente = CLIENT_TYPES.get(cliente_selecionado, "Novo") if cliente_selecionado != NEW_CLIENT_OPTION else "Novo"
                st.caption(f"Classificação: {tipo_cliente}")

            if new_revenue_type == "Locação":
                with b:
                    inicio_contrato = st.date_input(
                        "Início do contrato",
                        value=date(APP_YEAR, 1, 1),
                        min_value=date(APP_YEAR - 7, 1, 1),
                        max_value=date(APP_YEAR, 12, 31),
                        format="DD/MM/YYYY",
                    )
                    prazo_contrato = st.number_input("Prazo do contrato (meses)", min_value=1, max_value=120, value=12, step=1)
                with c:
                    numero_contrato = st.text_input("Nº / referência do contrato", help="Opcional no forecast. Pode ser preenchido quando o contrato estiver definido.")
                    st.caption("O mesmo contrato pode conter vários equipamentos. A receita mensal será a soma de todos os itens.")

                st.markdown("**Equipamentos do contrato**")
                rental_seed = pd.DataFrame([{
                    "Equipamento": "", "Equipamento_Novo": "", "Quantidade": 1.0,
                    "Valor_Mensal_Unitario": 0.0, "Observacao_Item": ""
                }])
                preserved_equipment = _editor_selected_equipment_values("new_rental_items")
                rental_choices = []
                seen_rental = set()
                for value in preserved_equipment + rental_product_options:
                    key = norm(value)
                    if value and key and key not in seen_rental:
                        seen_rental.add(key)
                        rental_choices.append(value)
                equipment_cfg = (
                    st.column_config.SelectboxColumn(
                        "Equipamento / produto *", options=[""] + rental_choices + [NEW_PRODUCT_OPTION], required=True,
                        help="A lista acima já foi filtrada pela busca inteligente. O rótulo mostra código/descrição e, quando disponível, Linha e Grupo.",
                    ) if rental_choices else st.column_config.TextColumn("Equipamento / produto *", required=True)
                )
                itens_locacao = st.data_editor(
                    rental_seed, num_rows="dynamic", hide_index=True, width="stretch", key="new_rental_items",
                    column_config={
                        "Equipamento": equipment_cfg,
                        "Equipamento_Novo": st.column_config.TextColumn("Novo equipamento", help="Preencha somente quando o item não existir no cadastro."),
                        "Quantidade": st.column_config.NumberColumn("Qtd. *", min_value=0.0, step=1.0, format="%.0f"),
                        "Valor_Mensal_Unitario": st.column_config.NumberColumn("Valor mensal unit. *", min_value=0.0, step=100.0, format="R$ %.2f"),
                        "Observacao_Item": st.column_config.TextColumn("Observação do item"),
                    },
                    column_order=["Equipamento", "Equipamento_Novo", "Quantidade", "Valor_Mensal_Unitario", "Observacao_Item"],
                )
                st.caption("Use + para adicionar equipamentos. Se o item não existir, escolha a opção de novo e digite o nome na coluna seguinte.")
                competencia = ""
                produto = ""
                quantidade = 0.0
                valor_unitario = 0.0
                valor_mensal = 0.0
                valor_previsto = 0.0
            else:
                with b:
                    competencia = st.selectbox(
                        "Mês previsto",
                        [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)],
                        format_func=month_label_from_comp,
                    )
                    product_choices = sales_product_options + [NEW_PRODUCT_OPTION]
                    produto_selecionado = st.selectbox(
                        "Produto / linha / oportunidade", product_choices,
                        index=0 if sales_product_options else len(product_choices) - 1,
                        format_func=lambda value: PRODUCT_VALUE_TO_DISPLAY.get(value, value),
                        help="Use a busca acima para localizar por código, descrição, linha, grupo, fornecedor ou NCM.",
                    )
                    produto_novo = st.text_input("Novo produto / oportunidade", placeholder="Preencha somente se não existir no cadastro")
                    produto = resolve_catalog_choice(produto_selecionado, produto_novo, NEW_PRODUCT_OPTION)
                with c:
                    quantidade = st.number_input("Quantidade", min_value=0.0, value=1.0, step=1.0)
                    valor_unitario = st.number_input("Valor unitário", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
                    valor_previsto = st.number_input(
                        "Receita prevista",
                        min_value=0.0,
                        value=0.0,
                        step=1000.0,
                        format="%.2f",
                        help="Se ficar zerado, o sistema usa Quantidade × Valor unitário.",
                    )
                inicio_contrato = None
                prazo_contrato = 0
                numero_contrato = ""
                itens_locacao = pd.DataFrame(columns=CONTRACT_ITEM_COLUMNS)
                valor_mensal = 0.0

            d, e = st.columns([1, 2])
            with d:
                prob = st.selectbox("Probabilidade", list(PROBABILITY_WEIGHTS.keys()))
            with e:
                observacao = st.text_area("Observação", height=86)
            submitted = st.form_submit_button("Salvar forecast", width="stretch")

        if submitted:
            cliente_clean = resolve_catalog_choice(cliente_selecionado, novo_cliente, NEW_CLIENT_OPTION)
            peso = PROBABILITY_WEIGHTS[prob]
            contract_data = {
                "Data_Inicio_Contrato": "",
                "Prazo_Contrato_Meses": 0,
                "Data_Fim_Contrato": "",
                "Valor_Mensal_Contrato": 0.0,
                "Receita_Contrato_Total": 0.0,
                "Meses_No_Ano": 0,
            }

            item_metrics = {"valid": True, "error": "", "item_count": 0, "total_units": float(quantidade), "monthly_total": 0.0, "summary": produto.strip(), "json": ""}
            if new_revenue_type == "Locação":
                item_metrics = contract_items_metrics(itens_locacao)
                valor_mensal = float(item_metrics.get("monthly_total", 0.0)) if item_metrics.get("valid") else 0.0
                proj = rental_projection(inicio_contrato, prazo_contrato, valor_mensal)
                receita = float(proj["revenue_year"])
                competencia_final = str(proj["first_comp"])
                contract_data = {
                    "Numero_Contrato": numero_contrato.strip(),
                    "Itens_Contrato_JSON": str(item_metrics.get("json", "")),
                    "Data_Inicio_Contrato": pd.Timestamp(inicio_contrato).strftime("%Y-%m-%d"),
                    "Prazo_Contrato_Meses": int(prazo_contrato),
                    "Data_Fim_Contrato": pd.Timestamp(proj["end"]).strftime("%Y-%m-%d") if proj["end"] is not None else "",
                    "Valor_Mensal_Contrato": float(valor_mensal),
                    "Receita_Contrato_Total": float(proj["contract_total"]),
                    "Meses_No_Ano": int(proj["months_in_year"]),
                }
                produto = str(item_metrics.get("summary", ""))
                quantidade = float(item_metrics.get("total_units", 0.0))
                valor_unitario = 0.0
            else:
                contract_data["Numero_Contrato"] = ""
                contract_data["Itens_Contrato_JSON"] = ""
                receita = float(valor_previsto) if float(valor_previsto) > 0 else float(quantidade) * float(valor_unitario)
                competencia_final = competencia

            if not cliente_clean:
                st.error("Informe o cliente.")
            elif new_revenue_type == "Locação" and not item_metrics.get("valid"):
                st.error(str(item_metrics.get("error", "Revise os equipamentos do contrato.")))
            elif new_revenue_type == "Locação" and contract_data["Meses_No_Ano"] <= 0:
                st.error(f"A vigência informada não possui receita dentro de {APP_YEAR}.")
            elif receita <= 0:
                st.error("Informe um valor válido para a receita prevista.")
            else:
                fid = f"FC-{APP_YEAR}-{uuid.uuid4().hex[:8].upper()}"
                row = {
                    "ID": fid,
                    "Ano": APP_YEAR,
                    "Linha": new_line,
                    "Competencia": competencia_final,
                    "Cliente": cliente_clean,
                    "Tipo_Cliente": tipo_cliente,
                    "Tipo_Receita": new_revenue_type,
                    "Produto_Linha": produto.strip(),
                    "Quantidade": float(quantidade),
                    "Valor_Unitario": float(valor_unitario),
                    **contract_data,
                    "Receita_Prevista": receita,
                    "Probabilidade": prob,
                    "Peso_Probabilidade": peso,
                    "Receita_Ponderada": receita * peso,
                    "Observacao": observacao.strip(),
                    "Status": "ATIVO",
                    "Criado_Por": user["nome"],
                    "Criado_Em": now_text(),
                    "Atualizado_Por": user["nome"],
                    "Atualizado_Em": now_text(),
                }
                try:
                    commit_forecast("INCLUSÃO", user, fid, new_line, None, row)
                    if new_revenue_type == "Locação":
                        st.success(
                            f"Locação incluída com {item_metrics.get('item_count', 0)} item(ns). "
                            f"Mensalidade total: {brl(contract_data['Valor_Mensal_Contrato'])} · "
                            f"Forecast {APP_YEAR}: {brl(receita)} · {contract_data['Meses_No_Ano']} competência(s)."
                        )
                    else:
                        st.success("Forecast incluído com sucesso.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível salvar: {exc}")

    section("Lançamentos ativos")
    scoped = scope_df(active, scope_choice)
    scoped_monthly = scope_df(expand_monthly_forecast(active), scope_choice)
    f1, f2, f3 = st.columns(3)
    with f1:
        month_filter = st.selectbox(
            "Filtrar mês",
            ["Todos"] + [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)],
            format_func=lambda x: x if x == "Todos" else month_label_from_comp(x),
        )
    with f2:
        prob_filter = st.selectbox("Filtrar probabilidade", ["Todas"] + list(PROBABILITY_WEIGHTS.keys()))
    with f3:
        revenue_filter = st.selectbox("Filtrar tipo", ["Todos", "Venda", "Locação", "Serviço"])
    forecast_search = st.text_input(
        "🔎 Buscar nos lançamentos",
        key="forecast_list_smart_search",
        placeholder="Cliente, contrato, código, descrição, linha, grupo, equipamento, observação...",
        help="Também localiza lançamentos pela Linha/Grupo do produto mesmo quando esses campos não foram gravados diretamente no forecast.",
    )

    view = scoped.copy()
    if month_filter != "Todos":
        month_ids = scoped_monthly.loc[scoped_monthly["Competencia"].astype(str).eq(month_filter), "ID"].astype(str).unique().tolist()
        view = view[view["ID"].astype(str).isin(month_ids)]
    if prob_filter != "Todas":
        view = view[view["Probabilidade"].eq(prob_filter)]
    if revenue_filter != "Todos":
        view = view[view["Tipo_Receita"].eq(revenue_filter)]
    if forecast_search:
        view = filter_budget_search(view, forecast_search)

    if view.empty:
        st.info("Nenhum forecast encontrado para os filtros selecionados.")
    else:
        show = view[[
            "ID", "Linha", "Competencia", "Cliente", "Tipo_Cliente", "Tipo_Receita", "Produto_Linha", "Numero_Contrato",
            "Data_Inicio_Contrato", "Data_Fim_Contrato", "Prazo_Contrato_Meses", "Valor_Mensal_Contrato",
            "Receita_Prevista", "Probabilidade", "Receita_Ponderada", "Atualizado_Por", "Atualizado_Em"
        ]].copy()
        show["Qtd. itens"] = view.apply(contract_item_count, axis=1)
        show["Linha"] = show["Linha"].map(line_label)
        show["Mês / Vigência"] = show.apply(forecast_period_label, axis=1)
        show = show.drop(columns=["Competencia", "Data_Inicio_Contrato", "Data_Fim_Contrato", "Prazo_Contrato_Meses"])
        show = show.rename(columns={
            "Tipo_Cliente": "Tipo cliente", "Tipo_Receita": "Receita", "Numero_Contrato": "Contrato",
            "Produto_Linha": "Itens / Oportunidade", "Valor_Mensal_Contrato": "Valor mensal",
            "Receita_Prevista": f"Forecast {APP_YEAR}", "Receita_Ponderada": "Forecast Ponderado",
            "Atualizado_Por": "Atualizado por", "Atualizado_Em": "Atualizado em",
        })
        ordered = [
            "ID", "Linha", "Mês / Vigência", "Cliente", "Tipo cliente", "Receita", "Contrato", "Qtd. itens", "Itens / Oportunidade",
            "Valor mensal", f"Forecast {APP_YEAR}", "Probabilidade", "Forecast Ponderado", "Atualizado por", "Atualizado em"
        ]
        st.dataframe(
            show[ordered],
            width="stretch",
            hide_index=True,
            column_config={
                "Valor mensal": st.column_config.NumberColumn(format="R$ %.2f"),
                f"Forecast {APP_YEAR}": st.column_config.NumberColumn(format="R$ %.2f"),
                "Forecast Ponderado": st.column_config.NumberColumn(format="R$ %.2f"),
            },
        )

    editable_scope = scope_df(active, scope_choice)
    if can_edit and not editable_scope.empty:
        section("Alterar ou excluir lançamento")
        with st.expander("Editar forecast", expanded=False):
            ids = editable_scope["ID"].astype(str).tolist()
            edit_id = st.selectbox("Selecione o lançamento", ids, key="edit_forecast_id")
            current = editable_scope.loc[editable_scope["ID"].astype(str).eq(edit_id)].iloc[0].to_dict()
            rev_opts = ["Venda", "Locação", "Serviço"]
            current_rev = str(current.get("Tipo_Receita", "Venda"))
            e_tipo_receita = st.selectbox(
                "Tipo de receita",
                rev_opts,
                index=rev_opts.index(current_rev) if current_rev in rev_opts else 0,
                key=f"edit_revenue_type_{edit_id}",
            )
            es1, es2 = st.columns(2)
            with es1:
                edit_client_search = st.text_input(
                    "🔎 Buscar cliente para edição",
                    key=f"edit_client_search_{edit_id}",
                    placeholder="Nome, código, cidade, UF, vendedor, gerente...",
                )
                edit_client_matches = _search_records(CLIENT_RECORDS, edit_client_search, "value", limit=120)
                if not CLIENT_RECORDS:
                    edit_client_matches = filter_catalog_options(CLIENT_OPTIONS, edit_client_search)
            with es2:
                edit_product_search = st.text_input(
                    "🔎 Buscar equipamento / produto para edição",
                    key=f"edit_product_search_{edit_id}",
                    placeholder="Código, descrição, linha, grupo, fornecedor, NCM...",
                )
                edit_product_matches = _search_records(PRODUCT_RECORDS, edit_product_search, "value", limit=120)
                edit_product_display_matches = _search_records(PRODUCT_RECORDS, edit_product_search, "display", limit=120)
                if not PRODUCT_RECORDS:
                    edit_product_matches = filter_catalog_options(PRODUCT_OPTIONS, edit_product_search)
                    edit_product_display_matches = edit_product_matches

            with st.form(f"edit_form_{edit_id}"):
                a, b, c = st.columns(3)
                with a:
                    if can_edit_all:
                        line_idx = LINES.index(norm(current["Linha"])) if norm(current["Linha"]) in LINES else 0
                        e_line = st.selectbox("Linha", LINES, index=line_idx, format_func=line_label)
                    else:
                        e_line = user["linha"]
                        st.text_input("Linha", line_label(e_line), disabled=True)
                    current_client = str(current.get("Cliente", "") or "").strip()
                    edit_client_options = list(edit_client_matches)
                    if current_client and current_client not in edit_client_options:
                        edit_client_options.insert(0, current_client)
                    edit_client_options = list(dict.fromkeys(edit_client_options)) + [NEW_CLIENT_OPTION]
                    e_cliente_selecionado = st.selectbox(
                        "Cliente", edit_client_options,
                        index=edit_client_options.index(current_client) if current_client in edit_client_options else len(edit_client_options) - 1,
                        format_func=lambda value: CLIENT_VALUE_TO_DISPLAY.get(value, value),
                        help="Pesquise pelo cadastro existente ou escolha + Novo cliente.",
                    )
                    e_novo_cliente = st.text_input("Novo cliente", placeholder="Preencha somente se escolher + Novo cliente")
                    e_tipo_cliente = (CLIENT_TYPES.get(e_cliente_selecionado, str(current.get("Tipo_Cliente", "Novo") or "Novo"))
                                      if e_cliente_selecionado != NEW_CLIENT_OPTION else "Novo")
                    st.caption(f"Classificação: {e_tipo_cliente}")

                if e_tipo_receita == "Locação":
                    old_start = pd.to_datetime(current.get("Data_Inicio_Contrato"), errors="coerce")
                    if pd.isna(old_start):
                        try:
                            old_start = pd.Period(str(current.get("Competencia", f"{APP_YEAR}-01")), freq="M").start_time
                        except Exception:
                            old_start = pd.Timestamp(APP_YEAR, 1, 1)
                    old_term = int(float(current.get("Prazo_Contrato_Meses") or 0))
                    if old_term <= 0:
                        old_term = 1
                    with b:
                        e_inicio = st.date_input("Início do contrato", value=old_start.date(), min_value=date(APP_YEAR - 7, 1, 1), max_value=date(APP_YEAR, 12, 31), format="DD/MM/YYYY")
                        e_prazo = st.number_input("Prazo do contrato (meses)", min_value=1, max_value=120, value=old_term, step=1)
                    with c:
                        e_numero_contrato = st.text_input("Nº / referência do contrato", value=str(current.get("Numero_Contrato", "") or ""))
                        st.caption("Edite os itens abaixo. A mensalidade total é recalculada pela soma dos equipamentos.")

                    st.markdown("**Equipamentos do contrato**")
                    legacy_items = contract_items_from_row(current)
                    if legacy_items.empty:
                        legacy_items = pd.DataFrame([{
                            "Equipamento": "", "Quantidade": 1.0, "Valor_Mensal_Unitario": 0.0, "Observacao_Item": ""
                        }], columns=CONTRACT_ITEM_COLUMNS)
                    legacy_items = legacy_items.copy()
                    legacy_items["Equipamento"] = legacy_items["Equipamento"].map(lambda value: PRODUCT_VALUE_TO_DISPLAY.get(str(value), str(value)))
                    legacy_items["Equipamento_Novo"] = ""
                    extra_items = [str(x).strip() for x in legacy_items["Equipamento"].dropna().tolist() if str(x).strip()]
                    preserved_edit = _editor_selected_equipment_values(f"edit_rental_items_{edit_id}")
                    edit_product_options = []
                    seen_products = set()
                    for value in extra_items + preserved_edit + edit_product_display_matches:
                        key = norm(value)
                        if key and key not in seen_products:
                            seen_products.add(key)
                            edit_product_options.append(value)
                    edit_equipment_cfg = (
                        st.column_config.SelectboxColumn(
                            "Equipamento / produto *", options=[""] + edit_product_options + [NEW_PRODUCT_OPTION], required=True,
                            help="A lista respeita a busca inteligente por código, descrição, linha, grupo, fornecedor ou NCM.",
                        ) if edit_product_options else st.column_config.TextColumn("Equipamento / produto *", required=True)
                    )
                    e_items = st.data_editor(
                        legacy_items, num_rows="dynamic", hide_index=True, width="stretch", key=f"edit_rental_items_{edit_id}",
                        column_config={
                            "Equipamento": edit_equipment_cfg,
                            "Equipamento_Novo": st.column_config.TextColumn("Novo equipamento", help="Preencha somente quando o item não existir no cadastro."),
                            "Quantidade": st.column_config.NumberColumn("Qtd. *", min_value=0.0, step=1.0, format="%.0f"),
                            "Valor_Mensal_Unitario": st.column_config.NumberColumn("Valor mensal unit. *", min_value=0.0, step=100.0, format="R$ %.2f"),
                            "Observacao_Item": st.column_config.TextColumn("Observação do item"),
                        },
                        column_order=["Equipamento", "Equipamento_Novo", "Quantidade", "Valor_Mensal_Unitario", "Observacao_Item"],
                    )
                    st.caption("Use + para incluir outro equipamento. Se for um item novo, escolha a opção de novo e informe o nome na coluna seguinte.")
                    e_comp = ""
                    e_produto = ""
                    e_qtd = 0.0
                    e_unit = 0.0
                    e_monthly = 0.0
                    e_receita = 0.0
                else:
                    with b:
                        comps = [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]
                        current_comp = str(current.get("Competencia", f"{APP_YEAR}-01"))
                        e_comp = st.selectbox("Mês", comps, index=comps.index(current_comp) if current_comp in comps else 0, format_func=month_label_from_comp)
                        current_product = str(current.get("Produto_Linha", "") or "").strip()
                        edit_product_choices = list(edit_product_matches)
                        if current_product and current_product not in edit_product_choices:
                            edit_product_choices.insert(0, current_product)
                        edit_product_choices = list(dict.fromkeys(edit_product_choices)) + [NEW_PRODUCT_OPTION]
                        e_produto_selecionado = st.selectbox(
                            "Produto / linha / oportunidade", edit_product_choices,
                            index=edit_product_choices.index(current_product) if current_product in edit_product_choices else len(edit_product_choices) - 1,
                            format_func=lambda value: PRODUCT_VALUE_TO_DISPLAY.get(value, value),
                            help="Pesquise no cadastro por código, descrição, linha, grupo, fornecedor ou NCM.",
                        )
                        e_produto_novo = st.text_input("Novo produto / oportunidade", placeholder="Preencha somente se não existir no cadastro")
                        e_produto = resolve_catalog_choice(e_produto_selecionado, e_produto_novo, NEW_PRODUCT_OPTION)
                    with c:
                        e_qtd = st.number_input("Quantidade", min_value=0.0, value=float(current["Quantidade"] or 0), step=1.0)
                        e_unit = st.number_input("Valor unitário", min_value=0.0, value=float(current["Valor_Unitario"] or 0), step=1000.0, format="%.2f")
                        e_receita = st.number_input("Receita prevista", min_value=0.0, value=float(current["Receita_Prevista"] or 0), step=1000.0, format="%.2f")
                    e_inicio = None
                    e_prazo = 0
                    e_numero_contrato = ""
                    e_items = pd.DataFrame(columns=CONTRACT_ITEM_COLUMNS)
                    e_monthly = 0.0

                d, e = st.columns([1, 2])
                with d:
                    probs = list(PROBABILITY_WEIGHTS.keys())
                    e_prob = st.selectbox("Probabilidade", probs, index=probs.index(str(current["Probabilidade"])) if str(current["Probabilidade"]) in probs else 0)
                with e:
                    e_obs = st.text_area("Observação", value=str(current["Observacao"]), height=86)
                update_btn = st.form_submit_button("Salvar alterações", width="stretch")

            if update_btn:
                peso = PROBABILITY_WEIGHTS[e_prob]
                contract_updates = {
                    "Numero_Contrato": "", "Itens_Contrato_JSON": "",
                    "Data_Inicio_Contrato": "", "Prazo_Contrato_Meses": 0, "Data_Fim_Contrato": "",
                    "Valor_Mensal_Contrato": 0.0, "Receita_Contrato_Total": 0.0, "Meses_No_Ano": 0,
                }
                edit_item_metrics = {"valid": True, "error": "", "total_units": float(e_qtd), "summary": e_produto.strip(), "json": ""}
                if e_tipo_receita == "Locação":
                    edit_item_metrics = contract_items_metrics(e_items)
                    e_monthly = float(edit_item_metrics.get("monthly_total", 0.0)) if edit_item_metrics.get("valid") else 0.0
                    e_qtd = float(edit_item_metrics.get("total_units", 0.0)) if edit_item_metrics.get("valid") else 0.0
                    e_produto = str(edit_item_metrics.get("summary", "")) if edit_item_metrics.get("valid") else ""
                    e_unit = 0.0
                    proj = rental_projection(e_inicio, e_prazo, e_monthly)
                    receita_edit = float(proj["revenue_year"])
                    comp_edit = str(proj["first_comp"])
                    contract_updates = {
                        "Numero_Contrato": e_numero_contrato.strip(),
                        "Itens_Contrato_JSON": str(edit_item_metrics.get("json", "")),
                        "Data_Inicio_Contrato": pd.Timestamp(e_inicio).strftime("%Y-%m-%d"),
                        "Prazo_Contrato_Meses": int(e_prazo),
                        "Data_Fim_Contrato": pd.Timestamp(proj["end"]).strftime("%Y-%m-%d") if proj["end"] is not None else "",
                        "Valor_Mensal_Contrato": float(e_monthly),
                        "Receita_Contrato_Total": float(proj["contract_total"]),
                        "Meses_No_Ano": int(proj["months_in_year"]),
                    }
                else:
                    receita_edit = float(e_receita) if float(e_receita) > 0 else float(e_qtd) * float(e_unit)
                    comp_edit = e_comp

                e_cliente_final = resolve_catalog_choice(e_cliente_selecionado, e_novo_cliente, NEW_CLIENT_OPTION)
                if not e_cliente_final:
                    st.error("Informe o cliente.")
                elif e_tipo_receita == "Locação" and not edit_item_metrics.get("valid"):
                    st.error(str(edit_item_metrics.get("error", "Revise os equipamentos do contrato.")))
                elif e_tipo_receita == "Locação" and contract_updates["Meses_No_Ano"] <= 0:
                    st.error(f"A vigência informada não possui receita dentro de {APP_YEAR}.")
                elif receita_edit <= 0:
                    st.error("Informe um valor válido para a receita prevista.")
                else:
                    before = current.copy()
                    updates = {
                        "Linha": e_line, "Competencia": comp_edit, "Cliente": e_cliente_final,
                        "Tipo_Cliente": e_tipo_cliente, "Tipo_Receita": e_tipo_receita,
                        "Produto_Linha": e_produto.strip(), "Quantidade": float(e_qtd),
                        "Valor_Unitario": float(e_unit), **contract_updates,
                        "Receita_Prevista": receita_edit, "Probabilidade": e_prob,
                        "Peso_Probabilidade": peso, "Receita_Ponderada": receita_edit * peso,
                        "Observacao": e_obs.strip(), "Atualizado_Por": user["nome"], "Atualizado_Em": now_text(),
                    }
                    after = before.copy()
                    after.update(updates)
                    try:
                        commit_forecast("ALTERAÇÃO", user, edit_id, e_line, before, after)
                        st.success("Forecast alterado.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Não foi possível salvar: {exc}")

        with st.expander("Excluir forecast", expanded=False):
            del_id = st.selectbox("Lançamento para exclusão", editable_scope["ID"].astype(str).tolist(), key="delete_forecast_id")
            confirm = st.checkbox("Confirmo a exclusão deste lançamento")
            if st.button("Excluir lançamento", type="secondary", disabled=not confirm, width="stretch"):
                before = editable_scope.loc[editable_scope["ID"].astype(str).eq(del_id)].iloc[0].to_dict()
                after = before.copy()
                after["Status"] = "EXCLUIDO"
                after["Atualizado_Por"] = user["nome"]
                after["Atualizado_Em"] = now_text()
                try:
                    commit_forecast("EXCLUSÃO", user, del_id, str(before.get("Linha", "")), before, after)
                    st.success("Lançamento excluído e mantido no histórico.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível excluir: {exc}")


# =========================================================
# PÁGINA: CONSOLIDAÇÃO
# =========================================================
elif page == "Consolidação":
    hero("Consolidação do Forecast Comercial", "Esta tela consolida somente as novas receitas previstas. A visão Carteira + Forecast está em Receita 2027.")
    scoped_raw = scope_df(active, scope_choice)
    scoped_monthly = scope_df(expand_monthly_forecast(active), scope_choice)
    consolidation_search = st.text_input(
        "🔎 Buscar antes de consolidar",
        key="consolidation_smart_search",
        placeholder="Cliente, contrato, código, descrição, linha, grupo, equipamento...",
        help="A consolidação e a exportação passam a refletir somente os registros encontrados pela busca.",
    )
    if consolidation_search:
        scoped_raw = filter_budget_search(scoped_raw, consolidation_search)
        allowed_ids = set(scoped_raw["ID"].astype(str)) if not scoped_raw.empty else set()
        scoped_monthly = scoped_monthly[scoped_monthly["ID"].astype(str).isin(allowed_ids)].copy()

    if scoped_raw.empty:
        st.info("Ainda não há forecast para consolidar neste escopo.")
    else:
        resumo_receita = scoped_monthly.groupby("Linha", as_index=False).agg(
            Forecast_Bruto=("Receita_Prevista", "sum"),
            Forecast_Ponderado=("Receita_Ponderada", "sum"),
        )
        resumo_base = scoped_raw.groupby("Linha", as_index=False).agg(
            Clientes=("Cliente", "nunique"),
            Lancamentos=("ID", "nunique"),
        )
        resumo = resumo_receita.merge(resumo_base, on="Linha", how="outer").fillna(0)
        resumo["Cobertura"] = np.where(resumo["Forecast_Bruto"] != 0, (resumo["Forecast_Ponderado"] / resumo["Forecast_Bruto"]) * 100, 0)
        resumo["Linha"] = resumo["Linha"].map(line_label)

        section("Resumo anual por linha")
        st.dataframe(
            resumo,
            hide_index=True,
            width="stretch",
            column_config={
                "Forecast_Bruto": st.column_config.NumberColumn("Forecast bruto", format="R$ %.2f"),
                "Forecast_Ponderado": st.column_config.NumberColumn("Forecast ponderado", format="R$ %.2f"),
                "Cobertura": st.column_config.NumberColumn("Cobertura", format="%.1f%%"),
            },
        )

        section("Matriz mensal")
        matrix = scoped_monthly.pivot_table(index="Linha", columns="Competencia", values="Receita_Prevista", aggfunc="sum", fill_value=0)
        for comp in [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]:
            if comp not in matrix.columns:
                matrix[comp] = 0.0
        matrix = matrix[[f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]].reset_index()
        matrix["Linha"] = matrix["Linha"].map(line_label)
        matrix = matrix.rename(columns={f"{APP_YEAR}-{m:02d}": MONTHS[m] for m in range(1, 13)})
        matrix["Total"] = matrix[[MONTHS[m] for m in range(1, 13)]].sum(axis=1)
        st.dataframe(
            matrix,
            hide_index=True,
            width="stretch",
            column_config={col: st.column_config.NumberColumn(format="R$ %.2f") for col in [MONTHS[m] for m in range(1, 13)] + ["Total"]},
        )

        section("Exportação")
        scoped_history = history.copy()
        if not is_director and not scoped_history.empty:
            scoped_history = scoped_history[scoped_history["Linha"].astype(str).map(norm).eq(user["linha"])]
        xlsx = export_excel(scoped_raw, scoped_history)
        st.download_button(
            "Baixar consolidação em Excel",
            data=xlsx,
            file_name=f"First_Budget_Forecast_{APP_YEAR}_{norm(scope_choice).replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )


# =========================================================
# PÁGINA: HISTÓRICO
# =========================================================
elif page == "Histórico":
    hero("Histórico de Alterações", "Rastreabilidade de inclusões, alterações e exclusões do forecast.")
    h = history.copy()
    if not is_director and not h.empty:
        h = h[h["Linha"].astype(str).map(norm).eq(user["linha"])]
    elif is_director and scope_choice != "CONSOLIDADO" and not h.empty:
        h = h[h["Linha"].astype(str).map(norm).eq(scope_choice)]

    history_search = st.text_input(
        "🔎 Buscar no histórico",
        key="history_smart_search",
        placeholder="Usuário, ação, ID, cliente, contrato, produto, código, observação...",
        help="A busca inclui o conteúdo de Antes/Depois gravado em JSON.",
    )
    if history_search:
        h = filter_dataframe_search(h, history_search)

    if h.empty:
        st.info("Nenhuma alteração registrada até o momento.")
    else:
        h["_ordem"] = pd.to_datetime(h["Data_Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        h = h.sort_values("_ordem", ascending=False).drop(columns=["_ordem"])
        show = h[["Data_Hora", "Acao", "Usuario", "Forecast_ID", "Linha"]].copy()
        show["Linha"] = show["Linha"].map(line_label)
        show = show.rename(columns={"Data_Hora": "Data / hora", "Acao": "Ação", "Usuario": "Usuário", "Forecast_ID": "Forecast ID"})
        st.dataframe(show, width="stretch", hide_index=True)

        with st.expander("Auditoria detalhada", expanded=False):
            audit_id = st.selectbox("Registro", h["Historico_ID"].astype(str).tolist())
            audit = h.loc[h["Historico_ID"].astype(str).eq(audit_id)].iloc[0]
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Antes")
                try:
                    st.json(json.loads(str(audit["Antes_JSON"])))
                except Exception:
                    st.code(str(audit["Antes_JSON"]))
            with c2:
                st.caption("Depois")
                try:
                    st.json(json.loads(str(audit["Depois_JSON"])))
                except Exception:
                    st.code(str(audit["Depois_JSON"]))

    section("Histórico do Budget de Receita")
    hb = budget_revenue_history.copy()
    if not is_director and not hb.empty:
        hb = hb[hb["Linha"].astype(str).map(norm).eq(user["linha"])].copy()
    elif is_director and scope_choice != "CONSOLIDADO" and not hb.empty:
        hb = hb[hb["Linha"].astype(str).map(norm).eq(scope_choice)].copy()
    if hb.empty:
        st.caption("Ainda não há alterações gravadas no Budget de Receita.")
    else:
        hb["_ordem"] = pd.to_datetime(hb["Data_Hora"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
        hb = hb.sort_values("_ordem", ascending=False).drop(columns=["_ordem"])
        hb_show = hb[["Data_Hora", "Acao", "Usuario", "Linha"]].copy()
        hb_show["Linha"] = hb_show["Linha"].map(line_label)
        hb_show = hb_show.rename(columns={"Data_Hora": "Data / hora", "Acao": "Ação", "Usuario": "Usuário"})
        st.dataframe(hb_show, width="stretch", hide_index=True)


# =========================================================
# AVISO DE PERSISTÊNCIA PARA CONTROLADORIA
# =========================================================
if is_controladoria and storage_config()["mode"] != "github":
    st.markdown(
        """
        <div class='storage-note'>
        <b>Ambiente de desenvolvimento:</b> os dados estão sendo gravados localmente.
        Para uso simultâneo pelos gestores e persistência após reinicializações, configure o bloco
        <code>[budget_storage]</code> nos Secrets do Streamlit para gravar as bases no GitHub.
        </div>
        """,
        unsafe_allow_html=True,
    )
