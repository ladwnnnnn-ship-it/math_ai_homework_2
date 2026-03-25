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

# ==================== 管理员邮箱列表 ====================
ADMIN_EMAILS = ["2155837094@qq.com", "3211038552@qq.com", "test@test.com","1@1.com"，"yk49474947@gmail.com"]

# ==================== Cookie 管理器 ====================
cookie = CookieController()

# ==================== 初始化 session_state ====================
if "user" not in st.session_state:
    st.session_state.user = None

if "auth_checked" not in st.session_state:
    st.session_state.auth_checked = False

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []  # 聊天记录 [{"role": "user"/"assistant", "content": ...}]

# ==================== 自动登录（从 Cookie 恢复会话） ====================
if not st.session_state.auth_checked:
    st.session_state.auth_checked = True
    try:
        saved_session = cookie.get("math_ai_session")
        if saved_session:
            session_data = json.loads(saved_session)
            expire_time = datetime.fromisoformat(session_data["expires_at"])
            if datetime.utcnow() < expire_time:
                try:
                    res = supabase.auth.set_session(
                        session_data["access_token"],
                        session_data["refresh_token"]
                    )
                    if res and res.user:
                        st.session_state.user = res.user
                except Exception:
                    cookie.remove("math_ai_session")
            else:
                cookie.remove("math_ai_session")
    except Exception:
        pass

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .big-title {font-size: 38px; font-weight: bold; color: #1E88E5;}
    .stButton>button {background-color: #1E88E5; color: white; font-size: 18px; height: 55px;}
    .chat-msg-user {background-color: #1E3A5F; border-radius: 12px; padding: 10px 14px; margin: 6px 0; text-align: right;}
    .chat-msg-ai {background-color: #1E2A1E; border-radius: 12px; padding: 10px 14px; margin: 6px 0;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">📊 高中数学AI智能分析系统</h1>', unsafe_allow_html=True)
st.caption("by Yuri_Lee | 使用 n1n.ai")

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
    is_admin = user.email in ADMIN_EMAILS

    st.sidebar.success(f"已登录：{user.email}")
    if is_admin:
        st.sidebar.markdown("🔑 **管理员账号**")
    if st.sidebar.button("退出登录"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.session_state.chat_messages = []
        try:
            cookie.remove("math_ai_session")
        except Exception:
            pass
        st.rerun()

    # ==================== 管理员：AI 聊天 ====================
    if is_admin:
        st.markdown("---")
        st.markdown("## 🤖 管理员 AI 对话")

        # 清空聊天记录按钮
        col1, col2 = st.columns([6, 1])
        with col2:
            if st.button("🗑️ 清空对话"):
                st.session_state.chat_messages = []
                st.rerun()

        # 显示历史聊天记录
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_messages:
                if msg["role"] == "user":
                    with st.chat_message("user"):
                        # 如果消息包含图片，显示图片
                        if isinstance(msg["content"], list):
                            for part in msg["content"]:
                                if part["type"] == "text":
                                    st.markdown(part["text"])
                                elif part["type"] == "image_url":
                                    # 从 base64 显示图片
                                    img_data = part["image_url"]["url"].split(",")[1]
                                    img_bytes = base64.b64decode(img_data)
                                    st.image(img_bytes, width=300)
                        else:
                            st.markdown(msg["content"])
                else:
                    with st.chat_message("assistant"):
                        st.markdown(msg["content"])

        # 图片上传（可选，最多9张）
        chat_images = st.file_uploader("📎 上传图片（可选，最多9张）", type=["jpg", "png", "jpeg"], key="chat_img", accept_multiple_files=True)
        if chat_images and len(chat_images) > 9:
            st.warning("最多只能上传9张图片，已自动截取前9张")
            chat_images = chat_images[:9]

        # 输入框
        user_input = st.chat_input("输入消息，按 Enter 发送...")

        if user_input:
            client = OpenAI(
                api_key=st.secrets["THIRD_API_KEY"],
                base_url=st.secrets["THIRD_BASE_URL"]
            )

            # 构建用户消息内容
            if chat_images:
                user_content = [{"type": "text", "text": user_input}]
                for img in chat_images:
                    b64 = base64.b64encode(img.getvalue()).decode("utf-8")
                    user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            else:
                user_content = user_input

            # 添加到聊天记录
            st.session_state.chat_messages.append({"role": "user", "content": user_content})

            # 构建发送给 API 的消息列表（带上下文）
            api_messages = [
                {"role": "system", "content": "你是一个全能AI助手，擅长高中数学、图片分析、解题讲解等。请用清晰的Markdown格式回答。"}
            ]
            for msg in st.session_state.chat_messages:
                api_messages.append({"role": msg["role"], "content": msg["content"]})

            # 调用 AI
            with st.spinner("AI思考中..."):
                try:
                    response = client.chat.completions.create(
                        model=st.secrets["THIRD_MODEL"],
                        messages=api_messages,
                        max_tokens=30000,
                        temperature=0.7
                    )
                    ai_reply = response.choices[0].message.content
                    st.session_state.chat_messages.append({"role": "assistant", "content": ai_reply})
                    st.rerun()
                except Exception as e:
                    st.error(f"AI 调用失败: {str(e)}")

        st.markdown("---")

    # ==================== 上传分析 ====================
    uploaded_files = st.file_uploader("上传作业照片（1-9张）", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
    if uploaded_files and len(uploaded_files) > 9:
        st.warning("最多只能上传9张图片，已自动截取前9张")
        uploaded_files = uploaded_files[:9]
    if uploaded_files and st.button("开始分析"):
        with st.spinner("AI分析中..."):
            try:
                client = OpenAI(
                    api_key=st.secrets["THIRD_API_KEY"],
                    base_url=st.secrets["THIRD_BASE_URL"]
                )

                # 构建多图消息
                image_parts = []
                for f in uploaded_files:
                    b64 = base64.b64encode(f.getvalue()).decode("utf-8")
                    image_parts.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})

                user_content = [{"type": "text", "text": f"请帮我批改这份数学作业（共{len(uploaded_files)}张图片）"}] + image_parts

                response = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[
                        {"role": "system", "content": "你是专业高中数学老师。请用清晰的Markdown格式批改作业：识别每道题、给出正确答案、指出错误、一步步详细讲解、打分（满分100）、给出改进建议。"},
                        {"role": "user", "content": user_content}
                    ],
                    max_tokens=30000,
                    temperature=0.7
                )

                result = response.choices[0].message.content

                # AI 自动生成标题（根据批改内容提取主题）
                title_resp = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[
                        {"role": "user", "content": f"根据以下作业批改内容，用不超过15个字概括本次作业的主要考察内容（例如：二次函数综合题、三角函数基础练习），只输出标题，不要其他内容：\n\n{result[:1000]}"}
                    ],
                    max_tokens=30000,
                    temperature=0.3
                )
                auto_title = title_resp.choices[0].message.content.strip()

                service_supabase = create_client(supabase_url, st.secrets["SUPABASE_SERVICE_KEY"])
                service_supabase.table("analyses").insert({
                    "user_id": str(user.id),
                    "title": auto_title,
                    "result_text": result,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()

                st.success(f"✅ 分析完成，已保存：《{auto_title}》")
                st.markdown(result)
                st.download_button("📥 下载报告", result.encode('utf-8'), f"{auto_title}.md", mime="text/markdown")

            except Exception as e:
                st.error(f"调用失败: {str(e)}")

    # ==================== 历史记录 ====================
    st.markdown("### 📜 我的历史批改记录")

    try:
        service_supabase_read = create_client(supabase_url, st.secrets["SUPABASE_SERVICE_KEY"])
        records_resp = service_supabase_read.table("analyses").select("*").eq("user_id", str(user.id)).order("timestamp", desc=True).execute()
        records = records_resp.data
    except Exception as e:
        st.error(f"读取历史记录失败: {str(e)}")
        records = []

    if records:
        st.caption(f"共 {len(records)} 条记录")
        for r in records:
            title = r.get("title") or "未命名作业"
            ts = r.get("timestamp", "")[:16].replace("T", " ")
            with st.expander(f"📅 {ts}　｜　📝 {title}"):
                st.markdown(r.get("result_text", "（内容为空）"))
    else:
        st.info("还没有批改记录，快上传第一张作业吧～")

    # ==================== 总结薄弱点 ====================
    st.markdown("### 🔍 总结我的知识漏洞")

    if records:
        summary_mode = st.radio(
            "选择总结方式",
            ["按时间范围选择", "手动勾选记录"],
            horizontal=True
        )

        filtered_records = []

        if summary_mode == "按时间范围选择":
            time_range = st.selectbox(
                "选择时间范围",
                ["全部记录", "最近7天", "最近30天", "最近90天"],
                index=0
            )
            if time_range == "全部记录":
                filtered_records = records
            else:
                days = {"最近7天": 7, "最近30天": 30, "最近90天": 90}[time_range]
                cutoff = datetime.utcnow() - timedelta(days=days)
                filtered_records = [
                    r for r in records
                    if datetime.fromisoformat(r["timestamp"].replace("Z", "").split(".")[0]) > cutoff
                ]
            if filtered_records:
                st.caption(f"已选中 {len(filtered_records)} 条记录")
            else:
                st.warning("该时间范围内没有记录")

        else:  # 手动勾选
            st.caption("勾选你想纳入分析的记录：")
            selected_ids = []
            for r in records:
                title = r.get("title") or "未命名作业"
                ts = r.get("timestamp", "")[:16].replace("T", " ")
                if st.checkbox(f"📅 {ts}　｜　📝 {title}", key=f"chk_{r['id']}"):
                    selected_ids.append(r["id"])
            filtered_records = [r for r in records if r["id"] in selected_ids]
            if filtered_records:
                st.caption(f"已选中 {len(filtered_records)} 条记录")

        if st.button("开始总结薄弱知识点"):
            if filtered_records:
                all_text = "\n\n".join([r["result_text"] for r in filtered_records])
                with st.spinner("AI正在分析你的记录..."):
                    client = OpenAI(api_key=st.secrets["THIRD_API_KEY"], base_url=st.secrets["THIRD_BASE_URL"])
                    resp = client.chat.completions.create(
                        model=st.secrets["THIRD_MODEL"],
                        messages=[{"role": "user", "content": f"总结以下作业记录中最需要补的知识点（3-6个，名称+原因+建议）：{all_text[:15000]}"}],
                        max_tokens=30000
                    )
                    st.markdown(resp.choices[0].message.content)
            else:
                st.warning("请先选择至少一条记录")
    else:
        st.info("还没有批改记录，无法总结知识漏洞")

st.caption("数据永久保存 · by Yuri_Lee | Powered by Gemini-3.1-pro")
