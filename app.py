import streamlit as st
import google.generativeai as genai
from openai import OpenAI
from PIL import Image
import base64

st.set_page_config(page_title="高中数学AI助手", page_icon="📚", layout="wide")
st.title("📚 高中数学作业AI分析器")
st.markdown("**上传照片 → AI瞬间批改+讲解+打分**（Gemini 2.5 Flash）")

# ==================== 侧边栏（部署后自动用secrets） ====================
with st.sidebar:
    provider = st.selectbox("选择AI模型", 
                            ["Gemini 2.5 Flash（推荐）", "Grok（xAI）"], index=0)
    
    # 🔥 部署安全写法：先从secrets读，没有再让输入
    if provider.startswith("Gemini"):
        gemini_key = st.secrets.get("GEMINI_API_KEY", None)
        if gemini_key:
            api_key = gemini_key
            st.success("✅ 已自动读取部署的Gemini Key")
        else:
            api_key = st.text_input("粘贴Gemini Key（本地测试用）", type="password")
            st.caption("部署后不需要填，系统自动读取")
    else:
        api_key = st.text_input("粘贴Grok Key", type="password")
    
    st.caption("部署成功后别人看不到你的Key！")

# 文件上传部分不变（和之前完全一样）
uploaded_file = st.file_uploader("📸 上传作业照片（jpg/png）", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="你的作业", use_column_width=True)
    
    if st.button("🚀 开始AI分析", type="primary", use_container_width=True):
        if not api_key:
            st.error("请输入Key（或检查部署secrets）")
        else:
            with st.spinner("AI批改中..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    if "Gemini" in provider:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel('gemini-2.5-flash')
                        response = model.generate_content([
                            "你是资深高中数学老师。请仔细看图片：识别所有题目、正确答案、错误点、一步步讲解、打分100分、鼓励。用Markdown。",
                            {"mime_type": "image/jpeg", "data": bytes_data}
                        ])
                        result = response.text
                    else:
                        # Grok代码不变...
                        client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
                        base64_image = base64.b64encode(bytes_data).decode()
                        # ...（保持你之前的Grok部分）
                        result = "Grok分析结果"
                    
                    st.success("✅ 完成！")
                    st.markdown(result)
                    st.download_button("📥 下载", result, "分析.md")
                except Exception as e:
                    st.error(str(e))