import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd


COLORS = px.colors.qualitative.Set3


def overview_metrics(df):
    cols = st.columns(4)
    metrics = [
        ("총 도서 수", f"{len(df):,}권"),
        ("평균 판매가", f"{df['판매가_num'].mean():,.0f}원"),
        ("평균 할인율", f"{df['할인율_num'].mean():.1f}%"),
        ("출판사 수", f"{df['출판사'].nunique():,}곳"),
    ]
    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"""
                <div class="modern-card">
                    <div class="kpi-wrapper">
                        <div class="kpi-title">{label}</div>
                        <div class="kpi-value">{value}</div>
                        <div class="kpi-accent-bar"></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def price_distribution(df):
    st.subheader("가격 분포")
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=df["판매가_num"],
            name="판매가",
            opacity=0.7,
            marker_color="#636EFA",
            nbinsx=40,
        )
    )
    fig.add_trace(
        go.Histogram(
            x=df["정가_num"],
            name="정가",
            opacity=0.4,
            marker_color="#EF553B",
            nbinsx=40,
        )
    )
    fig.update_layout(
        barmode="overlay",
        xaxis_title="가격 (원)",
        yaxis_title="도서 수",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=380,
        margin=dict(t=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def price_vs_rank(df):
    st.subheader("순위 vs 판매가 산점도")
    top_df = df.head(100).copy()
    fig = px.scatter(
        top_df,
        x="판매가_num",
        y="순위",
        color="할인율_num",
        size="할인율_num",
        hover_name="제목",
        hover_data={"저자": True, "출판사": True, "판매가_num": ":,.0f"},
        color_continuous_scale="Viridis",
        labels={
            "판매가_num": "판매가 (원)",
            "순위": "베스트셀러 순위",
            "할인율_num": "할인율 (%)",
        },
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=450, margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)


def publisher_ranking(df, top_n=15):
    st.subheader(f"출판사별 도서 수 (Top {top_n})")
    pub_counts = (
        df["출판사"]
        .value_counts()
        .head(top_n)
        .reset_index()
        .rename(columns={"출판사": "출판사명", "count": "도서 수"})
    )
    fig = px.bar(
        pub_counts,
        x="도서 수",
        y="출판사명",
        orientation="h",
        color="도서 수",
        color_continuous_scale="Teal",
        text="도서 수",
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        height=max(350, top_n * 30),
        margin=dict(t=40),
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


def publisher_avg_price(df, top_n=15):
    st.subheader(f"출판사별 평균 판매가 (Top {top_n} 도서)")
    top_pubs = df["출판사"].value_counts().head(top_n).index.tolist()
    filtered = df[df["출판사"].isin(top_pubs)]
    avg_df = (
        filtered.groupby("출판사")["판매가_num"]
        .mean()
        .reset_index()
        .rename(columns={"판매가_num": "평균 판매가"})
        .sort_values("평균 판매가", ascending=True)
    )
    fig = px.bar(
        avg_df,
        x="평균 판매가",
        y="출판사",
        orientation="h",
        color="평균 판매가",
        color_continuous_scale="Oranges",
        text="평균 판매가",
    )
    fig.update_traces(texttemplate="%{text:,.0f}원", textposition="outside")
    fig.update_layout(
        height=max(350, top_n * 30),
        margin=dict(t=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def publication_trend(df):
    st.subheader("출간일 추이")
    valid = df.dropna(subset=["출간년월"]).copy()
    if valid.empty:
        st.info("출간일 정보가 부족합니다.")
        return
    trend = valid.groupby("출간년월").size().reset_index(name="도서 수")
    trend = trend.sort_values("출간년월")
    fig = px.bar(
        trend,
        x="출간년월",
        y="도서 수",
        color="도서 수",
        color_continuous_scale="Blues",
        text="도서 수",
    )
    fig.update_xaxes(title="출간월", tickangle=-45)
    fig.update_yaxes(title="도서 수")
    fig.update_traces(textposition="outside")
    fig.update_layout(height=400, margin=dict(t=40))
    st.plotly_chart(fig, use_container_width=True)


def discount_analysis(df):
    st.subheader("할인율 분포 및 가격 비교")
    col1, col2 = st.columns(2)
    with col1:
        fig = px.histogram(
            df,
            x="할인율_num",
            nbins=20,
            color_discrete_sequence=["#AB63FA"],
            labels={"할인율_num": "할인율 (%)"},
        )
        fig.update_layout(
            title="할인율 분포",
            xaxis_title="할인율 (%)",
            yaxis_title="도서 수",
            height=320,
            margin=dict(t=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        discount_groups = df.copy()
        discount_groups["할인 구간"] = pd.cut(
            discount_groups["할인율_num"],
            bins=[0, 5, 10, 15, 20, 30, 100],
            labels=["~5%", "6~10%", "11~15%", "16~20%", "21~30%", "30%+"],
        )
        grp = (
            discount_groups.groupby("할인 구간", observed=False)
            .agg(평균_판매가=("판매가_num", "mean"), 도서_수=("제목", "count"))
            .reset_index()
        )
        fig2 = px.bar(
            grp,
            x="할인 구간",
            y="평균_판매가",
            color="도서_수",
            color_continuous_scale="Purples",
            text="도서_수",
            labels={"할인 구간": "할인 구간", "평균_판매가": "평균 판매가 (원)"},
        )
        fig2.update_layout(
            title="할인 구간별 평균 판매가",
            height=320,
            margin=dict(t=40),
        )
        fig2.update_traces(texttemplate="%{text}권", textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)


def author_top_words(df):
    st.subheader("저자별 도서 수 (상위 20명)")
    auth_counts = df["저자"].value_counts().head(20).reset_index()
    auth_counts.columns = ["저자", "도서 수"]
    fig = px.bar(
        auth_counts,
        x="도서 수",
        y="저자",
        orientation="h",
        color="도서 수",
        color_continuous_scale="Sunset",
        text="도서 수",
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=max(400, 20 * 28), margin=dict(t=40))
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)


def price_box_by_publisher(df, top_n=10):
    st.subheader(f"출판사별 판매가 박스플롯 (상위 {top_n})")
    top_pubs = df["출판사"].value_counts().head(top_n).index.tolist()
    filtered = df[df["출판사"].isin(top_pubs)].copy()
    fig = px.box(
        filtered,
        x="출판사",
        y="판매가_num",
        color="출판사",
        labels={"판매가_num": "판매가 (원)"},
    )
    fig.update_layout(
        height=400,
        margin=dict(t=40),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def rank_range_filter(df):
    st.subheader("순위별 데이터 필터링")
    rank_min, rank_max = st.slider(
        "순위 범위 선택",
        min_value=1,
        max_value=int(df["순위"].max()),
        value=(1, int(df["순위"].max())),
        step=1,
    )
    return df[(df["순위"] >= rank_min) & (df["순위"] <= rank_max)]
