import streamlit as st
import google.generativeai as genai
from PIL import Image
from datetime import datetime

st.set_page_config(page_title="Yuri的数学AI", page_icon="🧚", layout="wide", initial_sidebar_state="expanded")

# ================ 超可爱粉色风格 ================
st.markdown("""
<style>
    .big-title {font-size: 48px !important; font-weight: bold; background: linear-gradient(90deg, #FF69B4, #00BFFF); -webkit-background-clip: text; -webkit-text-fill-color: transparent;}
    .stButton>button {background-color: #FF69B4 !important; color: white !important; font-size: 22px; height: 70px; border-radius: 20px;}
    .history {background-color: #FFF0F5; padding: 10px; border-radius: 15px;}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="big-title">🧚‍♀️ Yuri的数学作业AI ✨</h1>', unsafe_allow_html=True)
st.markdown("**📸 拍一张作业 → AI秒批改+超详细讲解+打分+可爱鼓励** ❤️ by Yuri in Gxu")

with st.sidebar:
    st.image("https://img.icons8.com/emoji/100/000000/fairy.png")
    st.success("✅ API已隐藏 · 同学直接用！")
    st.caption("🧚 by Yuri in Gxu ❤️")
    
    # ==================== 历史记录（新增） ====================
    if 'history' not in st.session_state:
        st.session_state.history = []
    
    with st.expander("📜 查看历史批改记录（点击展开）", expanded=True):
        if st.session_state.history:
            for i, item in enumerate(st.session_state.history[::-1]):
                st.markdown(f"**{item['time']}** 第{i+1}次")
                st.write(item['preview'][:80] + "..." if len(item['preview']) > 80 else item['preview'])
                if st.button(f"🔄 恢复第{i+1}次", key=f"load{i}"):
                    st.success("已恢复！（下方会显示）")
                    st.session_state.current_result = item['full']
        else:
            st.info("还没有记录哦～第一次分析后就会自动保存啦💕")

# 主界面
col1, col2 = st.columns([3, 1])
with col1:
    uploaded_file = st.file_uploader("📸 快拍作业照片上传吧～（手机拍照超方便）", type=["jpg", "jpeg", "png"])

if uploaded_file:
    colA, colB = st.columns([2, 1])
    with colA:
        st.image(uploaded_file, caption="🌟 你的作业小可爱已上传", use_column_width=True)
    with colB:
        st.markdown("### 🧚 AI小精灵准备好了！")
        if st.button("🚀 让AI小精灵开始批改啦～ 💖", type="primary", use_container_width=True):
            with st.spinner("🧚 小精灵正在飞来飞去认真批改中...（10-30秒）"):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    response = model.generate_content([
                        "你是超级温柔可爱的高中数学小精灵老师！用超级可爱的Markdown格式回复：🌟1.识别题目 2.正确答案 3.哪里错啦 4.超详细一步一步讲解（加表情）5.打分/100 6.暖心鼓励+小建议。最后加一堆❤️✨🌈",
                        {"mime_type": "image/jpeg", "data": uploaded_file.getvalue()}
                    ])
                    result = response.text

                    # 保存历史（新增）
                    preview = result[:100].replace("\n", " ")
                    st.session_state.history.append({
                        "time": datetime.now().strftime("%H:%M"),
                        "preview": preview,
                        "full": result
                    })
                    if len(st.session_state.history) > 10:  # 只保留最近10条
                        st.session_state.history.pop(0)

                    st.balloons()
                    st.success("🎉 小精灵批改完成啦！快夸夸你自己～")
                    st.markdown(result)
                    
                    # ==================== 修复乱码下载 ====================
                    st.download_button(
                        label="📥 下载批改报告（发给老师/自己保存）",
                        data=result.encode('utf-8'),
                        file_name="Yuri_AI_数学作业分析.md",
                        mime="text/markdown;charset=utf-8"
                    )

                except Exception as e:
                    st.error(f"小精灵迷路了～ {str(e)}")

# 最底部可爱区
st.divider()
colX, colY, colZ = st.columns(3)
with colX:
    st.button("💌 分享给同学（复制链接）", use_container_width=True)
    st.code("https://你的网址.streamlit.app", language=None)
with colY:
    if st.button("🌟 给Yuri打Call（点我）", use_container_width=True):
        st.snow()
        st.success("❤️ 谢谢你！Yuri开心～")
with colZ:
    st.markdown("**🧚 by Yuri in Gxu**  · 03/22/26")

st.caption("💡 小贴士：手机用户建议横屏 + 长按拍照上传更方便 | 历史记录自动保存，只在本次会话有效")
