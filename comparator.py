import streamlit as st
import difflib
import hashlib
import os

# ─────────────────────────────
# UI CONFIG
# ─────────────────────────────
st.set_page_config(page_title="File Comparator", layout="wide")
st.title("🔍 FILE COMPARATOR (Web Version)")

# ─────────────────────────────
# FILE INPUT
# ─────────────────────────────
col1, col2 = st.columns(2)

with col1:
    file_a = st.file_uploader("FILE A", type=None)

with col2:
    file_b = st.file_uploader("FILE B", type=None)

# ─────────────────────────────
# MODE SELECT
# ─────────────────────────────
mode = st.radio(
    "Mode",
    ["auto", "text", "binary"],
    horizontal=True
)

# ─────────────────────────────
# UTIL
# ─────────────────────────────
def is_binary(data: bytes):
    return b"\x00" in data[:8192]

def md5(data: bytes):
    return hashlib.md5(data).hexdigest()

def read_text(data: bytes):
    for enc in ["utf-8", "utf-8-sig", "cp949", "latin-1"]:
        try:
            return data.decode(enc).splitlines()
        except:
            continue
    return []

def to_hex_lines(data: bytes):
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i+16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        asc_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{i:08x}  {hex_part:<47}  {asc_part}")
    return lines

# ─────────────────────────────
# COMPARE BUTTON
# ─────────────────────────────
if st.button("▶ 비교 시작"):

    if not file_a or not file_b:
        st.warning("두 파일을 모두 선택하세요")
        st.stop()

    data_a = file_a.read()
    data_b = file_b.read()

    # ─────────────────────────
    # MODE 결정
    # ─────────────────────────
    if mode == "auto":
        use_binary = is_binary(data_a) or is_binary(data_b)
    else:
        use_binary = (mode == "binary")

    # ─────────────────────────
    # TEXT MODE
    # ─────────────────────────
    if not use_binary:

        lines_a = read_text(data_a)
        lines_b = read_text(data_b)

        max_len = max(len(lines_a), len(lines_b))
        lines_a += [""] * (max_len - len(lines_a))
        lines_b += [""] * (max_len - len(lines_b))

        diff_rows = [
            i for i in range(max_len)
            if lines_a[i] != lines_b[i]
        ]

        st.subheader("📄 TEXT DIFF")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### FILE A")
            for i, line in enumerate(lines_a):
                if i in diff_rows:
                    st.error(f"{i+1}: {line}")
                else:
                    st.text(f"{i+1}: {line}")

        with col2:
            st.markdown("### FILE B")
            for i, line in enumerate(lines_b):
                if i in diff_rows:
                    st.error(f"{i+1}: {line}")
                else:
                    st.text(f"{i+1}: {line}")

        st.info(f"총 {len(diff_rows)}개 라인 차이")

    # ─────────────────────────
    # BINARY MODE
    # ─────────────────────────
    else:

        hex_a = to_hex_lines(data_a)
        hex_b = to_hex_lines(data_b)

        max_len = max(len(hex_a), len(hex_b))
        hex_a += [""] * (max_len - len(hex_a))
        hex_b += [""] * (max_len - len(hex_b))

        diff_rows = [
            i for i in range(max_len)
            if hex_a[i] != hex_b[i]
        ]

        st.subheader("🔧 BINARY DIFF (HEX VIEW)")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### FILE A")
            for i, line in enumerate(hex_a):
                if i in diff_rows:
                    st.error(line)
                else:
                    st.text(line)

        with col2:
            st.markdown("### FILE B")
            for i, line in enumerate(hex_b):
                if i in diff_rows:
                    st.error(line)
                else:
                    st.text(line)

        st.info(f"총 {len(diff_rows)} 블록 차이")

        # MD5 비교
        st.write("### HASH")
        c1, c2 = st.columns(2)
        c1.metric("MD5 A", md5(data_a))
        c2.metric("MD5 B", md5(data_b))