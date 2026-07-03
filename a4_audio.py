"""
A4 Audio Analysis - Streamlit Portal (Complete Fixed Version)
- Reset ALL: 파일 유지
- Segment 선택: 안정적 동작
- Time Domain: 파일/구간 변경 시 자동 초기화
- Custom Range Segment: 사용자 입력 시간을 segment로 저장 가능
"""

import streamlit as st
import numpy as np
import math
import wave
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
import io
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd
import json

plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

THRESHOLD_RMS = 0.01
MUTE_MIN_SECONDS = 1.0
MAX_SEGMENTS = 20
EPS = 1e-15
RMS_HOP_MS = 1.0

DEFAULT_BREAKPOINTS = [0.01, 0.05, 0.1, 0.5, 1.0, 3.0, 7.0]
DEFAULT_EFFICIENCIES = {
    "TI_Custom_VI(SN012578)": [39.31, 72.66, 81.72, 89.04, 89.32, 87.87, 84.19],
    "VI_GEN2": [39.0, 69.0, 78.0, 89.0, 91.0, 85.0, 81.0],
    "Goodix_Custom_VI(TFA9866)": [49.0, 78.0, 85.0, 89.0, 92.0, 86.0, 80.0],
    "Awinic_Custom_VI(AW88461)": [39.0, 71.0, 80.0, 89.0, 93.0, 85.0, 80.0],
}

@dataclass
class AudioData:
    sample_rate: int
    data: np.ndarray
    sampwidth: int
    nchannels: int

    @property
    def duration(self) -> float:
        return len(self.data) / self.sample_rate if self.sample_rate else 0.0

@dataclass
class Segment:
    name: str
    start_s: float
    end_s: float

@dataclass
class Stats:
    peak_dbfs: float
    max_rms_dbfs: float
    avg_rms_dbfs: float

# ═══════════════════════════════════════════════════════════════════════════════
# Audio Functions
# ═══════════════════════════════════════════════════════════════════════════════

def read_wav(data_bytes: bytes) -> AudioData:
    with io.BytesIO(data_bytes) as wf_io:
        with wave.open(wf_io, "rb") as wf:
            nchannels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            sample_rate = wf.getframerate()
            nframes = wf.getnframes()
            raw = wf.readframes(nframes)

    if nchannels not in (1, 2):
        raise ValueError("Mono or Stereo only")

    if sampwidth == 1:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float64)
        arr = (arr - 128.0) / 128.0
    elif sampwidth == 2:
        arr = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        vals = b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16)
        vals = np.where(vals & 0x800000, vals - 0x1000000, vals)
        arr = vals.astype(np.float64) / 8388608.0
    elif sampwidth == 4:
        arr = np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported: {sampwidth * 8} bit")

    arr = arr.reshape(-1, nchannels)
    return AudioData(sample_rate, arr, sampwidth, nchannels)

def write_wav(audio: AudioData, data: np.ndarray) -> bytes:
    with io.BytesIO() as wf_io:
        with wave.open(wf_io, "wb") as wf:
            wf.setnchannels(audio.nchannels)
            wf.setsampwidth(audio.sampwidth)
            wf.setframerate(audio.sample_rate)
            x = np.clip(data, -1.0, 1.0)
            if audio.sampwidth == 2:
                pcm = np.clip(x * 32767.0, -32768, 32767).astype("<i2").tobytes()
            elif audio.sampwidth == 1:
                pcm = np.clip(x * 127.0 + 128.0, 0, 255).astype(np.uint8).tobytes()
            elif audio.sampwidth == 3:
                vals = np.clip(x * 8388607.0, -8388608, 8388607).astype(np.int32).reshape(-1) & 0xFFFFFF
                b = np.empty((len(vals), 3), dtype=np.uint8)
                b[:, 0] = vals & 0xFF
                b[:, 1] = (vals >> 8) & 0xFF
                b[:, 2] = (vals >> 16) & 0xFF
                pcm = b.tobytes()
            else:
                pcm = np.clip(x * 32767.0, -32768, 32767).astype("<i2").tobytes()
            wf.writeframes(pcm)
        return wf_io.getvalue()

