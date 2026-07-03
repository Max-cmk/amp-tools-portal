# ============================================================
#  AcousticShift Simulator V6 - Streamlit Edition
#  Excel 직접 입력 + Delta FFT + AMP 효율 관리
# ============================================================

import os, traceback, tempfile
import numpy as np
import streamlit as st
from scipy.io import wavfile
from scipy.interpolate import PchipInterpolator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def _set_mpl_korean_font():
    candidates = ["Malgun Gothic", "맑은 고딕", "AppleGothic", "Apple SD Gothic Neo",
                  "NanumGothic", "NanumBarunGothic", "SamsungReportKorean", "Noto Sans CJK KR"]
    available = {f.name for f in fm.fontManager.ttflist}
    for name in candidates:
        if name in available:
            matplotlib.rcParams["font.family"] = name
            break
    matplotlib.rcParams["axes.unicode_minus"] = False

_set_mpl_korean_font()

from scipy.signal import welch

APP_NAME    = "AcousticShift Simulator"
APP_VERSION = "V6 Streamlit"

DEFAULT_FREQ = [100, 106, 112, 118, 125, 132, 140, 150, 160, 170, 180, 190, 200, 212, 224, 236,
    250, 265, 280, 300, 315, 335, 355, 375, 400, 425, 450, 475, 500, 530, 560, 600,
    630, 670, 710, 750, 800, 850, 900, 950, 1000, 1060, 1120, 1180, 1250, 1320, 1400,
    1500, 1600, 1700, 1800, 1900, 2000, 2120, 2240, 2360, 2500, 2650, 2800, 3000, 3150,
    3350, 3550, 3750, 4000, 4250, 4500, 4750, 5000, 5300, 5600, 6000, 6300, 6700, 7100,
    7500, 8000, 8500, 9000, 9500, 10000, 10600, 11200, 11800, 12500, 13200, 14000,
    15000, 16000, 17000, 18000, 19000, 20000]

DEFAULT_AMP_CURVES = {
    "TI_Custom_VI(SN012578)": {
        "breakpoints": [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 7.0],
        "efficiencies": [39.31, 72.66, 81.72, 89.04, 89.32, 87.87, 84.19],
    },
    "VI_GEN2": {
        "breakpoints": [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 7.0],
        "efficiencies": [39.0, 69.0, 78.0, 89.0, 91.0, 85.0, 81.0],
    },
    "Goodix_Custom_VI(TFA9866)": {
        "breakpoints": [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 7.0],
        "efficiencies": [49.0, 78.0, 85.0, 89.0, 92.0, 86.0, 80.0],
    },
    "Awinic_Custom_VI(AW88461)": {
        "breakpoints": [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 7.0],
        "efficiencies": [39.0, 71.0, 80.0, 89.0, 93.0, 85.0, 80.0],
    },
}

AMP_CURVES = DEFAULT_AMP_CURVES.copy()

def read_wav_float(path):
    """WAV 파일을 float64로 읽고 [-1, 1] 범위로 정규화"""
    fs, data = wavfile.read(path)
    
    # 데이터 타입별 정규화
    if data.dtype == np.int16:
        x = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        x = data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.uint8:
        x = (data.astype(np.float64) - 128) / 128.0
    elif data.dtype in [np.float32, np.float64]:
        x = data.astype(np.float64)
        # float 데이터가 [-1, 1] 범위 벗어나면 정규화
        peak = np.max(np.abs(x))
        if peak > 1.0:
            x = x / peak
    else:
        x = data.astype(np.float64)
    
    # 1차원이면 2차원으로 변환
    return fs, x.reshape(-1, 1) if x.ndim == 1 else x

def write_wav_float(path, fs, x):
    if x.ndim == 1: x = x.reshape(-1, 1)
    peak = np.max(np.abs(x))
    if peak > 0.999:
        x = x * (0.999 / peak)
    data_int16 = np.clip(x * 32767, -32768, 32767).astype(np.int16)
    wavfile.write(path, fs, data_int16 if data_int16.ndim > 1 else data_int16.flatten())

