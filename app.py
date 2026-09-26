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


@st.cache_data(show_spinner=False, ttl=300)
def _read_master_catalog(path_text: str, modified_ns: int) -> dict[str, object]:
    """Lê somente clientes e produtos da BASE BI para agilizar os lançamentos."""
    path = Path(path_text)
    try:
        book = pd.ExcelFile(path, engine="openpyxl")
        if "BANCO DE DADOS FATURAMENTO" not in book.sheet_names:
            return {"clients": [], "products": [], "source": path.name, "warning": "A aba BANCO DE DADOS FATURAMENTO não foi localizada."}
        df = pd.read_excel(path, sheet_name="BANCO DE DADOS FATURAMENTO", engine="openpyxl")
    except Exception as exc:
        return {"clients": [], "products": [], "source": path.name, "warning": f"Não foi possível ler a BASE BI: {exc}"}

    client_col = _optional_col(df, ["NOME DO CLIENTE", "CLIENTE", "RAZÃO SOCIAL", "RAZAO SOCIAL"])
    product_col = _optional_col(df, ["PRODUTO", "ITEM", "CÓDIGO PRODUTO", "CODIGO PRODUTO"])
    desc_col = _optional_col(df, ["DESCRIÇÃO", "DESCRICAO", "LINHA DE PRODUTO"])

    clients = []
    if client_col:
        clients = sorted({
            str(value).strip() for value in df[client_col].dropna().tolist()
            if str(value).strip() and norm(value) not in {"NAO INFORMADO", "NAN", "NONE"}
        }, key=lambda x: norm(x))

    products = []
    if product_col or desc_col:
        codes = df[product_col].fillna("").astype(str).str.strip() if product_col else pd.Series("", index=df.index)
        descs = df[desc_col].fillna("").astype(str).str.strip() if desc_col else pd.Series("", index=df.index)
        labels = []
        for code, desc in zip(codes, descs):
            if norm(code) in {"NAN", "NONE", "NAO INFORMADO"}:
                code = ""
            if norm(desc) in {"NAN", "NONE", "NAO INFORMADO"}:
                desc = ""
            label = f"{code} | {desc}" if code and desc and norm(code) != norm(desc) else (code or desc)
            if label:
                labels.append(label)
        products = sorted(set(labels), key=lambda x: norm(x))

    return {"clients": clients, "products": products, "source": path.name, "warning": ""}


def build_input_catalog(forecast_df: pd.DataFrame) -> dict[str, object]:
    """Combina cadastro mestre da BASE BI com nomes já utilizados no First Budget."""
    path = _master_base_path()
    master = {"clients": [], "products": [], "source": "", "warning": "BASE BI não localizada no repositório do Budget."}
    if path is not None:
        master = _read_master_catalog(str(path), path.stat().st_mtime_ns)

    master_clients = list(master.get("clients", []))
    master_products = list(master.get("products", []))
    forecast_clients = []
    forecast_products = []
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
        out = {}
        for value in values:
            label = str(value).strip()
            key = norm(label)
            if label and key and key not in out:
                out[key] = label
        return sorted(out.values(), key=lambda x: norm(x))

    clients = unique_labels(master_clients + forecast_clients)
    products = unique_labels(master_products + forecast_products)
    master_keys = {norm(x) for x in master_clients}
    client_types = {name: ("Atual" if norm(name) in master_keys else "Novo") for name in clients}
    return {
        "clients": clients, "products": products, "client_types": client_types,
        "master_client_count": len(master_clients), "master_product_count": len(master_products),
        "source": str(master.get("source", "")), "warning": str(master.get("warning", "")),
    }


def resolve_catalog_choice(selected: str, manual: str, new_option: str) -> str:
    return str(manual or "").strip() if selected == new_option else str(selected or "").strip()


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
        "Data_Inicio": col(["INICIO", "INÍCIO"]),
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


