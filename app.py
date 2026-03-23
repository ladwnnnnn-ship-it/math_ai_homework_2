import streamlit as st
from supabase import create_client, Client
from google import generativeai as genai  # 新方式
from PIL import Image
from datetime import datetime

st.set_page_config(page_title="高中数学AI系统", layout="wide")

# Supabase 客户端（从 secrets 读）
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_ANON_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# 用户状态
if "user" not in st.session_state:
    st.session_state.user = None

# 沉稳风格
st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .big-title {font-size: 38px; font-weight: bold; color: #1E88E5;}
    .stButton>button {background-color: #1E88E5; color: white; font-size: 18px; height: 55px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">📊 高中数学AI智能分析系统</h1>', unsafe_allow_html=True)

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        email = st.text_input("邮箱")
        password = st.text_input("密码", type="password")
        if st.button("登录"):
            st.write("你输入的邮箱是：", email)           # 新增
            st.write("你输入的密码长度是：", len(password))  # 新增，看是否为空或异常
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("登录成功")
                st.rerun()
            except Exception as e:
                st.error(f"登录失败: {str(e)}")
    with tab2:
        new_email = st.text_input("新邮箱")
        new_pass = st.text_input("新密码", type="password")
        if st.button("注册"):
            try:
                res = supabase.auth.sign_up({"email": new_email, "password": new_pass})
                st.success("注册成功！请登录")
            except Exception as e:
                st.error(f"注册失败: {str(e)}")

else:
    user = st.session_state.user
    st.sidebar.success(f"已登录：{user.email}")
    if st.sidebar.button("退出登录"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

    # 管理员面板
    if user.email == "test@test.com":  # 改成你的真实邮箱
        st.header("管理员后台")
        try:
            # 需要 service_role key 才能查所有用户（secrets 加 SUPABASE_SERVICE_KEY）
            service_supabase = create_client(supabase_url, st.secrets["SUPABASE_SERVICE_KEY"])
            users = service_supabase.table("auth.users").select("email, created_at").execute().data
            st.write("用户列表：")
            st.dataframe(users)
        except:
            st.warning("查看用户列表需要 service_role key")

    # 上传分析
    uploaded_file = st.file_uploader("上传作业照片", type=["jpg", "png"])
    if uploaded_file and st.button("开始分析"):
        with st.spinner("分析中..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content([  # ← 这里定义了 response
                    "你是专业高中数学老师。用清晰Markdown格式：识别题目、正确答案、错误分析、详细讲解、打分/100、建议。",
                    {"mime_type": "image/jpeg", "data": uploaded_file.getvalue()}
                ])
                result = response.text  # ← 这里用 response.text
            # 插入前打印调试
                st.write("当前用户 ID:", user.id)  # 确认有 uuid
                st.write("当前登录用户 auth.uid():", user.id)  # 应该打印 uuid 如 6600b96f-...
                st.write("准备插入的 user_id 值:", user.id)     # 必须一样

                supabase.table("analyses").insert({
                    "user_id": str(user.id),  # 强制转字符串
                    "result_text": result,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()

                st.success("分析完成，已保存")
                st.markdown(result)
                st.download_button("下载报告", result.encode('utf-8'), "报告.md", mime="text/markdown")
            except Exception as e:
                st.error(f"分析或插入失败: {str(e)}")
                st.info(f"详细错误: {repr(e)}")

    # 历史
    records = supabase.table("analyses").select("*").eq("user_id", user.id).order("timestamp", desc=True).limit(5).execute().data
    st.markdown("### 历史记录")
    for r in records:
        with st.expander(r["timestamp"]):
            st.markdown(r["result_text"])

    # 漏洞总结
    if st.button("总结薄弱点"):
        records = supabase.table("analyses").select("result_text").eq("user_id", user.id).execute().data
        if records:
            all_text = "\n\n".join([r["result_text"] for r in records])
            with st.spinner("汇总中..."):
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-2.5-flash')
                resp = model.generate_content(f"总结薄弱知识点（3-6个，名称+原因+建议）：{all_text[:10000]}")
                st.markdown(resp.text)
        else:
            st.info("先分析几次")

st.caption("数据永久保存 · by Yuri in Gxu")
