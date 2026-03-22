import streamlit as st
import google.generativeai as genai
from PIL import Image
from datetime import datetime

st.set_page_config(page_title="高中数学AI智能分析系统", page_icon="📊", layout="wide")

# ==================== 沉稳专业深蓝风格 ====================
st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .big-title {font-size: 38px; font-weight: bold; color: #1E88E5;}
    .stButton>button {background-color: #1E88E5; color: white; font-size: 18px; height: 55px;}
    .card {background-color: #1E1E2E; padding: 15px; border-radius: 10px; border: 1px solid #334455;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">📊 高中数学AI智能分析系统</h1>', unsafe_allow_html=True)
st.caption("沉稳专业版 · by Yuri in Gxu · 每个同学独立使用")

# ==================== 用户系统（简单实现，无需额外包） ====================
if 'users' not in st.session_state:
    st.session_state.users = {"admin": {"password": "123456", "history": []}}  # 默认账号，实际可多人注册
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

# 登录/注册页面
if st.session_state.current_user is None:
    tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
    
    with tab1:
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        if st.button("登录"):
            if username in st.session_state.users and st.session_state.users[username]["password"] == password:
                st.session_state.current_user = username
                st.success(f"欢迎回来，{username}！")
                st.rerun()
            else:
                st.error("用户名或密码错误")
    
    with tab2:
        new_user = st.text_input("新用户名")
        new_pass = st.text_input("新密码", type="password")
        if st.button("注册账号"):
            if new_user and new_user not in st.session_state.users:
                st.session_state.users[new_user] = {"password": new_pass, "history": []}
                st.success(f"注册成功！请用 {new_user} / {new_pass} 登录")
            else:
                st.error("用户名已存在或为空")

else:
    # 已登录界面（沉稳主界面）
    st.sidebar.success(f"👤 已登录：{st.session_state.current_user}")
    if st.sidebar.button("退出登录"):
        st.session_state.current_user = None
        st.rerun()

    # 侧边栏
    with st.sidebar:
        st.markdown("### 📈 我的学习情况")
        if st.button("🔍 一键AI总结知识漏洞"):
            if st.session_state.users[st.session_state.current_user]["history"]:
                all_text = "\n\n".join([h["result"] for h in st.session_state.users[st.session_state.current_user]["history"]])
                with st.spinner("AI正在分析你的所有作业，找出薄弱点..."):
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    resp = model.generate_content(f"""
你是高中数学老师。根据以下该学生所有作业分析记录，总结他当前最需要补的知识点漏洞。
要求：
1. 列出3-6个具体知识点名称（如：二次函数图像、导数应用、三角恒等变换等）
2. 每个知识点说明为什么弱（举例）
3. 给出针对性复习建议和优先级
学生记录：{all_text[:8000]}
                    """)
                    gap_summary = resp.text
                    st.session_state.gap_summary = gap_summary
                st.success("知识漏洞分析完成")
                st.markdown(gap_summary)
            else:
                st.info("先做几次作业分析吧～")

        st.caption("by Yuri in Gxu")

    # 主内容
    st.markdown("### 📸 上传作业进行分析")
    uploaded_file = st.file_uploader("选择作业照片（jpg/png）", type=["jpg", "jpeg", "png"])

    if uploaded_file:
        st.image(uploaded_file, caption="已上传", use_column_width=True)
        
        if st.button("🚀 开始AI分析", type="primary"):
            with st.spinner("分析中..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([
                    "你是专业高中数学老师。用清晰专业Markdown格式：识别题目、正确答案、错误分析、详细步骤讲解、打分/100、改进建议。",
                    {"mime_type": "image/jpeg", "data": uploaded_file.getvalue()}
                ])
                result = response.text
                
                # 保存到该用户历史
                st.session_state.users[st.session_state.current_user]["history"].append({
                    "time": datetime.now().strftime("%m-%d %H:%M"),
                    "result": result
                })
                
                st.success("分析完成")
                st.markdown(result)
                st.download_button("📥 下载本次分析", result.encode('utf-8'), "分析报告.md", mime="text/markdown")

    # 显示历史
    st.markdown("### 📜 我的历史分析")
    history = st.session_state.users[st.session_state.current_user]["history"]
    if history:
        for item in history[-5:]:  # 显示最近5条
            with st.expander(f"{item['time']} 的分析"):
                st.markdown(item["result"][:300] + "...")
    else:
        st.info("还没有分析记录，上传一次作业后就会出现")

    st.caption("💡 当前版本为演示，历史保存在本次会话。想永久保存可告诉我，我帮你加免费数据库。")
