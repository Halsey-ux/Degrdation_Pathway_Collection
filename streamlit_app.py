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


def _has_valid_external_html() -> bool:
    return HTML_FILE.exists() and HTML_FILE.stat().st_size > 0


def _build_inline_app(assets: Dict[str, str]) -> Optional[str]:
    js_uri = assets.get(RDKit_JS)
    wasm_uri = assets.get(RDKit_WASM)
    if not js_uri or not wasm_uri:
        return None

    wasm_base64 = wasm_uri.split(",", 1)[1]
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SMILES Degradation Pathway</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", sans-serif;
      background: #fefefe;
      color: #222;
    }}
    .app {{
      display: flex;
      flex-direction: column;
      gap: 1rem;
      padding: 1.5rem;
    }}
    .controls {{
      display: flex;
      gap: 0.75rem;
      flex-wrap: wrap;
      align-items: flex-start;
    }}
    textarea {{
      flex: 1;
      min-height: 120px;
      padding: 0.75rem;
      border-radius: 8px;
      border: 1px solid #d0d0d0;
      font-size: 0.95rem;
      resize: vertical;
    }}
    button {{
      padding: 0.8rem 1.5rem;
      border-radius: 999px;
      border: none;
      background: #2563eb;
      color: #fff;
      font-size: 0.95rem;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.2s ease;
    }}
    button:hover {{
      background: #1d4ed8;
    }}
    .pathway {{
      display: flex;
      gap: 1.5rem;
      flex-wrap: wrap;
      align-items: center;
      justify-content: flex-start;
    }}
    .step {{
      min-width: 220px;
      padding: 1rem;
      border-radius: 16px;
      background: #ffffff;
      box-shadow: 0 10px 40px rgba(15, 23, 42, 0.1);
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .step h3 {{
      margin: 0;
      font-size: 1rem;
      color: #0f172a;
    }}
    .step svg {{
      width: 100%;
      height: auto;
    }}
    .arrow {{
      font-size: 1.5rem;
      color: #94a3b8;
    }}
    .error {{
      color: #b91c1c;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <div class="app">
    <div class="controls">
      <textarea id="smiles-input" placeholder="Enter SMILES, one per line">CCO
CC(=O)O
O=C(O)C(O)CO</textarea>
      <button id="render-btn" type="button">Render Pathway</button>
    </div>
    <div id="feedback" class="error"></div>
    <div class="pathway" id="pathway"></div>
  </div>

  <script src="{js_uri}"></script>
  <script>
    const RDKIT_WASM_BASE64 = "{wasm_base64}";

    function base64ToBytes(base64) {{
      const binaryString = atob(base64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {{
        bytes[i] = binaryString.charCodeAt(i);
      }}
      return bytes;
    }}

    const rdkitReady = (function () {{
      const wasmBytes = base64ToBytes(RDKIT_WASM_BASE64);
      return initRDKitModule({{ wasmBinary: wasmBytes }});
    }})();

    function createStep(index, smiles, svg) {{
      const card = document.createElement("div");
      card.className = "step";
      const title = document.createElement("h3");
      title.innerText = `Step ${index + 1}`;
      const smilesEl = document.createElement("div");
      smilesEl.innerText = smiles;
      smilesEl.style.fontFamily = "monospace";
      smilesEl.style.fontSize = "0.85rem";
      const svgWrapper = document.createElement("div");
      svgWrapper.innerHTML = svg;
      card.appendChild(title);
      card.appendChild(svgWrapper);
      card.appendChild(smilesEl);
      return card;
    }}

    async function renderPathway() {{
      const feedback = document.getElementById("feedback");
      const container = document.getElementById("pathway");
      feedback.innerText = "";
      container.innerHTML = "<p>Rendering pathway…</p>";
      const rawInput = document.getElementById("smiles-input").value || "";
      const smilesList = rawInput
        .split(/\\n+/)
        .map((item) => item.trim())
        .filter(Boolean);

      if (!smilesList.length) {{
        container.innerHTML = "";
        feedback.innerText = "Please provide at least one SMILES string.";
        return;
      }}

      try {{
        const RDKit = await rdkitReady;
        container.innerHTML = "";
        smilesList.forEach((smiles, index) => {{
          try {{
            const mol = RDKit.get_mol(smiles);
            const svg = mol.get_svg();
            mol.delete();
            const stepEl = createStep(index, smiles, svg);
            container.appendChild(stepEl);
            if (index < smilesList.length - 1) {{
              const arrow = document.createElement("div");
              arrow.className = "arrow";
              arrow.innerHTML = "&#8594;";
              container.appendChild(arrow);
            }}
          }} catch (err) {{
            const errorCard = document.createElement("div");
            errorCard.className = "step";
            errorCard.innerHTML = `<strong>Error parsing:</strong> ${smiles}`;
            container.appendChild(errorCard);
          }}
        }});
      }} catch (error) {{
        container.innerHTML = "";
        feedback.innerText =
          "Failed to initialize RDKit. Please refresh and try again.";
      }}
    }}

    document
      .getElementById("render-btn")
      .addEventListener("click", renderPathway);

    window.addEventListener("DOMContentLoaded", () => {{
      renderPathway();
    }});
  </script>
</body>
</html>
    """
    return html


@st.cache_data(show_spinner=False)
def load_html() -> Optional[str]:
    assets = preload_rdkit_assets()
    if _has_valid_external_html():
        content = HTML_FILE.read_text(encoding="utf-8")
        content = _strip_inline_rdkit_bootstrap(content)
        content, wasm_uri = _inline_rdkit_assets(content, assets)
        content = _inject_preload_snippet(content, wasm_uri)
        return content

    inline_app = _build_inline_app(assets)
    return inline_app


html_content = load_html()
if html_content:
    st.components.v1.html(html_content, height=900, scrolling=True)
else:
    st.error("Cannot load RDKit assets. Please verify rdkit_minimal.js and RDKit_minimal.wasm.")
