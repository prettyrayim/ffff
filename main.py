
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

    required_columns = ["날짜", "식사", "메뉴"]

    if not all(col in df.columns for col in required_columns):
        raise ValueError("CSV 파일의 열 구성이 올바르지 않습니다.")

    # 중식만 분석
    df = df[df["식사"] == "중식"].copy()

    # 괄호 및 괄호 안의 내용 제거
    def clean_menu(menu):
        menu = str(menu)

        # 일반 괄호, 전각 괄호 제거
        menu = re.sub(r"\([^()]*\)", "", menu)
        menu = re.sub(r"（[^（）]*）", "", menu)

        return menu.strip()

    transactions = []

    for menu_text in df["메뉴"].dropna():

        menus = [
            clean_menu(menu)
            for menu in str(menu_text).split("|")
        ]

        # 빈 메뉴 제거 및 하루 안의 중복 제거
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

    # 메뉴별 출현 일수
    item_count = Counter()

    # 메뉴 쌍별 동시 출현 일수
    pair_count = Counter()

    for basket in transactions:

        item_count.update(basket)

        for a, b in combinations(sorted(set(basket)), 2):
            pair_count[(a, b)] += 1

    all_menus = sorted(item_count.keys())

    rules = []

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

    return all_menus, item_count, pair_count, rules_df


# --------------------------------------------------
# 데이터 불러오기 및 분석
# --------------------------------------------------

try:
    original_df, transactions = load_data()

    menus, item_count, pair_count, rules_df = analyze_rules(
        transactions
    )

except Exception as e:
    st.error(f"데이터 처리 중 오류가 발생했습니다: {e}")
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
# 연관규칙 검색 및 필터
# --------------------------------------------------

st.markdown("### 🔎 연관규칙 검색")

col1, col2 = st.columns(2)

with col1:
    selected_menu = st.selectbox(
        "좁혀 보기 - 메뉴 선택",
        options=["전체 메뉴"] + menus,
        index=0
    )

with col2:
    sort_option = st.selectbox(
        "정렬 기준",
        options=["향상도 순", "신뢰도 순", "동시 순"],
        index=0
    )


# 최소 동시 출현 일수 슬라이더
min_cooccurrence = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 규칙은 제외합니다."
)


# --------------------------------------------------
# 규칙 필터링
# --------------------------------------------------

filtered_df = rules_df.copy()

# 최소 동시 출현 일수 적용
filtered_df = filtered_df[
    filtered_df["동시"] >= min_cooccurrence
].copy()

# 선택한 메뉴가 조건 또는 결과에 포함된 규칙만 남김
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
# 남은 규칙 개수
# --------------------------------------------------

remaining_rules = len(filtered_df)

st.info(
    f"최소 동시 일수 {min_cooccurrence}일 기준으로 "
    f"표에 남은 규칙은 총 {remaining_rules:,}개입니다."
)


# --------------------------------------------------
# 연관규칙 결과 표
# --------------------------------------------------

st.markdown("### 📋 연관규칙 결과")

st.caption(
    "조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율을 신뢰도로 표시합니다."
)

if filtered_df.empty:

    st.warning("조건에 해당하는 연관규칙이 없습니다.")

else:

    display_df = filtered_df.copy()

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

    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "신뢰도", "동시"],
            ascending=False
        )
        .head(10)
        .copy()
    )

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text=top10["향상도"].map(
            lambda x: f"{x:.3f}"
        ),
        labels={
            "향상도": "Lift",
            "규칙": "연관규칙"
        },
        title="향상도 상위 10개"
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
        margin=dict(
            l=20,
            r=80,
            t=60,
            b=30
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:
    st.info("그래프에 표시할 데이터가 없습니다.")


# --------------------------------------------------
# 함께 나온 적 없는 짝
# --------------------------------------------------

st.divider()

st.markdown("### 🚫 함께 나온 적 없는 짝")

st.write(
    "메뉴 하나를 선택하면 해당 메뉴와 같은 날 한 번도 함께 "
    "나오지 않았으면서, 혼자서는 10일 이상 등장한 메뉴를 찾습니다."
)

# 기존 좁혀 보기와 별개인 메뉴 선택
selected_menu_for_absence = st.selectbox(
    "함께 나온 적 없는 짝 찾기 - 기준 메뉴 선택",
    options=menus,
    index=0,
    key="absence_menu_selector"
)

# 선택 메뉴가 등장한 일수
selected_menu_days = item_count[selected_menu_for_absence]

# 선택 메뉴와 함께 등장한 적이 있는 메뉴 목록
cooccurred_menus = set()

for basket in transactions:

    if selected_menu_for_absence in basket:

        cooccurred_menus.update(basket)

# 자기 자신은 제외
cooccurred_menus.discard(selected_menu_for_absence)

# 함께 나온 적 없는 메뉴 중 10일 이상 등장한 메뉴
absence_results = []

for menu in menus:

    if menu == selected_menu_for_absence:
        continue

    # 한 번도 함께 나온 적 없어야 함
    if menu in cooccurred_menus:
        continue

    # 해당 메뉴 자체는 10일 이상 등장해야 함
    days = item_count[menu]

    if days >= 10:

        absence_results.append({
            "메뉴": menu,
            "메뉴 등장 일수": days,
            f"'{selected_menu_for_absence}' 등장 일수": selected_menu_days
        })


# 등장 일수가 많은 순으로 정렬
absence_df = pd.DataFrame(absence_results)

if not absence_df.empty:

    absence_df = absence_df.sort_values(
        by=["메뉴 등장 일수", "메뉴"],
        ascending=[False, True]
    ).reset_index(drop=True)

    st.info(
        f"선택한 메뉴 '{selected_menu_for_absence}'는 "
        f"총 {selected_menu_days}일 등장했습니다. "
        f"함께 나온 적 없는 짝은 {len(absence_df)}개입니다."
    )

    st.dataframe(
        absence_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info(
        f"'{selected_menu_for_absence}'와 한 번도 함께 나오지 않았고 "
        "10일 이상 등장한 메뉴가 없습니다."
    )


# --------------------------------------------------
# 지표 설명
# --------------------------------------------------

with st.expander("📖 연관규칙 지표 설명"):

    st.markdown("""
    - **조건**: 먼저 등장한 메뉴(A)
    - **결과**: 조건 메뉴와 함께 등장한 메뉴(B)
    - **동시**: A와 B가 같은 날 함께 나온 횟수
    - **지지도(Support)**: 전체 급식 일수 중 A와 B가 함께 나온 비율
    - **신뢰도(Confidence)**: A가 나온 날 중 B도 함께 나온 비율
    - **향상도(Lift)**: A가 나왔을 때 B가 나올 가능성이
      B의 전체 등장 확률에 비해 얼마나 높은지를 나타내는 값

    ### 향상도 해석

    - 1보다 큼: 독립적으로 등장할 때보다 함께 나올 가능성이 높음
    - 1: 두 메뉴가 독립적으로 등장하는 수준
    - 1보다 작음: 함께 나올 가능성이 상대적으로 낮음

    ### 함께 나온 적 없는 짝

    - 선택 메뉴와 동시 출현 횟수가 0인 메뉴만 표시합니다.
    - 해당 메뉴 자체는 10일 이상 등장해야 합니다.
    - 메뉴 등장 일수가 많은 순서로 정렬합니다.

    ※ 향상도는 연관성을 나타내며 인과관계를 의미하지 않습니다.
    """)
