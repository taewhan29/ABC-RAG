import re
import pandas as pd
import streamlit as st
from groq import Groq
from vector_db import search_similar_books, init_vector_db

SYSTEM_PROMPT = """당신은 Yes24 IT 모바일 베스트셀러 도서 추천 어시스턴트입니다.
사용자의 질문을 분석하여 관련 도서를 추천해 줍니다.

규칙:
1. 제공된 도서 목록(context)에서 사용자 질문과 관련된 도서를 찾아 추천합니다.
2. 추천할 도서가 있으면 각 도서의 제목, 저자, 출판사, 가격, 그리고 [상세보기](링크) 형식으로 링크를 포함하여 답변합니다.
3. 추천할 도서가 없다면 "현재 데이터베이스에 해당 조건의 도서는 없습니다."라고 솔직하게 답변합니다.
4. 답변은 한국어로 작성합니다.
5. 마크다운 형식을 활용하여 가독성 있게 답변합니다.
6. 링크 형식: [상세보기](URL) - 반드시 실제 URL을 사용하세요."""


def _build_book_context(similar_books: list[dict]) -> str:
    """검색된 유사 도서 목록을 LLM 컨텍스트로 전달하기 위한 마크다운 텍스트로 빌드합니다.

    Args:
        similar_books: ChromaDB에서 검색된 유사 도서 정보 리스트.

    Returns:
        str: 마크다운 리스트 형태의 컨텍스트 문자열.
    """
    lines = []
    for row in similar_books:
        sale = row["price_sale"]
        original = row["price_original"]
        discount = row["discount_rate"]
        link = row["link"]
        similarity = row["similarity"]

        price_str = f"{sale:,}원"
        if original > sale:
            price_str += f" (정가 {original:,}원, {discount}% 할인)"
        else:
            price_str += f" (정가 {original:,}원)"

        lines.append(
            f"- [순위 {row['rank']}] {row['title']} | 저자: {row['author']} | "
            f"출판사: {row['publisher']} | 출간일: {row['pub_date']} | "
            f"가격: {price_str} | 링크: {link} | 매칭 유사도: {similarity:.2%}"
        )
    return "\n".join(lines)


def chat_with_groq(client: Groq, similar_books: list[dict], query: str, model: str) -> str:
    """ChromaDB 검색 결과를 컨텍스트로 활용해 Groq API로 챗봇 답변을 생성합니다.

    Args:
        client: Groq 클라이언트 객체.
        similar_books: 검색된 유사 도서 리스트.
        query: 사용자 질문.
        model: 적용할 LLM 모델명.

    Returns:
        str: 생성된 챗봇 답변 텍스트.
    """
    context = _build_book_context(similar_books)

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
    """사용자와 챗봇의 대화 메시지를 Streamlit UI로 렌더링합니다.

    Args:
        role: 메시지 발신 주체 ('user' 또는 'assistant').
        content: 출력할 메시지 내용.
    """
    with st.chat_message(role, avatar="📚" if role == "assistant" else "👤"):
        st.markdown(content, unsafe_allow_html=True)


def page_chatbot(df: pd.DataFrame):
    """도서 추천 챗봇 페이지를 렌더링합니다.

    최초 기동 시 ChromaDB 연결 및 모델 로딩을 안전하게 초기화하며,
    사용자 대화 흐름(RAG Rerank 검색 및 LLM 대화)을 관리합니다.

    Args:
        df: 원본 도서 데이터프레임.
    """
    st.header("📚 도서 추천 챗봇")

    # 벡터 DB 초기화 및 상태 점검
    with st.spinner("🤖 벡터 데이터베이스 및 AI 모델을 연결하고 있습니다. 최초 실행 시 다소 시간이 소요될 수 있습니다..."):
        try:
            collection = init_vector_db()
            db_count = collection.count()
        except Exception as e:
            st.error(f"데이터베이스 연결 중 오류가 발생했습니다: {str(e)}")
            return

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

        # 프리미엄 벡터 DB 상태 정보 제공 UI
        st.markdown("### 📊 벡터 DB 상태")
        st.success("데이터베이스 연결 완료")
        st.caption(f"**적재된 도서**: {db_count:,} 권")
        st.caption("**임베딩 모델**: klue/bert-base (768차원)")

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

    # 최신 대답과 연관 도서 추천을 받기 위한 변수 초기화
    similar_books = []
    try:
        client = Groq(api_key=api_key)
        with st.spinner("🔍 관련 도서를 벡터 공간에서 검색하고 있습니다..."):
            # ChromaDB로부터 가장 연관성이 높은 도서 5권 검색 (RAG)
            similar_books = search_similar_books(user_input, top_n=5)
            response = chat_with_groq(client, similar_books, user_input, model)
    except Exception as e:
        error_msg = f"API 호출 중 오류가 발생했습니다: {str(e)}"
        render_chat_message("assistant", error_msg)
        st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})
        return

    render_chat_message("assistant", response)
    st.session_state.chat_messages.append({"role": "assistant", "content": response})

    # 빠른 바로가기 링크 및 매칭 정보 UI 렌더링
    if similar_books:
        with st.expander("🔗 추천 도서 빠른 링크 (의미론적 유사도 순)", expanded=False):
            for book in similar_books:
                st.markdown(
                    f"📖 [{book['title']}]({book['link']}) &nbsp;&nbsp; "
                    f"`순위 #{book['rank']}` | `유사도: {book['similarity']:.2%}`"
                )
age("assistant", error_msg)
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
