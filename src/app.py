import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))

from data_loader import load_data, search_books
from components.charts import (
    overview_metrics,
    price_distribution,
    price_vs_rank,
    publisher_ranking,
    publisher_avg_price,
    publication_trend,
    discount_analysis,
    author_top_words,
    price_box_by_publisher,
    rank_range_filter,
)
from components.chatbot import page_chatbot

st.set_page_config(
    page_title="Yes24 IT 모바일 베스트셀러 대시보드",
    page_icon="https://image.yes24.com/sysimage/renew/gnb/favicon_n.ico",
    layout="wide",
)

# ──────────────────────────────────────────────
# 프리미엄 모던 CSS 스타일 주입
# ──────────────────────────────────────────────
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    
    <style>
    /* 글로벌 폰트 및 배경 스타일 */
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e272e 0%, #0f1419 100%);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #f1f2f6 !important;
        font-weight: 500;
    }
    /* 라디오 버튼의 선택 안 된 옵션도 흰색 글씨 보장 */
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        color: #ffffff !important;
        font-weight: 600;
    }
    /* 라디오 옵션 텍스트 색상 및 선택 아이콘 스타일 */
    [data-testid="stSidebar"] [role="radiogroup"] label p {
        color: #f1f2f6 !important;
    }
    
    /* 사이드바 하단 캡션 텍스트 가독성 개선 */
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] .stCaption * {
        color: #a4b0be !important;
        font-weight: 400;
    }
    
    /* 사이드바 데이터 정보 Expander 모던 다크화 */
    [data-testid="stSidebar"] [data-testid="stExpander"] {
        background-color: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 10px !important;
    }
    /* 호버 및 마우스 포커스가 벗어날 때의 모든 상태 배경 투명 고정 */
    [data-testid="stSidebar"] [data-testid="stExpander"]:hover,
    [data-testid="stSidebar"] [data-testid="stExpander"] details,
    [data-testid="stSidebar"] [data-testid="stExpander"] details:hover,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:focus,
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:active {
        background-color: transparent !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] details summary {
        color: #ffffff !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stMarkdownContainer"] li {
        color: #f1f2f6 !important;
    }
    
    /* 메인 카드 스타일링 (글래스모피즘) */
    .modern-card {
        background: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(226, 232, 240, 0.8);
        border-radius: 16px;
        padding: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.03);
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        margin-bottom: 1rem;
    }
    .modern-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0, 0, 0, 0.08);
        border-color: #4a90e2;
    }
    
    /* KPI 전용 모던 디자인 */
    .kpi-wrapper {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #8b9bb4;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }
    .kpi-value {
        font-size: 2.1rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .kpi-accent-bar {
        width: 40px;
        height: 4px;
        border-radius: 2px;
        background: linear-gradient(90deg, #4a90e2 0%, #50e3c2 100%);
        margin-top: 0.6rem;
    }
    
    /* 도서 카드 스타일링 */
    .book-item-container {
        background: #ffffff;
        border-left: 5px solid #4a90e2;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.02);
        margin-bottom: 1.2rem;
        transition: all 0.2s ease-in-out;
    }
    .book-item-container:hover {
        transform: scale(1.01);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_cached_data():
    return load_data()


def render_book_card(row):
    rank = int(row["순위"])
    title = row["제목"]
    author = row["저자"]
    publisher = row["출판사"]
    sale = int(row["판매가_num"])
    original = int(row["정가_num"])
    discount = int(row["할인율_num"])
    pub_date = row["출간일"]
    link = row["링크"]
    img = row["이미지"]

    # 모던한 HTML 카드 렌더링
    st.markdown(
        f"""
        <div class="book-item-container">
            <div style="display: flex; gap: 1.5rem; align-items: center;">
                <div style="font-size: 1.8rem; font-weight: 800; color: #4a90e2; min-width: 40px; text-align: center;">
                    #{rank}
                </div>
                <div style="flex-grow: 1;">
                    <div style="font-size: 1.15rem; font-weight: 700; color: #2c3e50; margin-bottom: 0.3rem;">
                        <a href="{link}" target="_blank" style="text-decoration: none; color: inherit; transition: color 0.2s;">{title}</a>
                    </div>
                    <div style="font-size: 0.85rem; color: #7f8c8d; margin-bottom: 0.5rem;">
                        저자: <b>{author}</b> &nbsp;|&nbsp; 출판사: <b>{publisher}</b> &nbsp;|&nbsp; 출간일: <b>{pub_date}</b>
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.8rem;">
                        <span style="font-size: 1rem; font-weight: 700; color: #2e7d32;">{sale:,}원</span>
                        {f'<span style="font-size: 0.85rem; text-decoration: line-through; color: #95a5a6;">{original:,}원</span>' if original > sale else ''}
                        {f'<span style="background-color: #ffebee; color: #c62828; font-size: 0.75rem; font-weight: 700; padding: 2px 8px; border-radius: 20px;">{discount}% Off</span>' if discount > 0 else ''}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_overview(df):
    st.header("IT 모바일 베스트셀러 개요")
    overview_metrics(df)
    st.divider()
    filtered = rank_range_filter(df)
    col1, col2 = st.columns(2)
    with col1:
        publisher_ranking(filtered)
    with col2:
        publication_trend(filtered)
    st.divider()
    price_distribution(filtered)
    st.divider()
    discount_analysis(filtered)


def page_price_analysis(df):
    st.header("가격 분포 분석")
    overview_metrics(df)
    st.divider()
    price_distribution(df)
    st.divider()
    price_vs_rank(df)
    st.divider()
    price_box_by_publisher(df)
    st.divider()
    discount_analysis(df)


def page_publisher_analysis(df):
    st.header("출판사 분석")
    col1, col2 = st.columns(2)
    with col1:
        n = st.slider("상위 출판사 수", 5, 30, 15, key="pub_n")
        publisher_ranking(df, top_n=n)
    with col2:
        publisher_avg_price(df, top_n=n)
    st.divider()
    price_box_by_publisher(df, top_n=n)
    st.divider()
    author_top_words(df)


def page_search(df):
    st.header("키워드 검색")

    tab_search, tab_advanced = st.tabs(["검색", "고급 검색"])

    with tab_search:
        query = st.text_input(
            "제목 또는 저자로 검색",
            placeholder="예: AI, 클로드, 조태호, 바이브 코딩 ...",
        )
        results = search_books(df, query)
        st.caption(f"검색 결과: **{len(results)}건**")

        if results.empty and query:
            st.info("검색 결과가 없습니다. 다른 키워드를 시도해 보세요.")
        elif not results.empty:
            for _, row in results.head(50).iterrows():
                render_book_card(row)
            if len(results) > 50:
                st.info(f"총 {len(results)}건 중 상위 50건만 표시됩니다.")

    with tab_advanced:
        c1, c2, c3 = st.columns(3)
        with c1:
            min_price = st.number_input("최소 판매가", value=0, step=1000)
        with c2:
            max_price = st.number_input("최대 판매가", value=int(df["판매가_num"].max()), step=1000)
        with c3:
            publisher_filter = st.multiselect(
                "출판사 선택", options=sorted(df["출판사"].unique().tolist())
            )

        col4, col5 = st.columns(2)
        with col4:
            discount_min = st.slider("최소 할인율", 0, 50, 0)
        with col5:
            year_range = st.slider(
                "출간년도 범위",
                min_value=int(df["출간년도"].dropna().min()),
                max_value=int(df["출간년도"].dropna().max()),
                value=(
                    int(df["출간년도"].dropna().min()),
                    int(df["출간년도"].dropna().max()),
                ),
            )

        mask = (
            (df["판매가_num"] >= min_price)
            & (df["판매가_num"] <= max_price)
            & (df["할인율_num"] >= discount_min)
            & (df["출간년도"] >= year_range[0])
            & (df["출간년도"] <= year_range[1])
        )
        if publisher_filter:
            mask &= df["출판사"].isin(publisher_filter)

        adv_results = df[mask]
        st.caption(f"검색 결과: **{len(adv_results)}건**")

        if adv_results.empty:
            st.info("해당 조건에 맞는 도서가 없습니다.")
        else:
            for _, row in adv_results.head(50).iterrows():
                render_book_card(row)
            if len(adv_results) > 50:
                st.info(f"총 {len(adv_results)}건 중 상위 50건만 표시됩니다.")


def page_ranking(df):
    st.header("전체 순위 목록")
    rank_range = st.slider(
        "순위 범위",
        min_value=1,
        max_value=int(df["순위"].max()),
        value=(1, 50),
    )
    filtered = df[(df["순위"] >= rank_range[0]) & (df["순위"] <= rank_range[1])]
    st.caption(f"총 **{len(filtered)}권**")

    display_df = filtered[
        ["순위", "제목", "저자", "출판사", "출간일", "판매가", "정가", "할인율"]
    ].copy()
    st.dataframe(display_df, use_container_width=True, height=600)

    csv_data = filtered.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="선택 범위 CSV 다운로드",
        data=csv_data,
        file_name="yes24_filtered.csv",
        mime="text/csv",
    )


def main():
    df = load_cached_data()

    st.sidebar.title("Yes24 IT 모바일\n베스트셀러 대시보드")
    st.sidebar.markdown("---")
    st.sidebar.caption(f"총 **{len(df):,}권** 도서 데이터")

    page = st.sidebar.radio(
        "페이지 선택",
        ["개요", "가격 분석", "출판사 분석", "키워드 검색", "전체 순위", "📚 챗봇 추천"],
    )

    st.sidebar.markdown("---")
    with st.sidebar.expander("데이터 정보"):
        st.write(f"- 수집 도서 수: {len(df):,}권")
        st.write(f"- 출판사 수: {df['출판사'].nunique():,}곳")
        st.write(f"- 가격 범위: {df['판매가_num'].min():,}~{df['판매가_num'].max():,}원")
        st.write(f"- 출간 기간: {df['출간일'].dropna().min()} ~ {df['출간일'].dropna().max()}")

    if page == "개요":
        page_overview(df)
    elif page == "가격 분석":
        page_price_analysis(df)
    elif page == "출판사 분석":
        page_publisher_analysis(df)
    elif page == "키워드 검색":
        page_search(df)
    elif page == "전체 순위":
        page_ranking(df)
    elif page == "📚 챗봇 추천":
        page_chatbot(df)


if __name__ == "__main__":
    main()
