"""
Streamlit 应用：SMILES 树状分子图
将 HTML/JS/WASM 前端应用包装为 Streamlit 应用
"""

import streamlit as st
import os

# 设置页面配置
st.set_page_config(
    page_title="SMILES 树状分子图",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 隐藏 Streamlit 的默认样式
st.markdown("""
    <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {
            padding: 0 !important;
            background: #fefefe;
        }
        [data-testid="stSidebar"] {display: none;}
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        .st-emotion-cache-1wrcr25,
        .st-emotion-cache-1dp5vir,
        .st-emotion-cache-13ln4jf {padding: 0 !important;}
    </style>
""", unsafe_allow_html=True)

# 读取并处理 HTML 文件
@st.cache_data
def load_html():
    """读取 index.html."""
    html_file = "index.html"
    if not os.path.exists(html_file):
        return None
    with open(html_file, "r", encoding="utf-8") as f:
        return f.read()

# 加载并显示 HTML
html_content = load_html()

if html_content:
    # 使用 st.components.v1.html 来渲染 HTML
    # height 设置为足够大以容纳整个应用
    st.components.v1.html(html_content, height=900, scrolling=True)
else:
    st.error("无法找到 index.html 文件。请确保文件存在于项目根目录。")

