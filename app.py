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

FORECAST_COLUMNS = [
    "ID", "Ano", "Linha", "Competencia", "Cliente", "Tipo_Cliente",
    "Tipo_Receita", "Produto_Linha", "Quantidade", "Valor_Unitario",
    "Data_Inicio_Contrato", "Prazo_Contrato_Meses", "Data_Fim_Contrato",
    "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Meses_No_Ano",
    "Receita_Prevista", "Probabilidade", "Peso_Probabilidade",
    "Receita_Ponderada", "Observacao", "Status", "Criado_Por",
    "Criado_Em", "Atualizado_Por", "Atualizado_Em",
]
HISTORY_COLUMNS = [
    "Historico_ID", "Forecast_ID", "Ano", "Linha", "Acao", "Usuario",
    "Data_Hora", "Antes_JSON", "Depois_JSON",
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
def export_excel(forecast: pd.DataFrame, history: pd.DataFrame) -> bytes:
    out = io.BytesIO()
    f = forecast.copy()
    if not f.empty:
        f["Competência"] = f["Competencia"].map(month_label_from_comp)
        f["Linha"] = f["Linha"].map(line_label)
        f["Início Contrato"] = f["Data_Inicio_Contrato"].map(date_br)
        f["Fim Contrato"] = f["Data_Fim_Contrato"].map(date_br)
        for col in ["Valor_Unitario", "Valor_Mensal_Contrato", "Receita_Contrato_Total", "Receita_Prevista", "Receita_Ponderada"]:
            f[col] = pd.to_numeric(f[col], errors="coerce").fillna(0)

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
        resumo_linha.to_excel(writer, index=False, sheet_name="Resumo Linha")
        resumo_mes.to_excel(writer, index=False, sheet_name="Resumo Mensal")
        history.to_excel(writer, index=False, sheet_name="Histórico")
        wb = writer.book
        header = wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY})
        money = wb.add_format({"num_format": 'R$ #,##0.00;[Red]-R$ #,##0.00'})
        frames = [("Forecast", f), ("Projeção Mensal", mensal_detalhe), ("Resumo Linha", resumo_linha), ("Resumo Mensal", resumo_mes), ("Histórico", history)]
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

    pages = ["Visão Geral", "Forecast Comercial", "Consolidação", "Histórico"]
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