def dbfs(value, fs_sine=True):
    value = np.asarray(value)
    if fs_sine:
        value = value * np.sqrt(2.0)
        return 20.0 * np.log10(np.maximum(value, EPS))
    return 10.0 * np.log10(np.maximum((value**2) / (2**31)**2, EPS))

def dbfs2(value, fs_sine=True):
    if fs_sine:
        return 20 * np.log10(value)
    return 10 * np.log10(value**2 / (2**31)**2)

def audition_rms_windows(values: np.ndarray, sr: int, window_ms: float = 50.0, hop_ms: float = 10.0) -> np.ndarray:
    x = np.asarray(values, dtype=np.float64).reshape(-1)
    win = max(1, int(round(sr * window_ms / 1000.0)))
    hop = max(1, int(round(sr * hop_ms / 1000.0)))
    n = x.size
    if n < win:
        return np.array([np.sqrt(np.mean(x * x))], dtype=np.float64)
    x = x.astype(np.float64, copy=False)
    energy = x * x
    csum = np.empty(n + 1, dtype=np.float64)
    csum[0] = 0.0
    np.cumsum(energy, out=csum[1:])
    starts = np.arange(0, n - win + 1, hop, dtype=np.int64)
    sums = csum[starts + win] - csum[starts]
    rms = np.sqrt(sums / win)
    return rms

def calculate_stats(data: np.ndarray, sr: int, start_s: float, end_s: float, rms_window_ms: float = 50.0) -> Stats:
    s = max(0, min(len(data), int(round(start_s * sr))))
    e = max(0, min(len(data), int(round(end_s * sr))))
    if e <= s:
        return Stats(-300.0, -300.0, -300.0)
    sec = data[s:e]
    flat = sec.reshape(-1)
    flat = flat - np.mean(flat)
    peak = float(np.max(np.abs(flat)))
    rms_values = audition_rms_windows(flat, sr, rms_window_ms, RMS_HOP_MS)
    if rms_values.size == 0:
        return Stats(-300.0, -300.0, -300.0)
    rms_values_db = dbfs(rms_values, fs_sine=True)
    max_rms = float(np.max(rms_values_db))
    avg_rms = float(np.mean(rms_values_db))
    return Stats(dbfs2(peak), max_rms, avg_rms)

def channel_rms_envelope(data: np.ndarray) -> np.ndarray:
    return np.sqrt(np.mean(np.square(data), axis=1))

def find_start_index(data: np.ndarray) -> int:
    env = channel_rms_envelope(data)
    idx = np.flatnonzero(env > THRESHOLD_RMS)
    return int(idx[0]) if len(idx) else 0

def find_segments(data: np.ndarray, sr: int) -> List[Segment]:
    env = channel_rms_envelope(data)
    active = env > THRESHOLD_RMS
    n = len(active)
    min_mute = max(1, int(round(MUTE_MIN_SECONDS * sr)))
    spans: List[Tuple[int, int]] = []
    i = 0
    while i < n and not active[i]:
        i += 1
    if i >= n:
        return []
    start = i
    mute = 0
    while i < n:
        if active[i]:
            mute = 0
        else:
            mute += 1
            if mute >= min_mute:
                end = i - mute + 1
                if end > start:
                    spans.append((start, end))
                    if len(spans) >= MAX_SEGMENTS:
                        break
                while i < n and not active[i]:
                    i += 1
                start = i
                mute = 0
                continue
        i += 1
    if len(spans) < MAX_SEGMENTS and start < n:
        end = n
        while end > start and not active[end - 1]:
            end -= 1
        if end > start:
            spans.append((start, end))
    return [Segment(f"{k + 1}Section", s / sr, e / sr) for k, (s, e) in enumerate(spans[:MAX_SEGMENTS])]

