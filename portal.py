"""
AMP Tools Portal - 고급 포탈 시스템
- 카드 기반 UI로 모든 Tool 표시
- 각 Tool 클릭 시 설명/가이드 모달 표시
- 실행 버튼으로 Tool 실행
- 각 Tool 내부에서 뒤로가기로 포탈 홈으로 복귀
- 포탈에서 Tool 설명 수정 가능
"""

import streamlit as st
import json
from pathlib import Path
from core.loader import load_tool

st.set_page_config(
    page_title="AMP Tools Portal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

TOOLS_DIR = Path("./tools")
META_FILE = Path("./tool_meta.json")

# ============== 헬퍼 함수 ==============
def load_meta():
    if META_FILE.exists():
        return json.loads(META_FILE.read_text(encoding='utf-8'))
    return {}

def save_meta(m):
    META_FILE.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding='utf-8')  # ← encoding 추가!

# ============== 세션 상태 초기화 ==============
if "page" not in st.session_state:
    st.session_state.page = "home"
if "tool" not in st.session_state:
    st.session_state.tool = None
if "editing_tool" not in st.session_state:
    st.session_state.editing_tool = None
if "show_edit_modal" not in st.session_state:
    st.session_state.show_edit_modal = False

meta = load_meta()

# ============== 스타일 ==============
st.markdown("""
<style>
    /* 전체 배경 */
    .main {
        background: linear-gradient(135deg, #0f1419 0%, #161b22 100%);
    }
    
    /* 포탈 제목 */
    .portal-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 1rem;
        letter-spacing: -0.5px;
    }
    
    /* 서브타이틀 */
    .portal-subtitle {
        font-size: 1.2rem;
        color: #8b949e;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    /* 카드 컨테이너 */
    .card-container {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1.5rem;
        margin-bottom: 2rem;
    }
    
    /* 카드 */
    .tool-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 2px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }
    
    .tool-card:hover {
        border-color: #58a6ff;
        box-shadow: 0 8px 24px rgba(88, 166, 255, 0.2);
        transform: translateY(-4px);
    }
    
    /* 카드 아이콘 */
    .card-icon {
        font-size: 3rem;
        margin-bottom: 0.75rem;
        text-align: center;
    }
    
    /* 카드 제목 */
    .card-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #e6edf3;
        margin-bottom: 0.5rem;
        text-align: center;
    }
    
    /* 카드 설명 */
    .card-desc {
        font-size: 0.95rem;
        color: #8b949e;
        text-align: center;
        line-height: 1.5;
        min-height: 2.5rem;
        margin-bottom: 1rem;
    }
    
    /* 버튼 그룹 */
    .button-group {
        display: flex;
        gap: 0.5rem;
        margin-top: 1rem;
    }
    
    /* 뒤로가기 버튼 */
    .back-button {
        background: linear-gradient(135deg, #21262d 0%, #161b22 100%);
        border: 1px solid #30363d;
        color: #58a6ff;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s;
    }
    
    .back-button:hover {
        background: #30363d;
        border-color: #58a6ff;
    }
    
    /* 모달 배경 */
    .modal-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.7);
        z-index: 100;
    }
    
    /* 모달 */
    .modal {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 2rem;
        max-width: 600px;
        margin: auto;
    }
    
    /* 관리자 섹션 */
    .admin-section {
        background: linear-gradient(135deg, rgba(88, 166, 255, 0.1) 0%, rgba(79, 195, 247, 0.1) 100%);
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 2rem;
    }
    
    .admin-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #58a6ff;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============== 홈 페이지 ==============
def home():
    # 제목
    st.markdown('<div class="portal-title">🧰 AMP Tools Portal</div>', unsafe_allow_html=True)
    st.markdown('<div class="portal-subtitle">모든 도구에 한 곳에서 접근하세요</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # 도구 카드 그리드
    if meta:
        cols = st.columns(min(3, len(meta)))
        for idx, (name, m) in enumerate(meta.items()):
            with cols[idx % len(cols)]:
                # 클릭 가능한 카드
                st.markdown(f'''
                <div class="tool-card" 
                     style="border: 2px solid #{'58a6ff' if st.session_state.tool == name else '30363d'};">
                    <div class="card-icon">{m.get("icon", "🧩")}</div>
                    <div class="card-title">{m.get("title", name)}</div>
                    <div class="card-desc">{m.get("desc", "설명이 아직 없습니다.")}</div>
                </div>
                ''', unsafe_allow_html=True)
                
                # 버튼 그룹
                btn_col1, btn_col2 = st.columns([1, 1])
                
                with btn_col1:
                    if st.button("ℹ️ 정보", key=f"info_{name}", use_container_width=True):
                        st.session_state.editing_tool = name
                        st.session_state.show_edit_modal = True
                        st.rerun()
                
                with btn_col2:
                    if st.button("▶ 실행", key=f"run_{name}", use_container_width=True):
                        st.session_state.tool = name
                        st.session_state.page = "run"
                        st.rerun()
    else:
        st.info("등록된 도구가 없습니다. 관리자 섹션에서 도구를 추가해주세요.")
    
    # ============== 관리자 섹션 ==============
    st.divider()
    
    with st.expander("⚙️ 관리자 설정", expanded=False):
        st.markdown("### 도구 설명 수정")
        
        if meta:
            selected_tool = st.selectbox("수정할 도구 선택", list(meta.keys()))
            
            if selected_tool:
                current_desc = meta[selected_tool].get("desc", "")
                new_desc = st.text_area(
                    "설명",
                    value=current_desc,
                    height=120,
                    key=f"edit_desc_{selected_tool}"
                )
                
                if st.button("💾 설명 저장", key=f"save_desc_{selected_tool}", use_container_width=True):
                    meta[selected_tool]["desc"] = new_desc
                    save_meta(meta)
                    st.success("✅ 설명이 저장되었습니다!")
                    st.rerun()
        
        st.divider()
        st.markdown("### 도구 추가")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            uploaded = st.file_uploader("Python 파일 선택", type=["py"], label_visibility="collapsed")
        
        with col2:
            pass
        
        tool_key = st.text_input("도구 키 (영문, 언더스코어)", placeholder="my_tool")
        tool_icon = st.text_input("아이콘 (이모지)", value="🧩")
        tool_title = st.text_input("도구 이름", placeholder="My Tool")
        tool_desc = st.text_area("설명", placeholder="도구 설명을 입력하세요", height=80)
        
        if uploaded and tool_key:
            if st.button("➕ 도구 추가", use_container_width=True):
                file_path = TOOLS_DIR / f"{tool_key}.py"
                file_path.write_bytes(uploaded.getvalue())
                
                meta[tool_key] = {
                    "icon": tool_icon,
                    "title": tool_title or tool_key,
                    "desc": tool_desc,
                    "file": f"{tool_key}.py"
                }
                
                save_meta(meta)
                st.success("✅ 도구가 추가되었습니다!")
                st.rerun()

# ============== 도구 실행 페이지 ==============
def run():
    name = st.session_state.tool
    if name not in meta:
        st.error("❌ 도구를 찾을 수 없습니다")
        return
    
    # 뒤로가기 버튼
    st.markdown(f"""
    <div style="margin-bottom: 1rem;">
        <button style="
            background: linear-gradient(135deg, #21262d 0%, #161b22 100%);
            border: 1px solid #30363d;
            color: #58a6ff;
            padding: 0.5rem 1.5rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            font-size: 1rem;
        " onclick="window.history.back()">⬅ 포탈로 돌아가기</button>
    </div>
    """, unsafe_allow_html=True)
    
    # 간단한 버튼으로도 제공
    col1, col2, col3 = st.columns([1, 1, 8])
    with col1:
        if st.button("⬅ 돌아가기", use_container_width=True):
            st.session_state.page = "home"
            st.session_state.tool = None
            st.rerun()
    
    st.divider()
    
    # 도구 정보 표시
    m = meta[name]
    st.markdown(f"### {m.get('icon', '🧩')} {m.get('title', name)}")
    
    st.divider()
    
    # 도구 실행
    try:
        module = load_tool(name, TOOLS_DIR / m["file"])
        if hasattr(module, 'main'):
            module.main()
        else:
            st.error("❌ 도구에 main() 함수가 없습니다")
    except Exception as e:
        st.error(f"❌ 도구 실행 중 오류 발생: {str(e)}")

# ============== 페이지 라우팅 ==============
if st.session_state.page == "home":
    home()
else:
    run()
