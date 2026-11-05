
import re
from itertools import combinations
from collections import Counter

import pandas as pd
import streamlit as st
import plotly.express as px


# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

CSV_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)

st.title("🍱 급식 규칙 찾기")
st.caption("송탄고 중식 메뉴 연관규칙 분석")


# --------------------------------------------------
# 데이터 불러오기
# --------------------------------------------------

@st.cache_data
def load_data():
    df = pd.read_csv(CSV_URL, encoding="utf-8")

    # 필요한 열 확인
    required_columns = ["날짜", "식사", "메뉴"]

    if not all(col in df.columns for col in required_columns):
        raise ValueError("CSV 파일의 열 구성이 올바르지 않습니다.")

    # 중식만 분석
    df = df[df["식사"] == "중식"].copy()

    # 괄호와 괄호 안의 내용 제거
    def clean_menu(menu):
        menu = str(menu)

        # 일반 괄호 및 전각 괄호 제거
        menu = re.sub(r"\([^)]*\)", "", menu)
        menu = re.sub(r"（[^）]*）", "", menu)

        return menu.strip()

    # 하루 식단을 하나의 거래로 처리
    transactions = []

    for menu_text in df["메뉴"].dropna():
        menus = [
            clean_menu(menu)
            for menu in str(menu_text).split("|")
        ]

        # 빈 메뉴 제거 및 하루 안의 중복 메뉴 제거
        menus = sorted(set(
            menu for menu in menus if menu
        ))

        transactions.append(menus)

    return df, transactions


# --------------------------------------------------
# 연관규칙 분석
# --------------------------------------------------

def analyze_rules(transactions):

    total_days = len(transactions)

    # 메뉴별 등장 횟수
    item_count = Counter()

    # 같은 날 등장한 메뉴 쌍의 횟수
    pair_count = Counter()

    for basket in transactions:

        item_count.update(basket)

        # 하루에 함께 나온 모든 메뉴 쌍
        for a, b in combinations(sorted(set(basket)), 2):
            pair_count[(a, b)] += 1

    # 전체 메뉴 종류
    all_menus = sorted(item_count.keys())

    rules = []

    # 모든 메뉴 쌍에 대해 양방향 규칙 생성
    for (a, b), count in pair_count.items():

        support_ab = count / total_days

        support_a = item_count[a] / total_days
        support_b = item_count[b] / total_days

        # A -> B
        confidence_ab = count / item_count[a]
        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": a,
            "결과": b,
            "동시": count,
            "지지도": support_ab,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B -> A
        confidence_ba = count / item_count[b]
        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": b,
            "결과": a,
            "동시": count,
            "지지도": support_ab,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return all_menus, pair_count, rules_df


# --------------------------------------------------
# 데이터 분석 실행
# --------------------------------------------------

try:
    original_df, transactions = load_data()

    menus, pair_count, rules_df = analyze_rules(transactions)

except Exception as e:
    st.error(f"데이터를 불러오거나 분석하는 중 오류가 발생했습니다: {e}")
    st.stop()


# --------------------------------------------------
# 요약 정보
# --------------------------------------------------

total_days = len(transactions)
total_menus = len(menus)
total_pairs = len(pair_count)

st.markdown("### 📊 분석 데이터 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days:,}일")
col2.metric("메뉴 종류 수", f"{total_menus:,}개")
col3.metric("함께 나온 메뉴 쌍", f"{total_pairs:,}쌍")

st.divider()


# --------------------------------------------------
# 필터 및 정렬
# --------------------------------------------------

st.markdown("### 🔎 연관규칙 검색")

col1, col2 = st.columns(2)

with col1:
    selected_menu = st.selectbox(
        "메뉴 선택",
        options=["전체 메뉴"] + menus,
        index=0
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0
    )


# --------------------------------------------------
# 메뉴 필터링
# --------------------------------------------------

filtered_df = rules_df.copy()

if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu) |
        (filtered_df["결과"] == selected_menu)
    ].copy()


# --------------------------------------------------
# 정렬
# --------------------------------------------------

sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_df = filtered_df.sort_values(
    by=[sort_column, "신뢰도", "동시"],
    ascending=False
).reset_index(drop=True)


# --------------------------------------------------
# 연관규칙 표
# --------------------------------------------------

st.markdown("### 📋 연관규칙 결과")

st.caption(
    "조건 메뉴가 포함된 날 중 결과 메뉴도 함께 나온 비율을 신뢰도로 표시합니다."
)

if filtered_df.empty:

    st.warning("조건에 해당하는 연관규칙이 없습니다.")

else:

    display_df = filtered_df.copy()

    # 표시 형식 설정
    display_df["지지도"] = display_df["지지도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["신뢰도"] = display_df["신뢰도"].map(
        lambda x: f"{x:.2%}"
    )

    display_df["향상도"] = display_df["향상도"].map(
        lambda x: f"{x:.3f}"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )


# --------------------------------------------------
# 향상도 상위 10개 그래프
# --------------------------------------------------

st.divider()

st.markdown("### 📈 향상도 상위 10개 규칙")

if not filtered_df.empty:

    # 향상도 기준 상위 10개
    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=False
        )
        .head(10)
        .copy()
    )

    # 그래프에 표시할 규칙 이름
    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values("향상도", ascending=True)

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10["향상도"].map(lambda x: f"{x:.3f}"),
        labels={
            "향상도": "Lift",
            "규칙": "연관규칙"
        },
        title="향상도(Lift) 상위 10개"
    )

    fig.update_traces(
        textposition="outside",
        marker_color="#4C78A8"
    )

    fig.update_layout(
        height=500,
        yaxis_title="메뉴 규칙",
        xaxis_title="향상도",
        showlegend=False,
        margin=dict(l=20, r=80, t=60, b=30)
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.info("그래프에 표시할 데이터가 없습니다.")


# --------------------------------------------------
# 지표 설명
# --------------------------------------------------

with st.expander("📖 연관규칙 지표 설명"):

    st.markdown("""
    - **조건**: 먼저 등장한 메뉴(A)
    - **결과**: 조건 메뉴와 함께 등장한 메뉴(B)
    - **동시**: A와 B가 같은 날 함께 나온 횟수
    - **지지도(Support)**: 전체 급식 일수 중 A와 B가 함께 나온 비율
    - **신뢰도(Confidence)**: A가 나온 날 중 B도 나온 비율
    - **향상도(Lift)**: A가 나왔을 때 B가 나올 가능성이
      B의 전체 등장 확률에 비해 얼마나 높은지를 나타내는 값

    향상도 해석:

    - 1보다 큼: 두 메뉴가 독립일 때보다 함께 나올 가능성이 높음
    - 1: 두 메뉴가 독립적으로 등장하는 수준
    - 1보다 작음: 두 메뉴가 함께 나올 가능성이 상대적으로 낮음

    ※ 향상도가 높다고 해서 반드시 인과관계가 있는 것은 아닙니다.
    """)
