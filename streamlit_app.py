"""
Streamlit app for SMILES degradation pathway visualization.
"""

import base64
import re
from pathlib import Path
from typing import Dict, Optional, Tuple

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "index.html"
RDKit_JS = "rdkit_minimal.js"
RDKit_WASM = "RDKit_minimal.wasm"
RDKit_ASSETS = (
    (RDKit_JS, "application/javascript"),
    (RDKit_WASM, "application/wasm"),
)

st.set_page_config(
    page_title="SMILES Degradation Pathway",
    page_icon=":test_tube:",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {padding: 0 !important; background: #fefefe;}
        [data-testid="stSidebar"] {display: none;}
        .block-container {padding: 0 !important; max-width: 100% !important;}
        .st-emotion-cache-1wrcr25,
        .st-emotion-cache-1dp5vir,
        .st-emotion-cache-13ln4jf {padding: 0 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _strip_inline_rdkit_bootstrap(content: str) -> str:
    """Remove the inline rdkit wasm hook so that we can inject our own loader."""
    pattern = (
        r"<script>\s*\(function\(\)\s*{[\s\S]*?window\.__rdkitLocalWasm\s*="
        r"\s*\"__rdkit_inline_wasm__\";\s*}\)\(\);\s*</script>\s*"
    )
    return re.sub(pattern, "", content, count=1)


def _encode_data_uri(file_path: Path, mime: str) -> Optional[str]:
    if not file_path.exists():
        return None
    with open(file_path, "rb") as file:
        data = base64.b64encode(file.read()).decode("ascii")
    return f"data:{mime};base64,{data}"


@st.cache_resource(show_spinner=False)
def preload_rdkit_assets() -> Dict[str, str]:
    """Load the rdkit assets once per process to accelerate future renders."""
    assets: Dict[str, str] = {}
    for filename, mime in RDKit_ASSETS:
        file_path = BASE_DIR / filename
        data_uri = _encode_data_uri(file_path, mime)
        if data_uri:
            assets[filename] = data_uri
    return assets


def _inline_rdkit_assets(
    content: str, assets: Dict[str, str]
) -> Tuple[str, Optional[str]]:
    js_uri = assets.get(RDKit_JS)
    wasm_uri = assets.get(RDKit_WASM)

    if js_uri:
        content = content.replace(f'src="{RDKit_JS}"', f'src="{js_uri}"')
        content = content.replace(
            f'const RDKIT_LOCAL_JS = "{RDKit_JS}";',
            f'const RDKIT_LOCAL_JS = "{js_uri}";',
        )

    if wasm_uri:
        content = content.replace(f'href="{RDKit_WASM}"', f'href="{wasm_uri}"')
        content = content.replace(
            f'const RDKIT_LOCAL_WASM = "{RDKit_WASM}";',
            f'const RDKIT_LOCAL_WASM = "{wasm_uri}";',
        )
        fetch_old = (
            "async function fetchWasm(url) {\r\n"
            "      const response = await fetch(url);\r\n"
            "      if (!response.ok) {\r\n"
            "        throw new Error(`Failed to fetch wasm: ${response.status}`);\r\n"
            "      }\r\n"
            "      const buffer = await response.arrayBuffer();\r\n"
            "      return new Uint8Array(buffer);\r\n"
            "    }"
        )
        fetch_new = (
            "async function fetchWasm(url) {\r\n"
            "      if (window.__rdkitPreloadedWasm) {\r\n"
            "        return window.__rdkitPreloadedWasm;\r\n"
            "      }\r\n"
            "      if (url.startsWith(\"data:\")) {\r\n"
            "        const base64 = url.split(\",\")[1];\r\n"
            "        const binaryString = atob(base64);\r\n"
            "        const bytes = new Uint8Array(binaryString.length);\r\n"
            "        for (let i = 0; i < binaryString.length; i++) {\r\n"
            "          bytes[i] = binaryString.charCodeAt(i);\r\n"
            "        }\r\n"
            "        window.__rdkitPreloadedWasm = bytes;\r\n"
            "        return bytes;\r\n"
            "      }\r\n"
            "      const response = await fetch(url);\r\n"
            "      if (!response.ok) {\r\n"
            "        throw new Error(`Failed to fetch wasm: ${response.status}`);\r\n"
            "      }\r\n"
            "      const buffer = await response.arrayBuffer();\r\n"
            "      const bytes = new Uint8Array(buffer);\r\n"
            "      window.__rdkitPreloadedWasm = bytes;\r\n"
            "      return bytes;\r\n"
            "    }"
        )
        content = content.replace(fetch_old, fetch_new, 1)

    return content, wasm_uri


def _inject_preload_snippet(content: str, wasm_uri: Optional[str]) -> str:
    if not wasm_uri:
        return content
    preload_script = (
        "<script>\n"
        "  window.__rdkitPreloadedWasm = (function () {\n"
        "    const dataUri = \"" + wasm_uri + "\";\n"
        "    if (!dataUri.startsWith(\"data:\")) {\n"
        "      return null;\n"
        "    }\n"
        "    const base64 = dataUri.split(\",\")[1];\n"
        "    const binaryString = atob(base64);\n"
        "    const bytes = new Uint8Array(binaryString.length);\n"
        "    for (let i = 0; i < binaryString.length; i++) {\n"
        "      bytes[i] = binaryString.charCodeAt(i);\n"
        "    }\n"
        "    return bytes;\n"
        "  })();\n"
        "</script>\n"
    )
    if "</head>" in content:
        return content.replace("</head>", f"{preload_script}</head>", 1)
    return preload_script + content


@st.cache_data(show_spinner=False)
def load_html() -> Optional[str]:
    if not HTML_FILE.exists():
        return None

    content = HTML_FILE.read_text(encoding="utf-8")
    content = _strip_inline_rdkit_bootstrap(content)
    assets = preload_rdkit_assets()
    content, wasm_uri = _inline_rdkit_assets(content, assets)
    content = _inject_preload_snippet(content, wasm_uri)
    return content


html_content = load_html()
if html_content:
    st.components.v1.html(html_content, height=900, scrolling=True)
else:
    st.error("Cannot find index.html. Please ensure the file exists in the project root.")
