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

# ★ 关键修复1：用 service_key 创建一个专门操作数据库的客户端（绕过 RLS）
# Streamlit 是服务端运行，service_key 不会暴露给用户，安全可行
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

    # ==================== 上传分析 ====================
    uploaded_file = st.file_uploader("上传作业照片", type=["jpg", "png"])

    # ★ 改进：上传后显示预览
    if uploaded_file:
        st.image(uploaded_file, caption="📷 图片预览", width=400)

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
                    max_tokens=30000,
                    temperature=0.7
                )

                result = response.choices[0].message.content

                # ★ 关键修复2：用 db_client 写入
                db_client.table("analyses").insert({
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
    st.markdown("---")
    st.markdown("### 📜 我的历史批改记录")

    # ★ 关键修复3：用 db_client 读取，并加 try/except
    try:
        records = db_client.table("analyses") \
            .select("*") \
            .eq("user_id", str(user.id)) \
            .order("timestamp", desc=True) \
            .execute().data
    except Exception as e:
        st.error(f"读取历史记录失败: {str(e)}")
        records = []

    # ★ 改进：显示记录数量
    st.caption(f"共 {len(records)} 条记录")

    if records:
        for i, r in enumerate(records):
            # ★ 改进：更友好的时间显示 + 防止 key 冲突
            ts = r.get('timestamp', '未知时间')[:16].replace("T", " ")
            with st.expander(f"📅 {ts} 的批改记录", expanded=(i == 0)):
                st.markdown(r.get("result_text", "内容为空"))
    else:
        st.info("还没有批改记录，快上传第一张作业吧～")

    # ==================== 总结薄弱点 ====================
    st.markdown("---")
    st.markdown("### 🔍 总结我的知识漏洞")

    time_range = st.selectbox(
        "选择总结范围",
        ["全部记录", "最近7天", "最近30天", "最近90天"],
        index=0
    )

    if st.button("开始总结薄弱知识点"):
        if not records:
            st.warning("没有任何历史记录，请先上传作业")
        else:
            # ★ 改进：时间过滤更健壮
            if time_range == "全部记录":
                filtered_records = records
            else:
                days = {"最近7天": 7, "最近30天": 30, "最近90天": 90}[time_range]
                cutoff = datetime.utcnow() - timedelta(days=days)
                filtered_records = []
                for r in records:
                    try:
                        ts_str = r.get("timestamp", "")
                        # 处理多种时间格式
                        ts_str = ts_str.replace("Z", "").replace("+00:00", "")
                        record_time = datetime.fromisoformat(ts_str)
                        if record_time > cutoff:
                            filtered_records.append(r)
                    except Exception:
                        filtered_records.append(r)  # 解析失败就包含进来

            if filtered_records:
                st.info(f"正在分析 {len(filtered_records)} 条记录...")

                # ★ 改进：按记录数截断而非字符数暴力截断
                texts = [r.get("result_text", "") for r in filtered_records[:20]]  # 最多取20条
                all_text = "\n\n---\n\n".join(texts)
                if len(all_text) > 15000:
                    all_text = all_text[:15000] + "\n...(已截断)"

                with st.spinner("AI正在分析你的所有记录..."):
                    try:
                        client = OpenAI(
                            api_key=st.secrets["THIRD_API_KEY"],
                            base_url=st.secrets["THIRD_BASE_URL"]
                        )
                        resp = client.chat.completions.create(
                            model=st.secrets["THIRD_MODEL"],
                            messages=[
                                {"role": "system", "content": "你是一位经验丰富的高中数学教师，擅长分析学生的薄弱环节。"},
                                {"role": "user", "content": f"以下是一位学生的多次数学作业批改记录，请总结出最需要补强的知识点（3-6个），每个包含：知识点名称、薄弱原因分析、具体改进建议和推荐练习方向。\n\n{all_text}"}
                            ],
                            max_tokens=30000,
                            temperature=0.7
                        )
                        st.markdown(resp.choices[0].message.content)
                    except Exception as e:
                        st.error(f"AI分析失败: {str(e)}")
            else:
                st.warning("该时间范围内没有记录")

st.caption("数据永久保存 · by Yuri in Gxu | 使用 n1n.ai")
