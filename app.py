import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import base64
from datetime import datetime, timedelta
from streamlit_cookies_controller import CookieController
import json
import time

st.set_page_config(page_title="高中数学AI系统", layout="wide")

# Supabase 配置
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(supabase_url, supabase_key)

# ==================== Cookie 管理器 ====================
cookie = CookieController()

# ==================== 初始化 session_state ====================
if "user" not in st.session_state:
    st.session_state.user = None

if "auth_checked" not in st.session_state:
    st.session_state.auth_checked = False

# ==================== 自动登录（从 Cookie 恢复会话） ====================
if not st.session_state.auth_checked:
    st.session_state.auth_checked = True
    try:
        saved_session = cookie.get("math_ai_session")
        if saved_session:
            session_data = json.loads(saved_session)
            expire_time = datetime.fromisoformat(session_data["expires_at"])
            if datetime.utcnow() < expire_time:
                # Cookie 未过期，尝试用 token 恢复会话
                try:
                    res = supabase.auth.set_session(
                        session_data["access_token"],
                        session_data["refresh_token"]
                    )
                    if res and res.user:
                        st.session_state.user = res.user
                except Exception:
                    # Token 失效，清除 Cookie
                    cookie.remove("math_ai_session")
            else:
                # Cookie 已过期，清除
                cookie.remove("math_ai_session")
    except Exception:
        pass

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

                # 保存 session 到 Cookie，有效期20分钟
                session_data = {
                    "access_token": res.session.access_token,
                    "refresh_token": res.session.refresh_token,
                    "expires_at": (datetime.utcnow() + timedelta(minutes=20)).isoformat()
                }
                cookie.set(
                    "math_ai_session",
                    json.dumps(session_data),
                    max_age=1200  # 20分钟 = 1200秒
                )

                st.success("登录成功")
                time.sleep(0.5)
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
        # 清除 Cookie
        try:
            cookie.remove("math_ai_session")
        except Exception:
            pass
        st.rerun()

    # 上传分析
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

    # ==================== 历史记录 ====================
    st.markdown("### 📜 我的历史批改记录")
    records = supabase.table("analyses").select("*").eq("user_id", str(user.id)).order("timestamp", desc=True).execute().data

    if records:
        for r in records:
            with st.expander(f"📅 {r['timestamp'][:16]} 的批改记录"):
                st.markdown(r["result_text"])
    else:
        st.info("还没有批改记录，快上传第一张作业吧～")

    # ==================== 总结薄弱点（带时间选择） ====================
    st.markdown("### 🔍 总结我的知识漏洞")
    time_range = st.selectbox(
        "选择总结范围",
        ["全部记录", "最近7天", "最近30天", "最近90天"],
        index=0
    )

    if st.button("开始总结薄弱知识点"):
        if time_range == "全部记录":
            filtered_records = records
        else:
            days = {"最近7天": 7, "最近30天": 30, "最近90天": 90}[time_range]
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered_records = [r for r in records if datetime.fromisoformat(r["timestamp"].replace("Z", "")) > cutoff]

        if filtered_records:
            all_text = "\n\n".join([r["result_text"] for r in filtered_records])
            with st.spinner("AI正在分析你的所有记录..."):
                client = OpenAI(api_key=st.secrets["THIRD_API_KEY"], base_url=st.secrets["THIRD_BASE_URL"])
                resp = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[{"role": "user", "content": f"总结以下作业记录中最需要补的知识点（3-6个，名称+原因+建议）：{all_text[:15000]}"}]
                )
                st.markdown(resp.choices[0].message.content)
        else:
            st.warning("该时间范围内没有记录")

st.caption("数据永久保存 · by Yuri in Gxu | 使用 n1n.ai")