def matlab_exact_gain(freq_ref, delta_db, fs, N):
    """Delta FFT Gain 계산"""
    f_pos = np.fft.fftfreq(N, 1.0 / fs)[:N // 2]
    interp_func = PchipInterpolator(freq_ref, delta_db)
    delta_interp = interp_func(f_pos)
    gain_pos = 10.0 ** (delta_interp / 20.0)
    gain = np.ones(N, dtype=np.complex128)
    gain[:N // 2] = gain_pos
    gain[N // 2:] = gain_pos[::-1] if N % 2 == 0 else gain_pos[-2::-1]
    return gain, f_pos, delta_interp, gain_pos

def calculate_current_ma(wav_data, fs, amp_name, dcr_l, r_pcb, avg_start, avg_end):
    """
    전류 계산 (원본과 동일한 Power 기반 방식)
    """
    if wav_data.ndim == 2:
        wav_data = wav_data[:, 0]
    
    # 0.5ms 블록 단위로 RMS 계산
    windowsamples = max(1, int(round(fs * 0.5e-3)))
    usable = wav_data.shape[0] - (wav_data.shape[0] % windowsamples)
    
    if usable < windowsamples:
        return np.nan
    
    x_left = wav_data[:usable]
    blocks = x_left.reshape((-1, windowsamples)).T
    rms_lin = np.sqrt(np.mean(blocks ** 2, axis=0))
    
    # V_RMS 계산 (dB)
    rms_db = 20.0 * np.log10(np.maximum(rms_lin, np.finfo(float).tiny))
    vrms = 14.2 * 10.0 ** ((rms_db + 2.0) / 20.0)
    
    # V_RMS > 0.01인 첫 번째 시점 찾기 (신호 시작점)
    above = np.where(vrms > 0.01)[0]
    if above.size == 0:
        return np.nan
    
    time_A = float(above[0]) * 0.5e-3
    time = np.arange(blocks.shape[1], dtype=float) * 0.5e-3
    
    # time_A + avg_start ~ time_A + avg_end 구간에서 유효한 샘플 찾기
    valid = (time >= time_A + avg_start) & (time <= time_A + avg_end)
    if not np.any(valid):
        return np.nan
    
    # ✅ 원본과 동일: Power 기반 계산
    # Power = V_RMS^2 / DCR + (V_RMS / DCR)^2 * R_PCB
    power_l = vrms[valid] ** 2 / dcr_l + (vrms[valid] / dcr_l) ** 2 * r_pcb
    
    # AMP 곡선에서 효율 조회 (Breakpoints 기반)
    if amp_name not in st.session_state.amp_curves:
        effs_norm = np.ones_like(power_l) * 0.85
    else:
        amp_data = st.session_state.amp_curves[amp_name]
        bps = np.array(amp_data["breakpoints"], dtype=float)
        effs = np.array(amp_data["efficiencies"], dtype=float) / 100.0
        effs_norm = np.interp(power_l, bps, effs, left=effs[0], right=effs[-1])
    
    # 입력 전력 계산
    power_in = power_l / np.maximum(effs_norm, 1e-9)
    avg_pin = float(np.mean(power_in))
    
    # 전류 계산 (원본과 동일)
    current_ma = avg_pin / 4.0 * 1000.0 + 1.0
    
    return current_ma

def safe_float(s):
    try:
        return float(str(s).strip())
    except (ValueError, AttributeError):
        return None

def count_numeric(txt):
    return sum(1 for line in str(txt).strip().split("\n") if safe_float(line) is not None)

st.set_page_config(page_title=APP_NAME, page_icon="🎵", layout="wide", initial_sidebar_state="expanded")

st.markdown("""<style>
:root { color-scheme: dark; }
body { background-color: #0d1117; color: #c9d1d9; }
.stApp { background-color: #0d1117; }
.stMetric { background-color: #161b22; padding: 15px; border-radius: 6px; border: 1px solid #30363d; }
h1, h2, h3, h4, h5, h6 { color: #c9d1d9; }
.stButton > button { background-color: #238636; color: #fff; border: 1px solid #238636; }
.stButton > button:hover { background-color: #2ea043; }
.stTabs > div > div > button { color: #8b949e; }
.stTabs > div > div > button[aria-selected="true"] { color: #58a6ff; border-bottom: 2px solid #58a6ff; }
</style>""", unsafe_allow_html=True)

if "wav_data" not in st.session_state:
    st.session_state.wav_data = None
    st.session_state.results = None
    st.session_state.debug_log = ""
    st.session_state.amp_curves = AMP_CURVES.copy()
    st.session_state.amp_input = list(AMP_CURVES.keys())[0]
    st.session_state.amp_output = list(AMP_CURVES.keys())[0]

st.title(f"🎵 {APP_NAME} {APP_VERSION}")

with st.sidebar:
    st.header("⚙️ 설정")
    st.subheader("1️⃣ 입력 파일")
    wav_file = st.file_uploader("WAV 파일 선택", type=["wav"])
    if wav_file:
        st.session_state.wav_data = wav_file.read()
        st.success("✅ WAV 파일 로드됨")
    
    st.subheader("2️⃣ 처리 매개변수")
    col1, col2 = st.columns(2)
    with col1:
        dcr_l = st.number_input("DCR (Ω)", value=6.0, step=0.1)
    with col2:
        r_pcb = st.number_input("PCB R (Ω)", value=0.0, step=0.1)
    
    col1, col2 = st.columns(2)
    with col1:
        avg_start = st.number_input("시작 시간 (s)", value=10.0, step=0.5)
    with col2:
        avg_end = st.number_input("종료 시간 (s)", value=130.0, step=0.5)
    
    st.subheader("3️⃣ AMP 효율 설정")
    
    st.write("**Input WAV 파일 AMP**")
    st.session_state.amp_input = st.selectbox("선택하기", list(st.session_state.amp_curves.keys()), key="amp_in_select")
    
    st.divider()
    
    st.write("**Output WAV 파일 AMP**")
    st.session_state.amp_output = st.selectbox("선택하기", list(st.session_state.amp_curves.keys()), key="amp_out_select")
    
    st.divider()
    
    if st.button("⚙️ AMP 효율 수정", use_container_width=True):
        st.session_state.show_amp_editor = True
    
    if st.session_state.get("show_amp_editor", False):
        st.divider()
        st.write("**AMP 효율 수정**")
        
        # 기존 AMP 수정 또는 새 AMP 추가
        operation = st.radio("작업 선택", ["기존 AMP 수정", "새로운 AMP 추가"], horizontal=True, key="amp_operation")
        
        if operation == "기존 AMP 수정":
            edit_amp_name = st.selectbox("수정할 AMP 선택", list(st.session_state.amp_curves.keys()), key="amp_edit_select")
            current_data = st.session_state.amp_curves[edit_amp_name]
            
            st.write("**Breakpoints (Power)**")
            bps_text = st.text_area("Breakpoints (각 줄에 하나씩)", value="\n".join(str(b) for b in current_data["breakpoints"]), height=100, key="bps_input")
            
            st.write("**Efficiencies (%)**")
            eff_text = st.text_area("Efficiencies (각 줄에 하나씩)", value="\n".join(str(e) for e in current_data["efficiencies"]), height=100, key="eff_input")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 저장", use_container_width=True):
                    try:
                        bps = [float(x.strip()) for x in bps_text.strip().split("\n") if x.strip()]
                        effs = [float(x.strip()) for x in eff_text.strip().split("\n") if x.strip()]
                        if len(bps) != len(effs):
                            st.error("❌ 개수 불일치")
                        elif len(bps) < 2:
                            st.error("❌ 최소 2개 필요")
                        else:
                            st.session_state.amp_curves[edit_amp_name] = {"breakpoints": bps, "efficiencies": effs}
                            st.success("✅ 저장됨")
                    except ValueError:
                        st.error("❌ 숫자 형식 오류")
            
            with col2:
                if st.button("🗑️ 삭제", use_container_width=True):
                    if len(st.session_state.amp_curves) > 1:
                        del st.session_state.amp_curves[edit_amp_name]
                        st.success("✅ 삭제됨")
                        st.rerun()
                    else:
                        st.error("❌ 최소 1개 AMP는 필요합니다")
            
            with col3:
                if st.button("❌ 닫기", use_container_width=True):
                    st.session_state.show_amp_editor = False
                    st.rerun()
        
        else:  # 새로운 AMP 추가
            st.write("**새로운 AMP 이름**")
            new_amp_name = st.text_input("AMP 이름 (예: Custom_AMP_01)", key="new_amp_name")
            
            st.write("**Breakpoints (Power)**")
            new_bps_text = st.text_area("Breakpoints (각 줄에 하나씩)", value="0.01\n0.05\n0.1\n0.5\n1.0", height=80, key="new_bps_input")
            
            st.write("**Efficiencies (%)**")
            new_eff_text = st.text_area("Efficiencies (각 줄에 하나씩)", value="40\n70\n80\n89\n90", height=80, key="new_eff_input")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("➕ 추가", use_container_width=True):
                    if not new_amp_name:
                        st.error("❌ AMP 이름을 입력해주세요")
                    elif new_amp_name in st.session_state.amp_curves:
                        st.error("❌ 이미 존재하는 이름입니다")
                    else:
                        try:
                            bps = [float(x.strip()) for x in new_bps_text.strip().split("\n") if x.strip()]
                            effs = [float(x.strip()) for x in new_eff_text.strip().split("\n") if x.strip()]
                            if len(bps) != len(effs):
                                st.error("❌ 개수 불일치")
                            elif len(bps) < 2:
                                st.error("❌ 최소 2개 필요")
                            else:
                                st.session_state.amp_curves[new_amp_name] = {"breakpoints": bps, "efficiencies": effs}
                                st.success(f"✅ '{new_amp_name}' 추가됨")
                                st.rerun()
                        except ValueError:
                            st.error("❌ 숫자 형식 오류")
            
            with col2:
                if st.button("❌ 닫기", use_container_width=True):
                    st.session_state.show_amp_editor = False
                    st.rerun()

st.subheader("📊 Excel A/B/C 열 직접 입력")

col1, col2, col3, col_buttons = st.columns([0.33, 0.33, 0.33, 0.5])

with col1:
    st.write("**A: Frequency (Hz)**")
    col_a_text = st.text_area("Frequency", value="\n".join(str(f) for f in DEFAULT_FREQ), height=250, label_visibility="collapsed", key="col_a")

with col2:
    st.write("**B: 기존 (dB)**")
    col_b_text = st.text_area("B Value", value="", height=250, label_visibility="collapsed", key="col_b")

with col3:
    st.write("**C: 신규 (dB)**")
    col_c_text = st.text_area("C Value", value="", height=250, label_visibility="collapsed", key="col_c")

ca = count_numeric(col_a_text)
cb = count_numeric(col_b_text)
cc = count_numeric(col_c_text)

with col_buttons:
    st.write("**상태**")
    if ca == cb == cc == 0:
        st.info("입력\n대기")
    elif ca == cb == cc and ca >= 10:
        st.success("✓ OK")
    else:
        st.error("✗ 불\n일치")
    
    st.write("")
    if st.button("🚀\n처리", use_container_width=True, key="btn_process", help="Excel 데이터로 처리 시작"):
        if st.session_state.wav_data is None:
            st.error("❌ WAV 파일을 먼저 로드해주세요")
        elif ca == 0 or cb == 0 or cc == 0:
            st.error("❌ A, B, C 열에 모두 데이터 입력")
        elif ca != cb or cb != cc:
            st.error("❌ 행 수 불일치")
        else:
            with st.spinner("처리 중..."):
                try:
                    a_vals = [safe_float(line) for line in col_a_text.strip().split("\n")]
                    b_vals = [safe_float(line) for line in col_b_text.strip().split("\n")]
                    c_vals = [safe_float(line) for line in col_c_text.strip().split("\n")]
                    
                    a_vals = [v for v in a_vals if v is not None]
                    b_vals = [v for v in b_vals if v is not None]
                    c_vals = [v for v in c_vals if v is not None]
                    
                    freq_ref = np.array(a_vals)
                    delta_db = np.array(b_vals) - np.array(c_vals)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_in:
                        wav_path = tmp_in.name
                        tmp_in.write(st.session_state.wav_data)
                    
                    fs, x = read_wav_float(wav_path)
                    N = x.shape[0]
                    
                    # 디버그: WAV 파일 정보
                    debug_info = f"""
━━━ WAV 파일 정보 ━━━
샘플레이트 (fs): {fs} Hz
데이터 길이: {N} samples ({N/fs:.2f}초)
채널 수: {x.shape[1]}
데이터 타입: {x.dtype}
데이터 범위: [{np.min(x):.6f}, {np.max(x):.6f}]
RMS (전체): {np.sqrt(np.mean(x**2)):.6f}
"""
                    st.write(debug_info)
                    
                    # Delta FFT 적용
                    gain, f_pos, delta_interp, gain_pos = matlab_exact_gain(freq_ref, delta_db, fs, N)
                    y = np.zeros_like(x, dtype=np.float64)
                    for ch in range(x.shape[1]):
                        y[:, ch] = np.real(np.fft.ifft(np.fft.fft(x[:, ch], N) * gain))
                    
                    peak = np.max(np.abs(y)) if y.size else 0
                    clip_norm_db = 0.0
                    if peak > 0.999:
                        scale = 0.999 / peak
                        y *= scale
                        clip_norm_db = 20 * np.log10(scale)
                    
                    # 전류 계산
                    amp_in_name = st.session_state.amp_input
                    amp_out_name = st.session_state.amp_output
                    
                    # 디버그: 전류 계산 상세 정보
                    st.write("### 🔍 전류 계산 디버그")
                    
                    # Input 전류 계산 단계별
                    windowsamples = max(1, int(round(fs * 0.5e-3)))
                    usable = x.shape[0] - (x.shape[0] % windowsamples)
                    x_left = x[:usable, 0]
                    blocks = x_left.reshape((-1, windowsamples)).T
                    rms_lin = np.sqrt(np.mean(blocks ** 2, axis=0))
                    rms_db = 20.0 * np.log10(np.maximum(rms_lin, np.finfo(float).tiny))
                    vrms = 14.2 * 10.0 ** ((rms_db + 2.0) / 20.0)
                    
                    above = np.where(vrms > 0.01)[0]
                    if above.size > 0:
                        time_A = float(above[0]) * 0.5e-3
                        time = np.arange(blocks.shape[1], dtype=float) * 0.5e-3
                        valid = (time >= time_A + avg_start) & (time <= time_A + avg_end)
                        if np.any(valid):
                            avg_rms = np.mean(rms_lin[valid])
                            st.write(f"""
**Input 신호 분석:**
- 블록 크기: {windowsamples} samples ({windowsamples/fs*1000:.2f}ms)
- V_RMS > 0.01 시작점: {time_A:.3f}s
- 유효 구간: [{time_A + avg_start:.3f}s ~ {time_A + avg_end:.3f}s]
- 평균 RMS (선형): {avg_rms:.6f}
- 평균 RMS (dB): {20*np.log10(avg_rms):.2f} dB
""")
                    
                    current_in = calculate_current_ma(x, fs, amp_in_name, dcr_l, r_pcb, avg_start, avg_end)
                    current_out = calculate_current_ma(y, fs, amp_out_name, dcr_l, r_pcb, avg_start, avg_end)
                    
                    st.write(f"""
**계산 결과:**
- Input 전류: {current_in:.2f} mA
- Output 전류: {current_out:.2f} mA
""")
                    
                    if current_in > 100000 or np.isnan(current_in):
                        st.error("⚠️ 입력 전류 값이 비정상적입니다. WAV 파일 형식을 확인하세요.")
                    
                    current_diff = (current_out - current_in if np.isfinite(current_in) and np.isfinite(current_out) else np.nan)
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_out:
                        out_path = tmp_out.name
                    
                    write_wav_float(out_path, fs, y)
                    
                    st.session_state.results = {
                        "freq_ref": freq_ref, "delta_db": delta_db, "f_pos": f_pos,
                        "delta_interp": delta_interp, "gain": gain, "gain_pos": gain_pos,
                        "x_orig": x, "y": y, "fs": fs,
                        "current_in": current_in, "current_out": current_out, 
                        "current_diff": current_diff, "clip_norm_db": clip_norm_db, "output_path": out_path,
                    }
                    
                    log_text = f"""[성공] 처리 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
주파수 범위: {np.min(freq_ref):.0f} ~ {np.max(freq_ref):.0f} Hz
Delta 범위: {np.min(delta_db):.4f} ~ {np.max(delta_db):.4f} dB
Gain 범위: {np.min(gain_pos):.6f} ~ {np.max(gain_pos):.6f}
Clip norm: {clip_norm_db:.4f} dB

DCR: {dcr_l:.3f} Ω  /  PCB R: {r_pcb:.3f} Ω
평균 윈도우: +{avg_start}s ~ +{avg_end}s

Input AMP: {amp_in_name}
Output AMP: {amp_out_name}

기존 전류: {current_in:.1f} mA
Duct반영 전류: {current_out:.1f} mA
차이: {current_diff:.1f} mA"""
                    st.session_state.debug_log = log_text
                    
                    st.success("✅ 처리 완료!")
                    
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                    
                except Exception as e:
                    st.error(f"❌ 처리 실패: {e}")
                    st.session_state.debug_log = traceback.format_exc()
    
    st.write("")
    if st.button("🗑️\n초기화", use_container_width=True, key="btn_reset"):
        st.session_state.wav_data = None
        st.session_state.results = None
        st.session_state.debug_log = ""
        st.rerun()

st.divider()

# 처리 결과 표시
if st.session_state.results:
    res = st.session_state.results
    
    st.markdown("### 📊 Current Result")
    
    # Current Result 테이블
    result_data = {
        "기존": f"{res['current_in']:.1f}" if np.isfinite(res['current_in']) else "-",
        "Duct반영": f"{res['current_out']:.1f}" if np.isfinite(res['current_out']) else "-",
        "차이": f"{res['current_diff']:.1f}" if np.isfinite(res['current_diff']) else "-",
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div style='background-color: #161b22; padding: 20px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 14px; font-weight: bold;'>기존</span><br><span style='color: #58a6ff; font-size: 24px; font-weight: bold;'>{result_data['기존']} mA</span></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div style='background-color: #161b22; padding: 20px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 14px; font-weight: bold;'>Duct반영</span><br><span style='color: #58a6ff; font-size: 24px; font-weight: bold;'>{result_data['Duct반영']} mA</span></div>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<div style='background-color: #161b22; padding: 20px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 14px; font-weight: bold;'>차이</span><br><span style='color: #58a6ff; font-size: 24px; font-weight: bold;'>{result_data['차이']} mA</span></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # Reference 실제 전류 기반 예상
    st.markdown("### 📈 Reference 실제 전류 기반 예상")
    
    ref_col1, ref_col2, ref_col3, ref_col4 = st.columns([1.2, 0.8, 0.8, 0.8])
    
    with ref_col1:
        st.markdown("<span style='color: #8b949e; font-size: 13px; font-weight: bold;'>Reference 실제 전류 (mA)</span>", unsafe_allow_html=True)
        ref_current = st.number_input("Reference 전류", value=50.0, step=0.1, label_visibility="collapsed", key="ref_current")
    
    # 예상 전류 계산
    if np.isfinite(res['current_in']) and np.isfinite(res['current_out']):
        ratio_out = res['current_out'] / res['current_in'] if res['current_in'] != 0 else 1.0
        expected_in = ref_current
        expected_out = ref_current * ratio_out
        expected_diff = expected_out - expected_in
    else:
        expected_in = np.nan
        expected_out = np.nan
        expected_diff = np.nan
    
    with ref_col2:
        st.markdown(f"<div style='background-color: #161b22; padding: 15px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 12px; font-weight: bold;'>예상 기존</span><br><span style='color: #d29922; font-size: 20px; font-weight: bold;'>{expected_in:.1f}</span></div>", unsafe_allow_html=True)
    with ref_col3:
        st.markdown(f"<div style='background-color: #161b22; padding: 15px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 12px; font-weight: bold;'>예상 Duct</span><br><span style='color: #d29922; font-size: 20px; font-weight: bold;'>{expected_out:.1f}</span></div>", unsafe_allow_html=True)
    with ref_col4:
        st.markdown(f"<div style='background-color: #161b22; padding: 15px; border-radius: 6px; text-align: center; border: 2px solid #30363d;'><span style='color: #8b949e; font-size: 12px; font-weight: bold;'>예상 차이</span><br><span style='color: #d29922; font-size: 20px; font-weight: bold;'>{expected_diff:.1f}</span></div>", unsafe_allow_html=True)
    
    st.divider()
    
    # 다운로드 버튼
    with open(res['output_path'], "rb") as f:
        st.download_button("📥 Output WAV 다운로드", f.read(), "output.wav", "audio/wav", use_container_width=False)

st.divider()

tabs = st.tabs(["📈 결과 그래프", "🔍 디버그"])

with tabs[0]:
    if st.session_state.results:
        res = st.session_state.results
        
        fig, axes = plt.subplots(2, 1, figsize=(14, 10))
        fig.patch.set_facecolor("#0d1117")
        
        # Excel Delta 곡선
        ax = axes[0]
        ax.semilogx(res["freq_ref"], res["delta_db"], "o", color="#58a6ff", markersize=4, label="Delta (B-C)")
        ax.axhline(0, color="#30363d", linewidth=0.6, alpha=0.5)
        ax.set_title("Excel Delta Curve (B - C)", color="#c9d1d9", fontsize=11, fontweight="bold")
        ax.set_xlabel("Frequency (Hz)", color="#8b949e")
        ax.set_ylabel("Delta (dB)", color="#8b949e")
        ax.set_xlim(100, 20000)
        ax.grid(True, which="both", alpha=0.2, color="#30363d")
        ax.legend(loc="best", labelcolor="#000000")
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        
        # Input/Output FFT 비교
        ax = axes[1]
        nfft = min(4096, res["x_orig"].shape[0])
        _f, p_in = welch(res["x_orig"][:, 0], fs=res["fs"], window="hamming", nperseg=nfft, noverlap=nfft // 2, nfft=nfft)
        _f, p_out = welch(res["y"][:, 0], fs=res["fs"], window="hamming", nperseg=nfft, noverlap=nfft // 2, nfft=nfft)
        eps = np.finfo(float).eps
        ax.semilogx(_f, 10*np.log10(p_in + eps), color="#f85149", linewidth=1.2, label="Input (원본)")
        ax.semilogx(_f, 10*np.log10(p_out + eps), color="#58a6ff", linewidth=1.2, label="Output (Delta FFT)")
        ax.set_title("Input / Output WAV FFT", color="#c9d1d9", fontsize=11, fontweight="bold")
        ax.set_xlabel("Frequency (Hz)", color="#8b949e")
        ax.set_ylabel("Magnitude (dB)", color="#8b949e")
        ax.set_xlim(100, 20000)
        ax.grid(True, which="both", alpha=0.2, color="#30363d")
        ax.legend(loc="best", labelcolor="#000000", fontsize=9)
        ax.set_facecolor("#161b22")
        ax.tick_params(colors="#8b949e")
        
        plt.tight_layout(pad=2.0)
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("💡 처리를 완료한 후 결과 그래프를 볼 수 있습니다")

with tabs[1]:
    if st.session_state.debug_log:
        st.text_area("디버그 로그", value=st.session_state.debug_log, height=400, disabled=True)
    else:
        st.info("💡 처리 후 디버그 정보가 표시됩니다")