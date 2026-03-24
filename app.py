import streamlit as st
from supabase import create_client, Client
from openai import OpenAI
import base64
from datetime import datetime, timedelta

st.set_page_config(page_title="高中数学AI系统", layout="wide")

# ==================== Supabase 配置 ====================
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_ANON_KEY"]
supabase = create_client(supabase_url, supabase_key)
db_client = create_client(supabase_url, st.secrets["SUPABASE_SERVICE_KEY"])

if "user" not in st.session_state:
    st.session_state.user = None

st.markdown("""
<style>
    .main {background-color: #0E1117;}
    .big-title {font-size: 38px; font-weight: bold; color: #1E88E5;}
    .stButton>button {background-color: #1E88E5; color: white; font-size: 18px; height: 55px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">📊 高中数学AI智能分析系统</h1>', unsafe_allow_html=True)
st.caption("by Yuri in Gxu | 使用 n1n.ai")

# ==================== 登录/注册 ====================
if st.session_state.user is None:
    tab1, tab2 = st.tabs(["登录", "注册"])
    with tab1:
        email = st.text_input("邮箱", key="login_email")
        password = st.text_input("密码", type="password", key="login_pass")
        if st.button("登录"):
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                st.session_state.user = res.user
                st.success("登录成功")
                st.rerun()
            except Exception as e:
                st.error(f"登录失败: {str(e)}")
    with tab2:
        new_email = st.text_input("新邮箱", key="reg_email")
        new_pass = st.text_input("新密码", type="password", key="reg_pass")
        if st.button("注册"):
            try:
                supabase.auth.sign_up({"email": new_email, "password": new_pass})
                st.success("注册成功！请登录")
            except Exception as e:
                st.error(f"注册失败: {str(e)}")

else:
    user = st.session_state.user
    st.sidebar.success(f"已登录：{user.email}")
    if st.sidebar.button("退出登录"):
        try:
            supabase.auth.sign_out()
        except:
            pass
        st.session_state.user = None
        st.rerun()

    # ==================== 上传作业 ====================
    st.markdown("### 📤 上传作业")

    homework_title = st.text_input(
        "📝 本次作业名称（必填）",
        placeholder="例如：第三章 函数与导数 课后练习"
    )

    uploaded_files = st.file_uploader(
        "上传作业照片（支持 1~9 张，一次上传算一次批改）",
        type=["jpg", "png"],
        accept_multiple_files=True
    )

    # ---- 图片预览 ----
    if uploaded_files:
        if len(uploaded_files) > 9:
            st.error("⚠️ 最多上传 9 张图片，请减少数量")
        else:
            st.success(f"已选择 {len(uploaded_files)} 张图片")
            preview_cols = st.columns(min(len(uploaded_files), 3))
            for i, f in enumerate(uploaded_files):
                with preview_cols[i % 3]:
                    st.image(f, caption=f"第 {i+1} 张", use_container_width=True)

    # ---- 提交前校验 ----
    if uploaded_files and not homework_title.strip():
        st.warning("⚠️ 请先输入作业名称")

    can_submit = (
        uploaded_files
        and 0 < len(uploaded_files) <= 9
        and homework_title.strip()
    )

    if can_submit and st.button("🚀 开始分析"):
        with st.spinner(f"AI 正在分析 {len(uploaded_files)} 张图片，请耐心等待..."):
            try:
                client = OpenAI(
                    api_key=st.secrets["THIRD_API_KEY"],
                    base_url=st.secrets["THIRD_BASE_URL"]
                )

                # ★ 构建多图消息
                content = [{
                    "type": "text",
                    "text": (
                        f"请帮我批改这份数学作业「{homework_title}」，"
                        f"共 {len(uploaded_files)} 张图片。"
                        f"请按图片顺序依次批改每张图中的所有题目。"
                    )
                }]
                for f in uploaded_files:
                    b64 = base64.b64encode(f.getvalue()).decode("utf-8")
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                    })

                response = client.chat.completions.create(
                    model=st.secrets["THIRD_MODEL"],
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是专业高中数学老师。请用清晰的 Markdown 格式批改作业：\n"
                                "1. 按图片顺序逐张批改\n"
                                "2. 识别每道题并编号\n"
                                "3. 给出正确答案\n"
                                "4. 指出错误并一步步详细讲解\n"
                                "5. 每张图片单独打分（满分100）\n"
                                "6. 最后给出总分和整体改进建议"
                            )
                        },
                        {"role": "user", "content": content}
                    ],
                    max_tokens=30000,
                    temperature=0.7
                )

                result = response.choices[0].message.content

                # ★ 保存到数据库（含 title 和 image_count）
                db_client.table("analyses").insert({
                    "user_id": str(user.id),
                    "title": homework_title.strip(),
                    "image_count": len(uploaded_files),
                    "result_text": result,
                    "timestamp": datetime.utcnow().isoformat()
                }).execute()

                st.success("✅ 分析完成，已保存！")
                st.markdown(result)
                st.download_button(
                    "📥 下载报告",
                    result.encode("utf-8"),
                    f"{homework_title}.md",
                    mime="text/markdown"
                )

            except Exception as e:
                st.error(f"分析失败: {str(e)}")

    # ==================== 历史批改记录 ====================
    st.markdown("---")
    st.markdown("### 📜 我的历史批改记录")

    try:
        records = (
            db_client.table("analyses")
            .select("*")
            .eq("user_id", str(user.id))
            .order("timestamp", desc=True)
            .execute()
            .data
        )
    except Exception as e:
        st.error(f"读取历史失败: {str(e)}")
        records = []

    st.caption(f"共 {len(records)} 条记录")

    if records:
        for i, r in enumerate(records):
            title = r.get("title") or "未命名作业"
            ts = r.get("timestamp", "")[:16].replace("T", " ")
            img_count = r.get("image_count") or 1

            with st.expander(
                f"📅 {ts}　|　📝 {title}　|　📷 {img_count} 张图片",
                expanded=(i == 0)
            ):
                st.markdown(r.get("result_text", "内容为空"))
                st.download_button(
                    "📥 下载本次报告",
                    r.get("result_text", "").encode("utf-8"),
                    f"{title}.md",
                    mime="text/markdown",
                    key=f"dl_{r.get('id', i)}"
                )
    else:
        st.info("还没有批改记录，快上传第一份作业吧～")

    # ==================== 总结知识漏洞 ====================
    st.markdown("---")
    st.markdown("### 🔍 总结我的知识漏洞")

    if not records:
        st.info("暂无记录，上传作业后即可使用总结功能")
    else:
        # ★ 两种总结方式
        summary_mode = st.radio(
            "选择总结方式",
            ["✅ 手动勾选记录", "📅 按时间范围"],
            horizontal=True
        )

        filtered_records = []

        if summary_mode == "✅ 手动勾选记录":
            # ★ 构建选项列表（带序号防重名）
            options_map = {}
            option_labels = []
            for idx, r in enumerate(records):
                title = r.get("title") or "未命名作业"
                ts = r.get("timestamp", "")[:16].replace("T", " ")
                img_count = r.get("image_count") or 1
                label = f"[{idx+1}] 📅 {ts} | {title}（{img_count}张）"
                option_labels.append(label)
                options_map[label] = r

            selected_labels = st.multiselect(
                "勾选要总结的批改记录（可多选）",
                options=option_labels,
                default=None,
                placeholder="点击选择记录..."
            )
            filtered_records = [options_map[lb] for lb in selected_labels]

            if selected_labels:
                st.caption(f"已选择 {len(filtered_records)} 条记录")

        else:
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
                for r in records:
                    try:
                        ts_str = r.get("timestamp", "")
                        ts_str = ts_str.replace("Z", "").replace("+00:00", "")
                        if datetime.fromisoformat(ts_str) > cutoff:
                            filtered_records.append(r)
                    except Exception:
                        filtered_records.append(r)

            st.caption(f"该范围内共 {len(filtered_records)} 条记录")

        # ★ 开始总结按钮
        if st.button("🧠 开始总结薄弱知识点"):
            if not filtered_records:
                st.warning("请至少选择一条记录！")
            else:
                # 拼接文本（带作业名称，方便 AI 理解上下文）
                texts = []
                for r in filtered_records[:20]:
                    t = r.get("title") or "未命名"
                    texts.append(f"## 作业：{t}\n{r.get('result_text', '')}")
                all_text = "\n\n---\n\n".join(texts)
                if len(all_text) > 15000:
                    all_text = all_text[:15000] + "\n\n...(内容过多，已截断)"

                st.info(f"正在分析 {len(filtered_records)} 条记录...")

                with st.spinner("AI 正在总结你的薄弱知识点..."):
                    try:
                        client = OpenAI(
                            api_key=st.secrets["THIRD_API_KEY"],
                            base_url=st.secrets["THIRD_BASE_URL"]
                        )
                        resp = client.chat.completions.create(
                            model=st.secrets["THIRD_MODEL"],
                            messages=[
                                {
                                    "role": "system",
                                    "content": "你是一位经验丰富的高中数学教师，擅长从学生的多次作业中分析薄弱环节并给出针对性建议。"
                                },
                                {
                                    "role": "user",
                                    "content": (
                                        "以下是一位学生的多次数学作业批改记录，"
                                        "请总结出 3~6 个最需要补强的知识点，每个包含：\n"
                                        "1. **知识点名称**\n"
                                        "2. **薄弱原因分析**（结合具体错题说明）\n"
                                        "3. **改进建议**\n"
                                        "4. **推荐练习方向**\n\n"
                                        f"{all_text}"
                                    )
                                }
                            ],
                            max_tokens=30000,
                            temperature=0.7
                        )
                        summary_result = resp.choices[0].message.content
                        st.markdown(summary_result)
                        st.download_button(
                            "📥 下载总结报告",
                            summary_result.encode("utf-8"),
                            "知识漏洞总结.md",
                            mime="text/markdown",
                            key="dl_summary"
                        )
                    except Exception as e:
                        st.error(f"总结失败: {str(e)}")

st.caption("数据永久保存 · by Yuri in Gxu | 使用 n1n.ai")