def build_active_contracts_budget() -> tuple[pd.DataFrame, dict[str, object]]:
    """Combina a planilha operacional com as decisões de planejamento para 2027."""
    source = active_contracts_source()
    base = source.get("data", pd.DataFrame()).copy()
    if base.empty:
        return base, source
    overrides = load_active_contract_overrides()
    if not overrides.empty:
        base = base.merge(overrides, on="Contrato_Key", how="left")
    else:
        for col in ACTIVE_CONTRACT_OVERRIDE_COLUMNS:
            if col != "Contrato_Key":
                base[col] = np.nan

    base["Status_2027"] = base["Status_2027"].fillna("").astype(str).replace("", "REVISAR")
    base["Linha_Budget"] = base["Linha_Budget"].fillna("").astype(str)
    base.loc[base["Linha_Budget"].eq(""), "Linha_Budget"] = base.loc[base["Linha_Budget"].eq(""), "Linha_Sugerida"]
    default_months = np.where(base["Valor_Mensal_Base"].gt(0), 12.0, 0.0)
    base["Meses_2027"] = pd.to_numeric(base["Meses_2027"], errors="coerce")
    base["Meses_2027"] = base["Meses_2027"].where(base["Meses_2027"].notna(), default_months).clip(0, 12)
    base["Valor_Mensal_Ajustado"] = pd.to_numeric(base["Valor_Mensal_Ajustado"], errors="coerce")
    base["Valor_Mensal_Ajustado"] = base["Valor_Mensal_Ajustado"].where(base["Valor_Mensal_Ajustado"].notna(), base["Valor_Mensal_Base"])
    base["Observacao_2027"] = base["Observacao_2027"].fillna("").astype(str)
    base["Receita_2027_Preliminar"] = base["Valor_Mensal_Base"] * np.where(base["Valor_Mensal_Base"].gt(0), 12, 0)
    base["Receita_2027_Planejada"] = base["Valor_Mensal_Ajustado"] * base["Meses_2027"]
    base.loc[base["Status_2027"].map(norm).eq("NAO CONSIDERAR"), "Receita_2027_Planejada"] = 0.0
    base["Validado"] = ~base["Status_2027"].map(norm).eq("REVISAR")
    base["Receita_2027_Validada"] = np.where(base["Validado"], base["Receita_2027_Planejada"], 0.0)
    return base, source


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


def load_table(name: str, columns: list[str]) -> pd.DataFrame:
    cfg = storage_config()
    raw: bytes | None = None
    try:
        if cfg["mode"] == "github":
            raw = github_read_bytes(name)
        else:
            path = LOCAL_DATA_DIR / name
            raw = path.read_bytes() if path.exists() else None
    except Exception as exc:
        st.warning(f"Falha ao ler a base de planejamento: {exc}")

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


def forecast_file() -> str:
    return f"forecast_comercial_{APP_YEAR}.csv"


def history_file() -> str:
    return f"historico_forecast_{APP_YEAR}.csv"


