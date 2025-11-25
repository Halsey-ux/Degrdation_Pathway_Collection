"""
Streamlit 应用：SMILES 树状分子图
"""

import os
import re
import base64
import streamlit as st

st.set_page_config(
    page_title="SMILES 树状分子图",
    page_icon="🧬",
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


@st.cache_data
def load_html():
    html_file = "index.html"
    if not os.path.exists(html_file):
        return None
    with open(html_file, "r", encoding="utf-8") as f:
        content = f.read()

    content = re.sub(
        r"<script>\s*\(function\(\)\s*{[\s\S]*?window\.__rdkitLocalWasm\s*=\s*\"__rdkit_inline_wasm__\";\s*}\)\(\);\s*</script>\s*",
        "",
        content,
        count=1,
    )

    def encode_data_uri(path: str, mime: str) -> str:
        if not os.path.exists(path):
            return ""
        with open(path, "rb") as file:
            data = base64.b64encode(file.read()).decode("ascii")
        return f"data:{mime};base64,{data}"

    js_uri = encode_data_uri("rdkit_minimal.js", "application/javascript")
    wasm_uri = encode_data_uri("RDKit_minimal.wasm", "application/wasm")

    if js_uri:
        content = content.replace('src="rdkit_minimal.js"', f'src="{js_uri}"')
        content = content.replace(
            'const RDKIT_LOCAL_JS = "rdkit_minimal.js";',
            f'const RDKIT_LOCAL_JS = "{js_uri}";',
        )
    if wasm_uri:
        content = content.replace('href="RDKit_minimal.wasm"', f'href="{wasm_uri}"')
        content = content.replace(
            'const RDKIT_LOCAL_WASM = "RDKit_minimal.wasm";',
            f'const RDKIT_LOCAL_WASM = "{wasm_uri}";',
        )
        fetch_old = (
            "async function fetchWasm(url) {\r\n"
            "      const response = await fetch(url);\r\n"
            "      if (!response.ok) {\r\n"
            "        throw new Error(`拉取 wasm 失败：${response.status}`);\r\n"
            "      }\r\n"
            "      const buffer = await response.arrayBuffer();\r\n"
            "      return new Uint8Array(buffer);\r\n"
            "    }"
        )
        fetch_new = (
            "async function fetchWasm(url) {\r\n"
            "      if (url.startsWith(\"data:\")) {\r\n"
            "        const base64 = url.split(\",\")[1];\r\n"
            "        const binaryString = atob(base64);\r\n"
            "        const bytes = new Uint8Array(binaryString.length);\r\n"
            "        for (let i = 0; i < binaryString.length; i++) {\r\n"
            "          bytes[i] = binaryString.charCodeAt(i);\r\n"
            "        }\r\n"
            "        return bytes;\r\n"
            "      }\r\n"
            "      const response = await fetch(url);\r\n"
            "      if (!response.ok) {\r\n"
            "        throw new Error(`拉取 wasm 失败：${response.status}`);\r\n"
            "      }\r\n"
            "      const buffer = await response.arrayBuffer();\r\n"
            "      return new Uint8Array(buffer);\r\n"
            "    }"
        )
        content = content.replace(fetch_old, fetch_new, 1)

    return content


html_content = load_html()
if html_content:
    st.components.v1.html(html_content, height=900, scrolling=True)
else:
    st.error("无法找到 index.html 文件，请确认文件存在于项目根目录。")
