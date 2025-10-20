# app.py
# ---------------------------------------------
# 요구 패키지: streamlit, pillow
# 실행: streamlit run app.py
# ---------------------------------------------

import time
from math import cos, sin, radians, pi
from io import BytesIO
from typing import List, Optional

import streamlit as st
from PIL import Image, ImageDraw

# ------------------ 기본 설정 ------------------
WIDTH, HEIGHT = 960, 540
GROUND_Y = HEIGHT - 120
WHEEL_R = 30
DEFAULT_SPEED = 240.0  # px/sec
ANIM_FPS = 10          # 말 프레임 속도(초당)
BG = (235, 245, 255)

st.set_page_config(page_title="클릭하면 달리는 마차 - Streamlit(무의존)", layout="wide")

# ------------------ 상태 초기화 ------------------
if "running" not in st.session_state:
    st.session_state.running = False
if "x" not in st.session_state:
    st.session_state.x = 60.0
if "wheel_angle" not in st.session_state:
    st.session_state.wheel_angle = 0.0
if "anim_index" not in st.session_state:
    st.session_state.anim_index = 0
if "last_time" not in st.session_state:
    st.session_state.last_time = time.perf_counter()

# ------------------ 사이드바: 자산 업로드/설정 ------------------
with st.sidebar:
    st.markdown("### 자산 업로드 (선택)")
    horse_files = st.file_uploader(
        "말 달리기 프레임들 (여러 개 선택, 순서대로 사용)",
        type=["png", "webp"],
        accept_multiple_files=True,
        help="여러 장의 말 스프라이트 프레임을 업로드하면 애니메이션으로 사용됩니다.",
    )
    carriage_file = st.file_uploader(
        "마차 이미지 (선택)",
        type=["png", "webp"],
        help="마차 본체 이미지 1장을 업로드하세요. 없으면 폴백 도형으로 그립니다."
    )
    speed = st.slider("속도(px/sec)", 60, 800, int(DEFAULT_SPEED), step=10)
    st.caption("버튼을 눌러 달리기/정지를 전환하세요. 업로드가 없으면 폴백 도형으로 애니메이션합니다.")

SPEED = float(speed)

# ------------------ 이미지 로드 ------------------
def load_pil_image(file) -> Optional[Image.Image]:
    if not file:
        return None
    try:
        return Image.open(file).convert("RGBA")
    except Exception:
        return None

horse_frames: List[Image.Image] = []
if horse_files:
    for f in horse_files:
        im = load_pil_image(f)
        if im:
            # 너무 크면 폭 260 기준으로 축소
            if im.width > 260:
                ratio = 260 / im.width
                im = im.resize((int(im.width * ratio), int(im.height * ratio)), Image.LANCZOS)
            horse_frames.append(im)

carriage_img = load_pil_image(carriage_file)
if carriage_img and carriage_img.width > 320:
    ratio = 320 / carriage_img.width
    carriage_img = carriage_img.resize(
        (int(carriage_img.width * ratio), int(carriage_img.height * ratio)),
        Image.LANCZOS
    )

USE_FALLBACK_HORSE = len(horse_frames) == 0
USE_FALLBACK_CARRIAGE = carriage_img is None

# 대체 드로잉 기준 크기
HORSE_W, HORSE_H = 220, 140
CARRIAGE_W, CARRIAGE_H = 260, 150

# 말/마차 상대 위치 오프셋 (말, 마차가 지면에 닿아 보이도록 조정)
HORSE_OFFSET = (-40, -HORSE_H + 30)
CARRIAGE_OFFSET = (120, -CARRIAGE_H + 50)

# ------------------ 그리기 도우미 ------------------
def draw_wheel(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, angle_deg: float):
    # 바퀴 테두리
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(30, 30, 30), width=3)
    # 스포크
    for base in (0, 45, 90, 135):
        a = radians(base + angle_deg)
        x2 = cx + r * cos(a)
        y2 = cy + r * sin(a)
        draw.line((cx, cy, x2, y2), fill=(30, 30, 30), width=2)
    # 허브
    draw.ellipse((cx - 5, cy - 5, cx + 5, cy + 5), fill=(30, 30, 30))

def draw_ground(draw: ImageDraw.ImageDraw, x: float):
    # 땅
    draw.rectangle((0, GROUND_Y + 1, WIDTH, HEIGHT), fill=(200, 220, 230))
    draw.line((0, GROUND_Y, WIDTH, GROUND_Y), fill=(170, 190, 200), width=3)
    # 간단한 패럴랙스 수풀
    for i in range(8):
        base_x = int(i * 160 - (x * 0.1) % 160)
        draw.ellipse((base_x, GROUND_Y - 26, base_x + 140, GROUND_Y + 14), fill=(190, 210, 220))

def paste_rgba(bg: Image.Image, fg: Image.Image, x: int, y: int):
    bg.alpha_composite(fg, (x, y))

def draw_fallback_horse(draw: ImageDraw.ImageDraw, base_x: int, base_y: int, frame_idx: int):
    # base_y는 말의 발끝이 닿는 지점 기준
    frame = frame_idx % 6
    leg_phase = [-15, 0, 15, -10, 10, 0][frame]

    # 몸통
    draw.ellipse((base_x, base_y - 60, base_x + 140, base_y), fill=(90, 80, 60))
    # 목/머리
    draw.rectangle((base_x + 110, base_y - 95, base_x + 126, base_y - 55), fill=(90, 80, 60))
    draw.ellipse((base_x + 115, base_y - 105, base_x + 155, base_y - 75), fill=(90, 80, 60))
    # 눈
    draw.ellipse((base_x + 143, base_y - 96, base_x + 149, base_y - 90), fill=(0, 0, 0))
    # 꼬리
    draw.line((base_x + 10, base_y - 40, base_x - 10, base_y - 65), fill=(70, 60, 45), width=6)

    def leg(px, py, ang_deg, length=55):
        a = radians(ang_deg)
        x2 = px + length * cos(a)
        y2 = py + length * sin(a)
        draw.line((px, py, x2, y2), fill=(60, 50, 40), width=8)

    # 앞다리
    leg(base_x + 120, base_y - 5, 90 + leg_phase)
    leg(base_x + 105, base_y - 5, 90 - leg_phase)
    # 뒷다리
    leg(base_x + 25, base_y - 2, 90 - leg_phase)
    leg(base_x + 40, base_y - 2, 90 + leg_phase)

