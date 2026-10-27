import streamlit as st
import pandas as pd
from datetime import date, timedelta
from io import BytesIO

# -----------------------------
# 기본 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="음식물 쓰레기 감량 계산기",
    page_icon="🌱",
    layout="wide"
)

# 초록색 계열의 간단한 디자인
st.markdown("""
<style>
    .stApp { background-color: #f5fbf5; }
    h1, h2, h3 { color: #216b3a; }
    div[data-testid="stMetric"] {
        background-color: white;
        border: 1px solid #d7ead9;
        padding: 14px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🌱 음식물 쓰레기 감량 계산기")
st.write(
    "음식물 쓰레기 발생량과 감량 목표를 입력해 감량 전후의 예상량을 비교해 보세요."
)
st.info(
    "이 프로그램은 입력한 값을 이용해 예상량을 계산합니다. "
    "실제 측정값과 예시값을 구분해서 사용하세요."
)

# -----------------------------
# 사이드바: 계산 조건 입력
# -----------------------------
st.sidebar.header("계산 조건")

data_kind = st.sidebar.radio(
    "데이터 종류",
    ["직접 입력한 값", "예시 데이터"],
    help="예시 데이터는 실제 측정값이 아닙니다."
)

if data_kind == "예시 데이터":
    daily_kg = 2.0
    reduction_rate = 20
    period_days = 30
    st.sidebar.caption("예시값: 하루 2kg, 감량 목표 20%, 기간 30일")
else:
    daily_kg = st.sidebar.number_input(
        "하루 평균 발생량 (kg)",
        min_value=0.0,
        max_value=100000.0,
        value=2.0,
        step=0.1,
        help="예: 하루 동안 발생한 음식물 쓰레기가 2kg이면 2를 입력하세요."
    )
    reduction_rate = st.sidebar.slider(
        "감량 목표 (%)",
        min_value=0,
        max_value=100,
        value=20,
        step=5
    )
    period_days = st.sidebar.selectbox(
        "계산 기간",
        options=[7, 30],
        format_func=lambda x: "1주일 (7일)" if x == 7 else "1개월 (30일)"
    )

# -----------------------------
# 날짜별 데이터 입력
# -----------------------------
st.header("📅 날짜별 발생량 입력 (선택 사항)")
st.write(
    "날짜별 실제 발생량이 있다면 표에 입력하세요. "
    "입력하지 않아도 위의 하루 평균 발생량을 이용해 계산할 수 있습니다."
)

use_daily_table = st.checkbox("날짜별 데이터를 입력하거나 수정하기")

if use_daily_table:
    default_rows = []
    today = date.today()
    for i in range(6, -1, -1):
        default_rows.append({
            "날짜": today - timedelta(days=i),
            "발생량 (kg)": 0.0
        })

    if "daily_table" not in st.session_state:
        st.session_state["daily_table"] = pd.DataFrame(default_rows)

    edited_df = st.data_editor(
        st.session_state["daily_table"],
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "날짜": st.column_config.DateColumn(
                "날짜",
                format="YYYY-MM-DD",
                required=True
            ),
            "발생량 (kg)": st.column_config.NumberColumn(
                "발생량 (kg)",
                min_value=0.0,
                step=0.1,
                format="%.2f",
                required=True
            )
        },
        key="daily_editor"
    )

    if not edited_df.empty:
        edited_df = edited_df.copy()
        edited_df["날짜"] = pd.to_datetime(
            edited_df["날짜"], errors="coerce"
        )
        edited_df["발생량 (kg)"] = pd.to_numeric(
            edited_df["발생량 (kg)"], errors="coerce"
        )
        valid_df = edited_df.dropna(subset=["날짜", "발생량 (kg)"])

        if (valid_df["발생량 (kg)"] < 0).any():
            st.error("날짜별 발생량은 0 이상이어야 합니다.")
            valid_df = valid_df[valid_df["발생량 (kg)"] >= 0]

        if not valid_df.empty:
            valid_df = valid_df.sort_values("날짜")
            st.session_state["daily_table"] = valid_df.rename(
                columns={"발생량 (kg)": "발생량 (kg)"}
            ).reset_index(drop=True)
            table_total = float(valid_df["발생량 (kg)"].sum())
            table_average = float(valid_df["발생량 (kg)"].mean())
            st.caption(
                f"입력 데이터: {len(valid_df)}일 | "
                f"총 발생량: {table_total:.2f}kg | "
                f"하루 평균: {table_average:.2f}kg"
            )
        else:
            st.warning("계산에 사용할 수 있는 날짜별 데이터가 없습니다.")
            valid_df = pd.DataFrame(columns=["날짜", "발생량 (kg)"])
    else:
        valid_df = pd.DataFrame(columns=["날짜", "발생량 (kg)"])
else:
    valid_df = pd.DataFrame(columns=["날짜", "발생량 (kg)"])

# -----------------------------
# 계산
# -----------------------------
st.header("📊 계산 결과")

if use_daily_table and not valid_df.empty:
    # 날짜별 데이터가 입력되면 그 합계를 기준으로 감량 효과를 계산
    baseline = float(valid_df["발생량 (kg)"].sum())
    used_days = len(valid_df)
    calculation_label = f"입력한 {used_days}일의 합계"
else:
    # 날짜별 데이터가 없으면 하루 평균 × 선택한 기간으로 계산
    baseline = float(daily_kg) * int(period_days)
    used_days = int(period_days)
    calculation_label = f"{period_days}일 예상량"

reduction_amount = baseline * float(reduction_rate) / 100
remaining_amount = baseline - reduction_amount

st.caption(f"계산 기준: {calculation_label}")

col1, col2, col3, col4 = st.columns(4)
col1.metric("감량 전 발생량", f"{baseline:.2f} kg")
col2.metric("목표 감량량", f"{reduction_amount:.2f} kg")
col3.metric("감량 후 예상량", f"{remaining_amount:.2f} kg")
col4.metric("감량 목표", f"{reduction_rate}%")

result_df = pd.DataFrame({
    "항목": ["감량 전 발생량", "목표 감량량", "감량 후 예상 발생량"],
    "발생량 (kg)": [baseline, reduction_amount, remaining_amount]
})

st.subheader("감량 전후 비교")
chart_df = pd.DataFrame({
    "구분": ["감량 전", "감량 후"],
    "음식물 쓰레기 (kg)": [baseline, remaining_amount]
}).set_index("구분")
st.bar_chart(chart_df)

st.subheader("🌍 환경 보호 의미")
if reduction_rate == 0:
    st.write("현재 감량 목표가 0%입니다. 감량 목표를 설정하면 예상 감량량을 확인할 수 있습니다.")
elif reduction_rate == 100:
    st.write(
        f"입력한 기간의 음식물 쓰레기를 전부 줄이는 것을 목표로 합니다. "
        f"계산상 {baseline:.2f}kg을 줄이는 결과입니다. 실제로 가능한지는 생활 환경에 따라 달라집니다."
    )
else:
    st.write(
        f"설정한 목표를 달성하면 {baseline:.2f}kg 중 약 "
        f"{reduction_amount:.2f}kg을 줄이고, 발생량을 "
        f"{remaining_amount:.2f}kg으로 낮출 수 있습니다. "
        "음식물 쓰레기를 줄이면 식품 생산·운송·처리에 쓰이는 자원 낭비를 줄이는 데 도움이 됩니다."
    )

st.caption(
    "주의: 감량량은 목표 비율을 적용한 예상치이며 실제 감량 실적을 의미하지 않습니다. "
    "탄소 배출량은 검증된 배출계수를 사용하지 않았으므로 표시하지 않습니다."
)

# -----------------------------
# 날짜별 그래프
# -----------------------------
if use_daily_table and not valid_df.empty:
    st.subheader("날짜별 음식물 쓰레기 발생량")
    daily_chart = valid_df.copy()
    daily_chart["날짜"] = pd.to_datetime(daily_chart["날짜"])
    daily_chart = daily_chart.set_index("날짜")
    st.line_chart(daily_chart[["발생량 (kg)"]])

# -----------------------------
# CSV 다운로드
# -----------------------------
st.header("⬇️ 결과 다운로드")

csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    label="계산 결과 CSV 다운로드",
    data=csv_bytes,
    file_name="음식물_쓰레기_감량_계산_결과.csv",
    mime="text/csv"
)

if use_daily_table and not valid_df.empty:
    daily_download = valid_df.copy()
    daily_download["날짜"] = pd.to_datetime(daily_download["날짜"]).dt.strftime("%Y-%m-%d")
    daily_csv = daily_download.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="날짜별 데이터 CSV 다운로드",
        data=daily_csv,
        file_name="날짜별_음식물_쓰레기_발생량.csv",
        mime="text/csv"
    )

with st.expander("🧮 계산 공식 보기"):
    st.markdown("""
    - **감량 전 예상 발생량** = 하루 평균 발생량 × 계산 기간
    - **목표 감량량** = 감량 전 발생량 × 감량 목표 비율 ÷ 100
    - **감량 후 예상 발생량** = 감량 전 발생량 − 목표 감량량

    날짜별 데이터를 입력한 경우에는 입력한 날짜들의 발생량 합계를 기준으로 계산합니다.
    """)