def _normalize_curve(raw) -> dict:
    if isinstance(raw, dict):
        bps = raw.get("breakpoints", DEFAULT_BREAKPOINTS)
        effs = raw.get("efficiencies", raw.get("efficiency", []))
    else:
        bps = DEFAULT_BREAKPOINTS
        effs = raw
    bps = [float(v) for v in bps]
    effs = [float(v) for v in effs]
    if len(bps) != len(effs) or len(bps) < 2:
        raise ValueError("mismatch")
    pairs = sorted((bp, eff) for bp, eff in zip(bps, effs) if bp > 0 and 0 < eff <= 100)
    if len(pairs) < 2:
        raise ValueError("invalid")
    if len({bp for bp, _ in pairs}) != len(pairs):
        raise ValueError("dup")
    return {"breakpoints": [p[0] for p in pairs], "efficiencies": [p[1] for p in pairs]}

def _interp_efficiency(power, curve: dict) -> np.ndarray:
    bps = np.array(curve["breakpoints"], dtype=np.float64)
    eff = np.array(curve["efficiencies"], dtype=np.float64) / 100.0
    return np.interp(np.asarray(power, dtype=np.float64), bps, eff, left=eff[0], right=eff[-1])

def calculate_channel_current(x_ch, fs, dcr, pcb_r, amp_name, efficiencies, window_ms=0.5, vrms_threshold=0.001,
                              analysis_start_s=0.0, analysis_end_s=0.0) -> dict:
    win_samples = int(round(fs * window_ms * 1e-3))
    if win_samples <= 0:
        raise ValueError("Window too small")
    usable = x_ch.shape[0] - (x_ch.shape[0] % win_samples)
    if usable <= 0:
        raise ValueError("WAV too short")
    x_win = x_ch[:usable].reshape(-1, win_samples).T
    rms_linear = np.sqrt(np.mean(x_win * x_win, axis=0))
    rms_db = 20.0 * np.log10(rms_linear + np.finfo(float).eps)
    vrms = 14.2 * np.power(10.0, (rms_db + 2.0) / 20.0)
    power_load = (vrms ** 2) / dcr + (((vrms / dcr) ** 2) * pcb_r)
    time_arr = np.arange(power_load.size, dtype=np.float64) * (window_ms / 1000.0)
    eff = _interp_efficiency(power_load, efficiencies[amp_name])
    power_in = power_load / eff
    valid = (time_arr >= analysis_start_s) & (time_arr <= analysis_end_s)
    if np.any(valid):
        avg_power_in = float(np.mean(power_in[valid]))
        current_ma = (avg_power_in / 4.0 * 1000.0) + 1.0
    else:
        current_ma = np.nan
    return {"current_ma": float(current_ma) if np.isfinite(current_ma) else np.nan}

# ═══════════════════════════════════════════════════════════════════════════════
# Plotting
# ═══════════════════════════════════════════════════════════════════════════════

def dbfs_tick_label(value: float, _pos=None) -> str:
    mag = abs(float(value))
    if mag <= 1e-6:
        return "-inf"
    return f"{20.0 * math.log10(mag):.0f}"