def load_forecast() -> pd.DataFrame:
    df = load_table(forecast_file(), FORECAST_COLUMNS)
    numeric = [
        "Ano", "Quantidade", "Valor_Unitario", "Prazo_Contrato_Meses",
        "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Meses_No_Ano",
        "Receita_Prevista", "Peso_Probabilidade", "Receita_Ponderada",
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df


def load_history() -> pd.DataFrame:
    return load_table(history_file(), HISTORY_COLUMNS)


def append_history(action: str, user: dict, forecast_id: str, line: str, before: dict | None, after: dict | None) -> None:
    hist = load_history()
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
    latest = load_forecast()

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

    pages = ["Visão Geral", "Carteira Ativa", "Forecast Comercial", "Consolidação", "Histórico"]
    page = st.radio("Navegação", pages, label_visibility="collapsed")

    cfg = storage_config()
    st.divider()
    if cfg["mode"] == "github":
        st.caption("Persistência: GitHub ✓")
    else:
        st.caption("Persistência: Local · desenvolvimento")


# =========================================================
# DADOS
# =========================================================
forecast = load_forecast()
history = load_history()
active = forecast[forecast["Status"].astype(str).str.upper().eq("ATIVO")].copy() if not forecast.empty else forecast.copy()
input_catalog = build_input_catalog(forecast)
CLIENT_OPTIONS = list(input_catalog.get("clients", []))
PRODUCT_OPTIONS = list(input_catalog.get("products", []))
CLIENT_TYPES = dict(input_catalog.get("client_types", {}))
active_contracts, active_contracts_meta = build_active_contracts_budget()
if not active_contracts.empty:
    contract_clients = [str(x).strip() for x in active_contracts["Cliente"].dropna().tolist() if str(x).strip()]
    contract_products = [str(x).strip() for x in active_contracts["Linha_Produto"].dropna().tolist() if str(x).strip()]
    CLIENT_OPTIONS = sorted({*CLIENT_OPTIONS, *contract_clients}, key=lambda x: norm(x))
    PRODUCT_OPTIONS = sorted({*PRODUCT_OPTIONS, *contract_products}, key=lambda x: norm(x))
    master_client_keys = {norm(x) for x in contract_clients}
    for name in CLIENT_OPTIONS:
        if norm(name) in master_client_keys:
            CLIENT_TYPES[name] = "Atual"
active_scope = scope_df(active, scope_choice)
active_monthly = expand_monthly_forecast(active)
active_monthly_scope = scope_df(active_monthly, scope_choice)


# =========================================================
# PÁGINA: VISÃO GERAL
# =========================================================
if page == "Visão Geral":
    hero("First Budget 2027", "Forecast comercial como ponto de partida do orçamento anual.")

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
    if carteira_scope.empty:
        st.info("A planilha de contratos ativos ainda não foi localizada no repositório do Budget.")
    else:
        validada = float(carteira_scope["Receita_2027_Validada"].sum())
        preliminar = float(carteira_scope["Receita_2027_Preliminar"].sum())
        pendentes = int((carteira_scope["Status_2027"].astype(str).map(norm) == "REVISAR").sum())
        sem_valor = int(carteira_scope["Valor_Mensal_Base"].le(0).sum())
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            kpi("Carteira validada", brl(validada), f"Receita base {APP_YEAR} revisada")
        with a2:
            kpi("Run-rate preliminar", brl(preliminar), "Valor mensal atual × 12 · antes da revisão")
        with a3:
            kpi("Contratos pendentes", f"{pendentes}", "Precisam validar meses/renovação")
        with a4:
            kpi("Sem valor mensal", f"{sem_valor}", "Não entram na receita até ajuste")
        if pendentes:
            st.caption("A carteira só entra como receita contratada validada após a revisão dos contratos. O arquivo fonte não possui data de término/vigência contratual.")


# =========================================================
# PÁGINA: CARTEIRA ATIVA
# =========================================================
elif page == "Carteira Ativa":
    hero("Carteira Ativa 2027", "Contratos existentes formam a base da receita; o forecast comercial deve registrar somente expansão, renovação e novos negócios.")

    source_name = str(active_contracts_meta.get("source", "") or "")
    warning = str(active_contracts_meta.get("warning", "") or "")
    if source_name:
        st.caption(f"Fonte operacional: {source_name}")
    if warning:
        st.warning(warning)

    carteira_scope = scope_active_contracts(active_contracts, scope_choice)
    if carteira_scope.empty:
        st.info("Inclua a planilha de contratos ativos no mesmo repositório do app para carregar a carteira automaticamente.")
    else:
        monthly_runrate = float(carteira_scope["Valor_Mensal_Base"].sum())
        preliminar = float(carteira_scope["Receita_2027_Preliminar"].sum())
        validada = float(carteira_scope["Receita_2027_Validada"].sum())
        pendentes = int((carteira_scope["Status_2027"].astype(str).map(norm) == "REVISAR").sum())
        sem_valor = int(carteira_scope["Valor_Mensal_Base"].le(0).sum())

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            kpi("Contratos / linhas", f"{len(carteira_scope)}", "Registros da carteira vigente")
        with c2:
            kpi("Faturamento mensal", brl(monthly_runrate), "Somatório dos valores mensais informados")
        with c3:
            kpi("Run-rate 2027", brl(preliminar), "Hipótese inicial: 12 meses")
        with c4:
            kpi("Base validada", brl(validada), "Somente contratos revisados")
        with c5:
            kpi("Pendentes", f"{pendentes}", f"{sem_valor} sem valor mensal")

        st.markdown(
            "<div class='storage-note'><b>Importante:</b> esta planilha informa início e valor de faturamento, mas não traz uma data de término/vigência do contrato. Por isso, o sistema usa 12 meses apenas como <b>run-rate preliminar</b>. A receita oficial do Budget deve usar a coluna <b>Base validada</b>, após informar quantos meses o contrato permanecerá em 2027.</div>",
            unsafe_allow_html=True,
        )

        section("Revisão da carteira para 2027")
        if is_controladoria:
            selector = carteira_scope.copy()
            selector["_label"] = selector.apply(
                lambda r: f"{str(r.get('Numero_Contrato','')).strip() or 'Sem nº'} · {str(r.get('Cliente','')).strip()} · {str(r.get('Linha_Produto','')).strip() or str(r.get('Gerente','')).strip()} · {brl(r.get('Valor_Mensal_Base',0))}/mês",
                axis=1,
            )
            labels = selector["_label"].tolist()
            selected_label = st.selectbox("Contrato / linha para revisar", labels)
            selected_row = selector.loc[selector["_label"].eq(selected_label)].iloc[0]
            current_status = str(selected_row.get("Status_2027", "REVISAR"))
            status_index = ACTIVE_CONTRACT_STATUS.index(current_status) if current_status in ACTIVE_CONTRACT_STATUS else 0
            current_line = norm(selected_row.get("Linha_Budget", selected_row.get("Linha_Sugerida", "LOCACAO")))
            line_index = LINES.index(current_line) if current_line in LINES else LINES.index("LOCACAO")
            with st.form("active_contract_review_form"):
                r1, r2, r3, r4 = st.columns([1.25, .85, 1, 1])
                with r1:
                    status_2027 = st.selectbox("Tratamento 2027", ACTIVE_CONTRACT_STATUS, index=status_index)
                with r2:
                    meses_2027 = st.number_input("Meses em 2027", min_value=0, max_value=12, value=int(float(selected_row.get("Meses_2027", 12) or 0)), step=1)
                with r3:
                    valor_mensal_ajustado = st.number_input(
                        "Valor mensal 2027", min_value=0.0,
                        value=float(selected_row.get("Valor_Mensal_Ajustado", 0) or 0), step=100.0, format="%.2f",
                    )
                with r4:
                    linha_budget = st.selectbox("Linha Budget", LINES, index=line_index, format_func=line_label)
                obs_2027 = st.text_area("Observação / renovação / encerramento previsto", value=str(selected_row.get("Observacao_2027", "") or ""), height=80)
                save_review = st.form_submit_button("Salvar revisão da carteira", width="stretch")
            if save_review:
                try:
                    save_active_contract_override(user, selected_row, status_2027, int(meses_2027), float(valor_mensal_ajustado), linha_budget, obs_2027)
                    st.success("Contrato revisado para o Budget 2027.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Não foi possível salvar a revisão: {exc}")
        else:
            st.caption("A revisão da carteira é feita pela Controladoria. Seu perfil visualiza os contratos da respectiva linha.")

        section("Contratos existentes")
        view = carteira_scope.copy()
        view["Contrato"] = view["Numero_Contrato"].fillna("").astype(str)
        view["Cliente"] = view["Cliente"].fillna("").astype(str)
        view["Início"] = view["Data_Inicio"].map(date_br)
        view["Linha"] = view["Linha_Budget"].map(line_label)
        view["Valor mensal"] = view["Valor_Mensal_Ajustado"]
        view["Receita 2027"] = view["Receita_2027_Planejada"]
        view["Status"] = view["Status_2027"]
        view["Meses"] = view["Meses_2027"].astype(int)
        view["Produto / linha"] = view["Linha_Produto"].fillna("").astype(str)
        view["Qtd. eq."] = view["Qtd_Equipamentos"]
        display_cols = ["Contrato", "Cliente", "Linha", "Produto / linha", "Início", "Valor mensal", "Meses", "Receita 2027", "Status", "Qtd. eq."]
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

        with st.form("new_forecast_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            with a:
                if can_edit_all:
                    new_line = st.selectbox("Linha de negócio", LINES, format_func=line_label)
                else:
                    new_line = user["linha"]
                    st.text_input("Linha de negócio", value=line_label(new_line), disabled=True)
                client_choices = CLIENT_OPTIONS + [NEW_CLIENT_OPTION]
                cliente_selecionado = st.selectbox(
                    "Cliente *", client_choices,
                    index=0 if CLIENT_OPTIONS else len(client_choices) - 1,
                    help="Digite parte do nome para pesquisar. A lista usa a BASE BI e clientes já registrados no Budget.",
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
                equipment_cfg = (
                    st.column_config.SelectboxColumn(
                        "Equipamento / produto *", options=[""] + PRODUCT_OPTIONS + [NEW_PRODUCT_OPTION], required=True,
                        help="Pesquise no cadastro ou escolha + Novo equipamento / produto / oportunidade.",
                    ) if PRODUCT_OPTIONS else st.column_config.TextColumn("Equipamento / produto *", required=True)
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
                    product_choices = PRODUCT_OPTIONS + [NEW_PRODUCT_OPTION]
                    produto_selecionado = st.selectbox(
                        "Produto / linha / oportunidade", product_choices,
                        index=0 if PRODUCT_OPTIONS else len(product_choices) - 1,
                        help="Digite parte do código ou descrição para pesquisar no cadastro existente.",
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

    view = scoped.copy()
    if month_filter != "Todos":
        month_ids = scoped_monthly.loc[scoped_monthly["Competencia"].astype(str).eq(month_filter), "ID"].astype(str).unique().tolist()
        view = view[view["ID"].astype(str).isin(month_ids)]
    if prob_filter != "Todas":
        view = view[view["Probabilidade"].eq(prob_filter)]
    if revenue_filter != "Todos":
        view = view[view["Tipo_Receita"].eq(revenue_filter)]

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
                    edit_client_options = list(CLIENT_OPTIONS)
                    if current_client and current_client not in edit_client_options:
                        edit_client_options.append(current_client)
                    edit_client_options = sorted(edit_client_options, key=lambda x: norm(x)) + [NEW_CLIENT_OPTION]
                    e_cliente_selecionado = st.selectbox(
                        "Cliente", edit_client_options,
                        index=edit_client_options.index(current_client) if current_client in edit_client_options else len(edit_client_options) - 1,
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
                    legacy_items["Equipamento_Novo"] = ""
                    extra_items = [str(x).strip() for x in legacy_items["Equipamento"].dropna().tolist() if str(x).strip()]
                    edit_product_options = []
                    seen_products = set()
                    for value in PRODUCT_OPTIONS + extra_items:
                        key = norm(value)
                        if key and key not in seen_products:
                            seen_products.add(key)
                            edit_product_options.append(value)
                    edit_equipment_cfg = (
                        st.column_config.SelectboxColumn(
                            "Equipamento / produto *", options=[""] + edit_product_options + [NEW_PRODUCT_OPTION], required=True,
                            help="Pesquise no cadastro ou escolha + Novo equipamento / produto / oportunidade.",
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
                        edit_product_choices = list(PRODUCT_OPTIONS)
                        if current_product and current_product not in edit_product_choices:
                            edit_product_choices.append(current_product)
                        edit_product_choices = sorted(edit_product_choices, key=lambda x: norm(x)) + [NEW_PRODUCT_OPTION]
                        e_produto_selecionado = st.selectbox(
                            "Produto / linha / oportunidade", edit_product_choices,
                            index=edit_product_choices.index(current_product) if current_product in edit_product_choices else len(edit_product_choices) - 1,
                            help="Pesquise no cadastro existente ou escolha a opção de novo.",
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
    hero("Consolidação do Forecast", "A locação é distribuída mês a mês conforme a vigência; venda e serviço permanecem na competência informada.")
    scoped_raw = scope_df(active, scope_choice)
    scoped_monthly = scope_df(expand_monthly_forecast(active), scope_choice)

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
