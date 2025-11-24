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
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp {
            padding-top: 0rem;
        }
    </style>
""", unsafe_allow_html=True)

# 读取 HTML 文件
@st.cache_data
def load_html():
    """加载 HTML 文件内容"""
    html_file = "index.html"
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return f.read()
    return None

# 加载并显示 HTML
html_content = load_html()

if html_content:
    # 使用 st.components.v1.html 来渲染 HTML
    # height 设置为足够大以容纳整个应用
    st.components.v1.html(html_content, height=900, scrolling=True)
else:
    st.error("无法找到 index.html 文件。请确保文件存在于项目根目录。")

