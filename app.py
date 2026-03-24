import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import base64
from datetime import datetime

st.set_page_config(page_title="高中数学AI系统", layout="wide")

# Supabase 配置
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(supabase_url, supabase_key)

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
st.caption("by Yuri in Gxu | 使用 n1n.ai")

if st.session_state.user is None:
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        email = st.text_input("邮箱")
        password = st.text_input("密码", type="password")
        if st.button("登录"):
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

    # 上传分析（使用 n1n.ai）
    uploaded_file = st.file_uploader("上传作业照片", type=["jpg", "png"])
    if uploaded_file and st.button("开始分析"):
        with st.spinner("AI分析中..."):
            try:
                client = OpenAI(
                    api_key=st.secrets["THIRD_API_KEY"],
                    base_url=st.secrets["THIRD_BASE_URL"]
                )

                base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

                response = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[
                        {"role": "system", "content": "你是专业高中数学老师。请用清晰的Markdown格式批改作业：识别每道题、给出正确答案、指出错误、一步步详细讲解、打分（满分100）、给出改进建议。"},
                        {"role": "user", "content": [
                            {"type": "text", "text": "请帮我批改这份数学作业"},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]}
                    ],
                    max_tokens=1500,
                    temperature=0.7
                )

                result = response.choices[0].message.content

                # 保存到数据库（使用 service_role key 绕过 RLS）
                service_supabase = create_client(supabase_url, st.secrets["SUPABASE_SERVICE_KEY"])
                service_supabase.table("analyses").insert({
                    "user_id": str(user.id),
                    "result_text": result,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()

                st.success("✅ 分析完成，已保存")
                st.markdown(result)
                st.download_button("📥 下载报告", result.encode('utf-8'), "报告.md", mime="text/markdown")

            except Exception as e:
                st.error(f"调用失败: {str(e)}")

    # 历史记录
    records = supabase.table("analyses").select("*").eq("user_id", user.id).order("timestamp", desc=True).limit(5).execute().data
    st.markdown("### 历史记录")
    for r in records:
        with st.expander(r["timestamp"]):
            st.markdown(r["result_text"])

    # 总结薄弱点
    if st.button("总结薄弱点"):
        records = supabase.table("analyses").select("result_text").eq("user_id", user.id).execute().data
        if records:
            all_text = "\n\n".join([r["result_text"] for r in records])
            with st.spinner("汇总中..."):
                client = OpenAI(api_key=st.secrets["THIRD_API_KEY"], base_url=st.secrets["THIRD_BASE_URL"])
                resp = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[{"role": "user", "content": f"总结以下作业记录中最需要补的知识点（3-6个，名称+原因+建议）：{all_text[:12000]}"}]
                )
                st.markdown(resp.choices[0].message.content)
        else:
            st.info("先分析几次作业吧")

st.caption("数据永久保存")
st.caption("· by Yuri in Gxu")