def plot_time_domain(audio: AudioData, data: np.ndarray, segment: Segment, ax, sel_start: float = None, sel_end: float = None):
    sr = audio.sample_rate
    time = np.arange(len(data)) / sr
    
    if len(data) == 0:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return

    if audio.nchannels == 1:
        ax.plot(time, data[:, 0], label="Mono", color="#1f77b4", linewidth=0.5, alpha=0.8)
    else:
        ax.plot(time, data[:, 0], label="L", color="#1f77b4", linewidth=0.5, alpha=0.8)
        ax.plot(time, data[:, 1], label="R", color="#d62728", linewidth=0.5, alpha=0.8)

    ax.axvline(segment.start_s, color='red', linestyle='--', linewidth=2, alpha=0.8, label=f'{segment.name}')
    ax.axvline(segment.end_s, color='red', linestyle='--', linewidth=2, alpha=0.8)
    ax.axvspan(segment.start_s, segment.end_s, alpha=0.1, color='red')
    
    if sel_start is not None and sel_end is not None and sel_start < sel_end:
        ax.axvline(sel_start, color='green', linestyle=':', linewidth=2, alpha=0.7)
        ax.axvline(sel_end, color='green', linestyle=':', linewidth=2, alpha=0.7)

    ax.set_ylim(-1.0, 1.0)
    ticks = np.array([-1.0, -0.5, -0.25, -0.125, 0.0, 0.125, 0.25, 0.5, 1.0])
    ax.set_yticks(ticks)
    ax.yaxis.set_major_formatter(FuncFormatter(dbfs_tick_label))

    ax.set_title(f"Time Domain - Full File", fontweight="bold", fontsize=10)
    ax.set_xlabel("Time (s)", fontsize=9)
    ax.set_ylabel("Amplitude (dBFS)", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=8)
    ax.set_xlim(0.0, audio.duration)

def plot_fft(audio: AudioData, data: np.ndarray, segment: Segment, nfft: int, ax):
    sr = audio.sample_rate
    s = max(0, min(len(data), int(round(segment.start_s * sr))))
    e = max(0, min(len(data), int(round(segment.end_s * sr))))
    if e <= s:
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        return
    sec = data[s:e]
    if len(sec) < nfft:
        pad = np.zeros((nfft - len(sec), sec.shape[1]))
        section = np.vstack([sec, pad])
    else:
        section = sec[:nfft]
    window = np.hanning(nfft).reshape(-1, 1)
    freq = np.fft.rfftfreq(nfft, d=1.0 / sr)
    mag = np.abs(np.fft.rfft(section * window, axis=0)) / max(np.sum(window) / 2.0, EPS)
    mag_db = np.maximum(20 * np.log10(np.maximum(mag, EPS)), -160)
    mask = freq > 0
    freq_log = freq[mask]
    mag_db_log = mag_db[mask]
    ax.set_xscale("log")
    if audio.nchannels == 1:
        ax.plot(freq_log, mag_db_log[:, 0], label=f"Mono {nfft}", color="#2ca02c", linewidth=0.8)
    else:
        ax.plot(freq_log, mag_db_log[:, 0], label=f"L {nfft}", color="#1f77b4", linewidth=0.8)
        ax.plot(freq_log, mag_db_log[:, 1], label=f"R {nfft}", color="#d62728", linewidth=0.8)
    ax.set_title(f"Frequency Domain ({nfft} FFT)", fontweight="bold", fontsize=10)
    ax.set_xlabel("Frequency (Hz)", fontsize=9)
    ax.set_ylabel("Magnitude (dBFS)", fontsize=9)
    ax.set_xlim(20, 20000)
    ax.set_ylim(-160, 0)
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(loc="upper right", fontsize=8)

# ═══════════════════════════════════════════════════════════════════════════════
# Streamlit App
# ═══════════════════════════════════════════════════════════════════════════════

def init_session():
    if "audio" not in st.session_state:
        st.session_state.audio = None
    if "audio_file_name" not in st.session_state:
        st.session_state.audio_file_name = None
    if "segments" not in st.session_state:
        st.session_state.segments = []
    if "segments_created" not in st.session_state:
        st.session_state.segments_created = False
    if "current_seg_idx" not in st.session_state:
        st.session_state.current_seg_idx = 0
    if "efficiencies" not in st.session_state:
        st.session_state.efficiencies = {name: _normalize_curve(vals) for name, vals in DEFAULT_EFFICIENCIES.items()}
    if "fft_x_min" not in st.session_state:
        st.session_state.fft_x_min = 20.0
    if "fft_x_max" not in st.session_state:
        st.session_state.fft_x_max = 20000.0
    if "fft_y_min" not in st.session_state:
        st.session_state.fft_y_min = -160.0
    if "fft_y_max" not in st.session_state:
        st.session_state.fft_y_max = 0.0
    if "show_amp_editor" not in st.session_state:
        st.session_state.show_amp_editor = False
    if "sel_start_s" not in st.session_state:
        st.session_state.sel_start_s = 0.0
    if "sel_end_s" not in st.session_state:
        st.session_state.sel_end_s = 0.0

