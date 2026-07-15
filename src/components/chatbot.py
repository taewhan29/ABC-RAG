import re

import pandas as pd
import streamlit as st
from groq import Groq


SYSTEM_PROMPT = """당신은 Yes24 IT 모바일 베스트셀러 도서 추천 어시스턴트입니다.
사용자의 질문을 분석하여 관련 도서를 추천해 줍니다.

규칙:
1. 제공된 도서 목록(context)에서 사용자 질문과 관련된 도서를 찾아 추천합니다.
2. 추천할 도서가 있으면 각 도서의 제목, 저자, 출판사, 가격, 그리고 [상세보기](링크) 형식으로 링크를 포함하여 답변합니다.
3. 추천할 도서가 없다면 "현재 데이터베이스에 해당 조건의 도서는 없습니다."라고 솔직하게 답변합니다.
4. 답변은 한국어로 작성합니다.
5. 마크다운 형식을 활용하여 가독성 있게 답변합니다.
6. 링크 형식: [상세보기](URL) - 반드시 실제 URL을 사용하세요."""


def _build_book_context(df: pd.DataFrame, query: str, max_items: int = 30) -> str:
    if df.empty:
        return ""

    keywords = re.findall(r"[\w가-힣]+", query.lower())
    if not keywords:
        top = df.head(max_items)
    else:
        mask = pd.Series([False] * len(df))
        for kw in keywords:
            mask |= df["제목"].str.contains(kw, case=False, na=False)
            mask |= df["저자"].str.contains(kw, case=False, na=False)
            mask |= df["출판사"].str.contains(kw, case=False, na=False)
        matched = df[mask]
        if matched.empty:
            top = df.head(max_items)
        else:
            top = matched.head(max_items)

    lines = []
    for _, row in top.iterrows():
        sale = int(row["판매가_num"])
        original = int(row["정가_num"])
        discount = int(row["할인율_num"])
        link = row["링크"]
        price_str = f"{sale:,}원"
        if original > sale:
            price_str += f" (정가 {original:,}원, {discount}% 할인)"
        else:
            price_str += f" (정가 {original:,}원)"
        lines.append(
            f"- 순위 {row['순위']}: {row['제목']} | 저자: {row['저자']} | "
            f"출판사: {row['출판사']} | 출간일: {row['출간일']} | "
            f"가격: {price_str} | 링크: {link}"
        )
    return "\n".join(lines)


def chat_with_groq(client: Groq, df: pd.DataFrame, query: str, model: str) -> str:
    context = _build_book_context(df, query)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"다음은 Yes24 IT 모바일 베스트셀러 도서 목록입니다:\n\n{context}\n\n---\n\n사용자 질문: {query}",
        },
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def render_chat_message(role: str, content: str):
    with st.chat_message(role, avatar="📚" if role == "assistant" else "👤"):
        st.markdown(content, unsafe_allow_html=True)


def page_chatbot(df: pd.DataFrame):
    st.header("📚 도서 추천 챗봇")

    with st.sidebar:
        st.markdown("---")
        st.subheader("⚙️ 챗봇 설정")
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="gsk_...",
            help="https://console.groq.com 에서 API Key를 발급받으세요.",
        )
        model = st.selectbox(
            "모델 선택",
            [
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
                "gemma2-9b-it",
            ],
            index=0,
        )

    if not api_key:
        st.info("🔑 사이드바에서 Groq API Key를 입력해 주세요.")
        st.markdown("""
        ### 사용법
        1. [Groq Console](https://console.groq.com)에서 API Key를 발급받으세요
        2. 사이드바에 API Key를 입력하세요
        3. 질문을 입력하면 관련 도서를 추천해 드립니다

        **예시 질문:**
        - "AI 관련 책 추천해줘"
        - "Python 배우기 좋은 책 있어?"
        - "바이브 코딩에 대한 책 추천"
        - "가성비 좋은 IT 책 추천해줘"
        - "클로드 관련 책 있어?"
        """)
        return

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        render_chat_message(msg["role"], msg["content"])

    user_input = st.chat_input("IT 도서에 대해 질문해 보세요...")
    if not user_input:
        return

    render_chat_message("user", user_input)
    st.session_state.chat_messages.append({"role": "user", "content": user_input})

    try:
        client = Groq(api_key=api_key)
        with st.spinner("🔍 관련 도서를 검색하고 있습니다..."):
            response = chat_with_groq(client, df, user_input, model)
    except Exception as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {str(e)}"
        render_chat_message("assistant", error_msg)
        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
        return

    render_chat_message("assistant", response)
    st.session_state.chat_messages.append({"role": "assistant", "content": response})

    matched = _build_book_context(df, user_input, max_items=5)
    if matched:
        with st.expander("🔗 추천 도서 빠른 링크", expanded=False):
            for line in matched.strip().split("\n"):
                line = line.strip().lstrip("- ")
                parts = line.split(" | ")
                title_part = parts[0] if parts else ""
                link_part = [p for p in parts if p.startswith("링크: ")]
                if link_part:
                    url = link_part[0].replace("링크: ", "")
                    title_text = title_part.split(": ", 1)[-1] if ": " in title_part else title_part
                    st.markdown(f"📖 [{title_text}]({url})")