# =========================================================
# PÁGINA: FORECAST COMERCIAL
# =========================================================
elif page == "Forecast Comercial":
    hero("Forecast Comercial 2027", "Venda e serviço são lançados por competência; locação é projetada automaticamente pelo prazo do contrato.")

    if can_edit:
        section("Novo lançamento")
        default_rev_idx = 1 if (not can_edit_all and user.get("linha") == "LOCACAO") else 0
        new_revenue_type = st.radio(
            "Tipo de receita",
            ["Venda", "Locação", "Serviço"],
            index=default_rev_idx,
            horizontal=True,
            key="new_revenue_type",
            help="Na locação, informe início, prazo e valor mensal. O sistema distribui a receita nas competências de 2027.",
        )

        with st.form("new_forecast_form", clear_on_submit=True):
            a, b, c = st.columns(3)
            with a:
                if can_edit_all:
                    new_line = st.selectbox("Linha de negócio", LINES, format_func=line_label)
                else:
                    new_line = user["linha"]
                    st.text_input("Linha de negócio", value=line_label(new_line), disabled=True)
                cliente = st.text_input("Cliente *")
                tipo_cliente = st.selectbox("Tipo de cliente", ["Atual", "Novo"])

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
                    produto = st.text_input("Equipamento / linha / oportunidade")
                with c:
                    valor_mensal = st.number_input("Valor mensal da locação", min_value=0.0, value=0.0, step=1000.0, format="%.2f")
                    quantidade = st.number_input("Quantidade de equipamentos", min_value=0.0, value=1.0, step=1.0)
                    st.caption("A receita de 2027 será calculada pelos meses de vigência que pertencem ao ano do orçamento.")
                competencia = ""
                valor_unitario = float(valor_mensal)
                valor_previsto = 0.0
            else:
                with b:
                    competencia = st.selectbox(
                        "Mês previsto",
                        [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)],
                        format_func=month_label_from_comp,
                    )
                    produto = st.text_input("Produto / linha / oportunidade")
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
                valor_mensal = 0.0

            d, e = st.columns([1, 2])
            with d:
                prob = st.selectbox("Probabilidade", list(PROBABILITY_WEIGHTS.keys()))
            with e:
                observacao = st.text_area("Observação", height=86)
            submitted = st.form_submit_button("Salvar forecast", width="stretch")

        if submitted:
            cliente_clean = cliente.strip()
            peso = PROBABILITY_WEIGHTS[prob]
            contract_data = {
                "Data_Inicio_Contrato": "",
                "Prazo_Contrato_Meses": 0,
                "Data_Fim_Contrato": "",
                "Valor_Mensal_Contrato": 0.0,
                "Receita_Contrato_Total": 0.0,
                "Meses_No_Ano": 0,
            }

            if new_revenue_type == "Locação":
                proj = rental_projection(inicio_contrato, prazo_contrato, valor_mensal)
                receita = float(proj["revenue_year"])
                competencia_final = str(proj["first_comp"])
                contract_data = {
                    "Data_Inicio_Contrato": pd.Timestamp(inicio_contrato).strftime("%Y-%m-%d"),
                    "Prazo_Contrato_Meses": int(prazo_contrato),
                    "Data_Fim_Contrato": pd.Timestamp(proj["end"]).strftime("%Y-%m-%d") if proj["end"] is not None else "",
                    "Valor_Mensal_Contrato": float(valor_mensal),
                    "Receita_Contrato_Total": float(proj["contract_total"]),
                    "Meses_No_Ano": int(proj["months_in_year"]),
                }
            else:
                receita = float(valor_previsto) if float(valor_previsto) > 0 else float(quantidade) * float(valor_unitario)
                competencia_final = competencia

            if not cliente_clean:
                st.error("Informe o cliente.")
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
                            f"Locação incluída. Receita projetada em {APP_YEAR}: {brl(receita)} · "
                            f"{contract_data['Meses_No_Ano']} competência(s)."
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
            "ID", "Linha", "Competencia", "Cliente", "Tipo_Cliente", "Tipo_Receita", "Produto_Linha",
            "Data_Inicio_Contrato", "Data_Fim_Contrato", "Prazo_Contrato_Meses", "Valor_Mensal_Contrato",
            "Receita_Prevista", "Probabilidade", "Receita_Ponderada", "Atualizado_Por", "Atualizado_Em"
        ]].copy()
        show["Linha"] = show["Linha"].map(line_label)
        show["Mês / Vigência"] = show.apply(forecast_period_label, axis=1)
        show = show.drop(columns=["Competencia", "Data_Inicio_Contrato", "Data_Fim_Contrato", "Prazo_Contrato_Meses"])
        show = show.rename(columns={
            "Tipo_Cliente": "Tipo cliente", "Tipo_Receita": "Receita",
            "Produto_Linha": "Produto / Oportunidade", "Valor_Mensal_Contrato": "Valor mensal",
            "Receita_Prevista": f"Forecast {APP_YEAR}", "Receita_Ponderada": "Forecast Ponderado",
            "Atualizado_Por": "Atualizado por", "Atualizado_Em": "Atualizado em",
        })
        ordered = [
            "ID", "Linha", "Mês / Vigência", "Cliente", "Tipo cliente", "Receita", "Produto / Oportunidade",
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
                    e_cliente = st.text_input("Cliente", value=str(current["Cliente"]))
                    e_tipo_cliente = st.selectbox("Tipo de cliente", ["Atual", "Novo"], index=0 if str(current["Tipo_Cliente"]) != "Novo" else 1)

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
                    old_monthly = float(current.get("Valor_Mensal_Contrato") or 0)
                    if old_monthly <= 0:
                        old_monthly = float(current.get("Receita_Prevista") or 0)
                    with b:
                        e_inicio = st.date_input("Início do contrato", value=old_start.date(), min_value=date(APP_YEAR - 7, 1, 1), max_value=date(APP_YEAR, 12, 31), format="DD/MM/YYYY")
                        e_prazo = st.number_input("Prazo do contrato (meses)", min_value=1, max_value=120, value=old_term, step=1)
                        e_produto = st.text_input("Equipamento / linha / oportunidade", value=str(current["Produto_Linha"]))
                    with c:
                        e_monthly = st.number_input("Valor mensal da locação", min_value=0.0, value=old_monthly, step=1000.0, format="%.2f")
                        e_qtd = st.number_input("Quantidade de equipamentos", min_value=0.0, value=float(current["Quantidade"] or 0), step=1.0)
                        st.caption("A alteração recalcula automaticamente todas as competências de 2027 cobertas pelo contrato.")
                    e_comp = ""
                    e_unit = e_monthly
                    e_receita = 0.0
                else:
                    with b:
                        comps = [f"{APP_YEAR}-{m:02d}" for m in range(1, 13)]
                        current_comp = str(current.get("Competencia", f"{APP_YEAR}-01"))
                        e_comp = st.selectbox("Mês", comps, index=comps.index(current_comp) if current_comp in comps else 0, format_func=month_label_from_comp)
                        e_produto = st.text_input("Produto / linha / oportunidade", value=str(current["Produto_Linha"]))
                    with c:
                        e_qtd = st.number_input("Quantidade", min_value=0.0, value=float(current["Quantidade"] or 0), step=1.0)
                        e_unit = st.number_input("Valor unitário", min_value=0.0, value=float(current["Valor_Unitario"] or 0), step=1000.0, format="%.2f")
                        e_receita = st.number_input("Receita prevista", min_value=0.0, value=float(current["Receita_Prevista"] or 0), step=1000.0, format="%.2f")
                    e_inicio = None
                    e_prazo = 0
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
                    "Data_Inicio_Contrato": "", "Prazo_Contrato_Meses": 0, "Data_Fim_Contrato": "",
                    "Valor_Mensal_Contrato": 0.0, "Receita_Contrato_Total": 0.0, "Meses_No_Ano": 0,
                }
                if e_tipo_receita == "Locação":
                    proj = rental_projection(e_inicio, e_prazo, e_monthly)
                    receita_edit = float(proj["revenue_year"])
                    comp_edit = str(proj["first_comp"])
                    contract_updates = {
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

                if not e_cliente.strip():
                    st.error("Informe o cliente.")
                elif e_tipo_receita == "Locação" and contract_updates["Meses_No_Ano"] <= 0:
                    st.error(f"A vigência informada não possui receita dentro de {APP_YEAR}.")
                elif receita_edit <= 0:
                    st.error("Informe um valor válido para a receita prevista.")
                else:
                    before = current.copy()
                    updates = {
                        "Linha": e_line, "Competencia": comp_edit, "Cliente": e_cliente.strip(),
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