def main():
    st.set_page_config(page_title="A4 Audio Analysis", layout="wide", initial_sidebar_state="expanded")
    init_session()

    st.title("🎵 A4 Audio Analysis Portal")
    st.markdown("**Adaptive Audio Analysis** - Professional Audio File Analysis")

    with st.sidebar:
        st.header("File Upload")

        uploaded_file = st.file_uploader("Select WAV File", type=["wav"])

        if uploaded_file:
            # ★ 새 파일이 업로드되었는지 확인
            if st.session_state.audio_file_name != uploaded_file.name:
                try:
                    file_bytes = uploaded_file.getvalue()
                    audio = read_wav(file_bytes)
                    st.session_state.audio = audio
                    st.session_state.audio_file_name = uploaded_file.name
                    
                    full_segment = Segment("Full File", 0.0, audio.duration)
                    st.session_state.segments = [full_segment]
                    st.session_state.current_seg_idx = 0
                    st.session_state.segments_created = False
                    
                    # ★ Time Domain 범위 초기화
                    st.session_state.sel_start_s = 0.0
                    st.session_state.sel_end_s = audio.duration

                    st.success("✅ File loaded!")
                    st.info(f"SR: {audio.sample_rate} Hz | {audio.nchannels}ch | {audio.duration:.2f}s")

                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    st.session_state.audio = None

        # ★ Reset All (파일도 삭제)
        if st.session_state.audio is not None:
            if st.button("🔄 Reset All", use_container_width=True, key="reset_btn"):
                st.session_state.audio = None
                st.session_state.audio_file_name = None
                st.session_state.segments = []
                st.session_state.current_seg_idx = 0
                st.session_state.segments_created = False
                st.session_state.show_amp_editor = False
                st.session_state.sel_start_s = 0.0
                st.session_state.sel_end_s = 0.0
                st.success("✅ All reset!")
                st.rerun()

        st.divider()

        if st.session_state.audio is not None:
            st.subheader("Segment Tools")

            if st.button("🔍 시작점 찾기", use_container_width=True, key="find_start_btn"):
                audio = st.session_state.audio
                start_idx = find_start_index(audio.data)
                start_time = start_idx / audio.sample_rate
                
                st.info(f"Start: {start_time:.3f}s")
                
                trimmed_data = audio.data[start_idx:].copy()
                trimmed_audio = AudioData(audio.sample_rate, trimmed_data, audio.sampwidth, audio.nchannels)
                st.session_state.audio = trimmed_audio
                
                full_segment = Segment("Full File (Trimmed)", 0.0, trimmed_audio.duration)
                st.session_state.segments = [full_segment]
                st.session_state.segments_created = False
                st.session_state.current_seg_idx = 0
                st.session_state.sel_start_s = 0.0
                st.session_state.sel_end_s = trimmed_audio.duration
                
                wav_bytes = write_wav(trimmed_audio, trimmed_data)
                
                # ★ 파일명 입력 UI
                col_fname, col_down = st.columns([2, 1])
                with col_fname:
                    save_filename = st.text_input("Save filename", "trimmed.wav", key="trimmed_filename")
                with col_down:
                    st.download_button("💾 Download", wav_bytes, save_filename, "audio/wav", use_container_width=True)

            st.divider()

            if st.button("📍 구간 분리", use_container_width=True, key="split_btn"):
                audio = st.session_state.audio
                segments = find_segments(audio.data, audio.sample_rate)
                
                if segments:
                    full_file = st.session_state.segments[0]
                    st.session_state.segments = [full_file] + segments
                    st.session_state.segments_created = True
                    st.session_state.current_seg_idx = 0
                    st.success(f"✅ {len(segments)} segments")
                else:
                    st.warning("⚠ No segments")

            st.divider()

        st.subheader("Segment Selection")
        if st.session_state.segments:
            seg_names = [seg.name for seg in st.session_state.segments]
            
            # ★ 안정적인 선택 처리
            idx = min(st.session_state.current_seg_idx, len(seg_names) - 1)
            selected_idx = st.selectbox(
                "Select",
                range(len(seg_names)),
                format_func=lambda i: seg_names[i],
                index=idx,
                key=f"segment_select_{len(st.session_state.segments)}"  # ★ 동적 key
            )
            
            # ★ Section 선택 시 Time Domain 범위 자동 변경
            if selected_idx != st.session_state.current_seg_idx:
                st.session_state.current_seg_idx = selected_idx
                selected_segment = st.session_state.segments[selected_idx]
                st.session_state.sel_start_s = selected_segment.start_s
                st.session_state.sel_end_s = selected_segment.end_s
            
            st.session_state.current_seg_idx = selected_idx
            st.caption(f"✓ {seg_names[selected_idx]}")

        st.divider()

        st.subheader("Current/Power Calculation")
        amp_names = sorted(st.session_state.efficiencies.keys())
        col_amp, col_edit = st.columns([3, 1])
        with col_amp:
            amp_name = st.selectbox("AMP Model", amp_names, key="amp_model_select")
        with col_edit:
            if st.button("✏️", key="edit_amp_btn"):
                st.session_state.show_amp_editor = not st.session_state.get("show_amp_editor", False)
        
        if st.session_state.get("show_amp_editor", False):
            st.divider()
            edit_amp_name = st.selectbox("Edit", amp_names, key="edit_amp_select")
            curve = st.session_state.efficiencies[edit_amp_name]
            st.dataframe(pd.DataFrame({"Power (W)": curve["breakpoints"], "Efficiency (%)": curve["efficiencies"]}), use_container_width=True)
            json_str = json.dumps({"breakpoints": curve["breakpoints"], "efficiencies": curve["efficiencies"]}, indent=2)
            edited_json = st.text_area("JSON", value=json_str, height=100, key="json_edit_area")
            if st.button("💾 Save", key="save_amp_btn"):
                try:
                    new_curve = json.loads(edited_json)
                    st.session_state.efficiencies[edit_amp_name] = _normalize_curve(new_curve)
                    st.success("Saved!")
                except Exception as e:
                    st.error(f"Error: {e}")

        col_dcr, col_pcb = st.columns(2)
        with col_dcr:
            dcr = st.number_input("DCR (Ohm)", 0.1, 100.0, 8.0, 0.1)
        with col_pcb:
            pcb_r = st.number_input("PCB R (mOhm)", 0.0, 1000.0, 0.0, 1.0)
        vrms_threshold = st.number_input("Vrms Threshold", 0.0001, 1.0, 0.01, 0.0001)

        st.divider()

        st.subheader("Analysis Parameters")
        rms_window_ms = st.number_input("RMS Window (ms)", 10.0, 200.0, 50.0, 10.0)
        fft_size = st.selectbox("FFT Size", [512, 1024, 2048, 4096, 8192, 16384, 65536], 2)

        st.divider()

        st.subheader("FFT Axis Range")
        col_x, col_y = st.columns(2)
        with col_x:
            st.session_state.fft_x_min = st.number_input("X Min (Hz)", 1.0, 10000.0, st.session_state.fft_x_min, 10.0)
            st.session_state.fft_x_max = st.number_input("X Max (Hz)", 100.0, 50000.0, st.session_state.fft_x_max, 100.0)
        with col_y:
            st.session_state.fft_y_min = st.number_input("Y Min (dB)", -200.0, -50.0, st.session_state.fft_y_min, 10.0)
            st.session_state.fft_y_max = st.number_input("Y Max (dB)", -50.0, 10.0, st.session_state.fft_y_max, 5.0)

    # ═════════════════════════════════════════════════════════════════════════════
    # Main Content
    # ═════════════════════════════════════════════════════════════════════════════

    if st.session_state.audio is None:
        st.warning("👈 Upload a WAV file in sidebar")
        return

    if not st.session_state.segments:
        st.error("No segments")
        return

    current_segment = st.session_state.segments[st.session_state.current_seg_idx]
    
    st.info(f"📍 {current_segment.name} ({current_segment.start_s:.3f}s ~ {current_segment.end_s:.3f}s)")

    tab1, tab2 = st.tabs(["Time Domain", "FFT Spectrum"])

    with tab1:
        st.subheader(f"Time Domain - {current_segment.name}")

        st.write("**Analysis Time Range (green dashed lines):**")
        col_x1, col_x2 = st.columns(2)
        with col_x1:
            # ★ key를 동적으로 변경 (current_seg_idx 포함)
            st.session_state.sel_start_s = st.number_input("Start (s)", 0.0, float(st.session_state.audio.duration), float(st.session_state.sel_start_s), 0.1, key=f"x_min_{st.session_state.current_seg_idx}")
        with col_x2:
            # ★ key를 동적으로 변경 (current_seg_idx 포함)
            st.session_state.sel_end_s = st.number_input("End (s)", 0.0, float(st.session_state.audio.duration), float(st.session_state.sel_end_s), 0.1, key=f"x_max_{st.session_state.current_seg_idx}")

        if st.session_state.sel_start_s >= st.session_state.sel_end_s:
            st.error("Start < End")
            return

        st.divider()

        col_graph, col_stats = st.columns([2, 1])

        with col_graph:
            fig = Figure(figsize=(10, 5), dpi=100)
            ax = fig.add_subplot(111)
            plot_time_domain(st.session_state.audio, st.session_state.audio.data, current_segment, ax, 
                           st.session_state.sel_start_s, st.session_state.sel_end_s)
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)

        with col_stats:
            st.write("**Statistics**")

            audio = st.session_state.audio
            data = audio.data
            
            time_start = st.session_state.sel_start_s
            time_end = st.session_state.sel_end_s

            if audio.nchannels == 1:
                stats_l = calculate_stats(data, audio.sample_rate, time_start, time_end, rms_window_ms)
                stats_r = stats_l
            else:
                stats_l = calculate_stats(data[:, [0]], audio.sample_rate, time_start, time_end, rms_window_ms)
                stats_r = calculate_stats(data[:, [1]], audio.sample_rate, time_start, time_end, rms_window_ms)

            st.write("**Amplitude (dBFS)**")
            st.dataframe(pd.DataFrame({
                "Metric": ["Peak", "Max RMS", "Avg RMS"],
                "L": [f"{stats_l.peak_dbfs:.1f}", f"{stats_l.max_rms_dbfs:.1f}", f"{stats_l.avg_rms_dbfs:.1f}"],
                "R": [f"{stats_r.peak_dbfs:.1f}", f"{stats_r.max_rms_dbfs:.1f}", f"{stats_r.avg_rms_dbfs:.1f}"]
            }), use_container_width=True, hide_index=True)

            st.divider()

            st.write("**Current (mA)**")
            try:
                if audio.nchannels == 1:
                    res = calculate_channel_current(data[:, 0], audio.sample_rate, dcr, pcb_r, amp_name, st.session_state.efficiencies, window_ms=0.5, vrms_threshold=vrms_threshold, analysis_start_s=time_start, analysis_end_s=time_end)
                    current_l = current_r = res["current_ma"]
                else:
                    res_l = calculate_channel_current(data[:, 0], audio.sample_rate, dcr, pcb_r, amp_name, st.session_state.efficiencies, window_ms=0.5, vrms_threshold=vrms_threshold, analysis_start_s=time_start, analysis_end_s=time_end)
                    res_r = calculate_channel_current(data[:, 1], audio.sample_rate, dcr, pcb_r, amp_name, st.session_state.efficiencies, window_ms=0.5, vrms_threshold=vrms_threshold, analysis_start_s=time_start, analysis_end_s=time_end)
                    current_l = res_l["current_ma"]
                    current_r = res_r["current_ma"]

                st.dataframe(pd.DataFrame({
                    "": ["Current"],
                    "L": [f"{current_l:.1f}" if np.isfinite(current_l) else "-"],
                    "R": [f"{current_r:.1f}" if np.isfinite(current_r) else "-"]
                }), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error: {e}")

            st.divider()

            st.write("**Power (W)**")
            try:
                if audio.nchannels == 1:
                    v_peak = 14.2 * (10.0 ** ((stats_l.peak_dbfs + 2.0) / 20.0))
                    power_peak = (v_peak ** 2) / (dcr * 2.0)
                    v_max_rms = 10.0 * (10.0 ** ((stats_l.max_rms_dbfs + 2.0) / 20.0))
                    power_max_rms = (v_max_rms ** 2) / dcr
                    v_avg_rms = 10.0 * (10.0 ** ((stats_l.avg_rms_dbfs + 2.0) / 20.0))
                    power_avg_rms = (v_avg_rms ** 2) / dcr

                    st.dataframe(pd.DataFrame({
                        "Type": ["Peak", "Vrms Max", "Vrms"],
                        "L": [f"{power_peak:.1f}", f"{power_max_rms:.1f}", f"{power_avg_rms:.1f}"],
                        "R": [f"{power_peak:.1f}", f"{power_max_rms:.1f}", f"{power_avg_rms:.1f}"]
                    }), use_container_width=True, hide_index=True)
                else:
                    v_peak_l = 14.2 * (10.0 ** ((stats_l.peak_dbfs + 2.0) / 20.0))
                    power_peak_l = (v_peak_l ** 2) / (dcr * 2.0)
                    v_max_rms_l = 10.0 * (10.0 ** ((stats_l.max_rms_dbfs + 2.0) / 20.0))
                    power_max_rms_l = (v_max_rms_l ** 2) / dcr
                    v_avg_rms_l = 10.0 * (10.0 ** ((stats_l.avg_rms_dbfs + 2.0) / 20.0))
                    power_avg_rms_l = (v_avg_rms_l ** 2) / dcr

                    v_peak_r = 14.2 * (10.0 ** ((stats_r.peak_dbfs + 2.0) / 20.0))
                    power_peak_r = (v_peak_r ** 2) / (dcr * 2.0)
                    v_max_rms_r = 10.0 * (10.0 ** ((stats_r.max_rms_dbfs + 2.0) / 20.0))
                    power_max_rms_r = (v_max_rms_r ** 2) / dcr
                    v_avg_rms_r = 10.0 * (10.0 ** ((stats_r.avg_rms_dbfs + 2.0) / 20.0))
                    power_avg_rms_r = (v_avg_rms_r ** 2) / dcr

                    st.dataframe(pd.DataFrame({
                        "Type": ["Peak", "Vrms Max", "Vrms"],
                        "L": [f"{power_peak_l:.1f}", f"{power_max_rms_l:.1f}", f"{power_avg_rms_l:.1f}"],
                        "R": [f"{power_peak_r:.1f}", f"{power_max_rms_r:.1f}", f"{power_avg_rms_r:.1f}"]
                    }), use_container_width=True, hide_index=True)
            except Exception as e:
                st.error(f"Error: {e}")

    with tab2:
        st.subheader(f"FFT Spectrum - {current_segment.name}")

        fig = Figure(figsize=(12, 6), dpi=100)
        ax = fig.add_subplot(111)
        plot_fft(st.session_state.audio, st.session_state.audio.data, current_segment, fft_size, ax)
        ax.set_xlim(st.session_state.fft_x_min, st.session_state.fft_x_max)
        ax.set_ylim(st.session_state.fft_y_min, st.session_state.fft_y_max)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)


if __name__ == "__main__":
    main()