def draw_fallback_carriage(draw: ImageDraw.ImageDraw, base_x: int, base_y: int, wheel_angle: float):
    # base_y는 바퀴 중심 높이 근처
    # 차체
    draw.rounded_rectangle((base_x, base_y - 90, base_x + 200, base_y), radius=12, fill=(40, 60, 85))
    # 창문
    draw.rounded_rectangle((base_x + 20, base_y - 80, base_x + 80, base_y - 40), radius=6, fill=(220, 235, 250))
    draw.rounded_rectangle((base_x + 90, base_y - 80, base_x + 150, base_y - 40), radius=6, fill=(220, 235, 250))
    # 멍에
    draw.line((base_x + 200, base_y - 40, base_x + 260, base_y - 60), fill=(60, 60, 60), width=6)
    # 바퀴
    draw_wheel(draw, base_x + 50, base_y, WHEEL_R, wheel_angle)
    draw_wheel(draw, base_x + 160, base_y, WHEEL_R, wheel_angle)

# ------------------ 프레임 생성 ------------------
def render_frame() -> Image.Image:
    # 캔버스 백버퍼
    frame = Image.new("RGBA", (WIDTH, HEIGHT), BG + (255,))
    draw = ImageDraw.Draw(frame)

    # 배경/땅
    draw_ground(draw, st.session_state.x)

    # 말 위치
    hx = int(st.session_state.x + HORSE_OFFSET[0])
    hy = int(GROUND_Y + HORSE_OFFSET[1])

    # 살짝 바운스
    bounce = 3 * sin(time.perf_counter() * 6.0)

    if USE_FALLBACK_HORSE:
        draw_fallback_horse(draw, hx, hy + HORSE_H, st.session_state.anim_index)
    else:
        horse = horse_frames[st.session_state.anim_index % len(horse_frames)]
        paste_rgba(frame, horse, hx, int(hy + bounce))

    # 마차 위치
    cx = int(st.session_state.x + CARRIAGE_OFFSET[0])
    cy = int(GROUND_Y + CARRIAGE_OFFSET[1])

    if USE_FALLBACK_CARRIAGE:
        draw_fallback_carriage(draw, cx, cy + CARRIAGE_H - 10, st.session_state.wheel_angle)
    else:
        paste_rgba(frame, carriage_img, cx, cy)
        # 바퀴(이미지에 없다 가정하고 그려줌)
        draw_wheel(draw, cx + 50, cy + CARRIAGE_H - 10, WHEEL_R, st.session_state.wheel_angle)
        draw_wheel(draw, cx + carriage_img.width - 50, cy + CARRIAGE_H - 10, WHEEL_R, st.session_state.wheel_angle)

    return frame.convert("RGB")

def step_physics(dt: float):
    # 이동 및 각도/애니메이션 갱신
    if st.session_state.running:
        st.session_state.x += SPEED * dt
        circumference = 2 * pi * WHEEL_R
        deg_per_px = 360.0 / circumference
        st.session_state.wheel_angle = (st.session_state.wheel_angle + SPEED * dt * deg_per_px) % 360

        # 말 프레임 (시간 기반 증가)
        frames_per_sec = ANIM_FPS
        # dt가 작더라도 안정적으로 증가하도록 누적 방식
        # 간단히 dt*fps 만큼 인덱스를 올림
        inc = max(1, int(round(frames_per_sec * dt)))
        st.session_state.anim_index = (st.session_state.anim_index + inc) % 10_000

        # 화면 루프
        if st.session_state.x - 300 > WIDTH:
            st.session_state.x = -400

# ------------------ 상단 UI ------------------
title_col, ctrl_col = st.columns([0.7, 0.3])
with title_col:
    st.markdown("## 달리는 마차 (Streamlit, 외부 의존 제거)")
    st.write("• **시작/정지 버튼**으로 애니메이션을 제어합니다.  \n• 스프라이트 업로드가 없으면 **도형 기반 폴백 애니메이션**으로 동작합니다.")

with ctrl_col:
    state_str = "달리는 중" if st.session_state.running else "정지"
    st.metric("상태", state_str)

# 버튼으로 달리기 토글
if st.button("🏇 시작/정지 전환", use_container_width=True):
    st.session_state.running = not st.session_state.running

# ------------------ 물리 갱신 & 렌더 ------------------
now = time.perf_counter()
dt = now - st.session_state.last_time
st.session_state.last_time = now

step_physics(dt)
frame = render_frame()

# ------------------ 표시 ------------------
st.image(frame, use_column_width=False, caption="버튼을 눌러 달리기/정지 전환")

# ------------------ 자동 재실행(애니메이션용) ------------------
# 실행 중이면 약 20FPS 정도로 갱신 (50ms 간격)
if st.session_state.running:
    time.sleep(0.05)
    # Streamlit 1.30+에서는 st.rerun, 그 외 버전 호환을 위해 예외 처리
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()
