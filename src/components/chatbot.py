import re
import json
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
6. 링크 형식: [상세보기](URL) - 반드시 실제 URL을 사용하세요.
7. 유사도가 낮은 책은 추천하지 말아주세요."""

PARSE_PROMPT = """사용자의 질문을 분석하여 도서 검색을 위한 수치형 조건과 키워드를 JSON 형식으로 추출해 주세요.
반드시 아래 JSON 스키마를 만족하는 올바른 JSON 문자열만 반환해야 하며, 부가적인 설명이나 마크다운 코드 블록 기호(예: ```json)는 절대로 쓰지 마세요.

JSON 스키마:
{{
    "min_price": int or null (최소 가격, 언급 없거나 제한 없으면 null),
    "max_price": int or null (최대 가격, 언급 없거나 제한 없으면 null),
    "min_sale_index": int or null (최소 판매지수, 언급 없거나 제한 없으면 null),
    "max_sale_index": int or null (최대 판매지수, 언급 없거나 제한 없으면 null),
    "sort_by": "price" or "sale_index" or "rank" or null (정렬 기준 컬럼. 가격/판매가/비용 등은 "price", 판매지수/인기/판매량 등은 "sale_index", 순위/베스트셀러 순위 등은 "rank", 정렬에 대한 언급이 전혀 없으면 null),
    "sort_order": "asc" or "desc" or null (오름차순 또는 내림차순. 싼 가격순/오름차순 등은 "asc", 비싼 가격순/판매지수 높은순/인기순/내림차순 등은 "desc", 정렬 방향이 모호하면 null),
    "keywords": string or null (검색하고자 하는 주요 도서 키워드나 주제, 예: "파이썬", "인공지능", "클로드" 등. 단, 가격이나 판매지수 수치와 관련된 단어는 제외하고 책 내용과 관련된 키워드만 추출. 언급 없으면 null)
}}

예시 1: "2만원 이하인 책 중 가장 인기있는거"
응답: {{"min_price": 0, "max_price": 20000, "min_sale_index": null, "max_sale_index": null, "sort_by": "sale_index", "sort_order": "desc", "keywords": null}}

예시 2: "판매지수가 50000 넘는 인공지능 관련 도서 추천"
응답: {{"min_price": null, "max_price": null, "min_sale_index": 50000, "max_sale_index": null, "sort_by": "sale_index", "sort_order": "desc", "keywords": "인공지능"}}

예시 3: "가격이 저렴한 순으로 클로드 책 보여줘"
응답: {{"min_price": null, "max_price": null, "min_sale_index": null, "max_sale_index": null, "sort_by": "price", "sort_order": "asc", "keywords": "클로드"}}

질문: {user_input}
응답:"""


def _build_book_context(similar_books: list[dict]) -> str:
    """검색된 유사 도서 목록을 LLM 컨텍스트로 전달하기 위한 마크다운 텍스트로 빌드합니다.

    Args:
        similar_books: ChromaDB 또는 직접 검색된 유사 도서 정보 리스트.

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

        sale_index_str = f" | 판매지수: {row['sale_index']:,}" if "sale_index" in row and row["sale_index"] > 0 else ""

        lines.append(
            f"- [순위 {row['rank']}] {row['title']} | 저자: {row['author']} | "
            f"출판사: {row['publisher']} | 출간일: {row['pub_date']} | "
            f"가격: {price_str}{sale_index_str} | 링크: {link} | 매칭 유사도: {similarity:.2%}"
        )
    return "\n".join(lines)


def parse_numeric_conditions(client: Groq, user_input: str, model: str) -> dict:
    """사용자의 자연어 질문에서 가격 범위, 판매지수 범위, 정렬 조건, 키워드를 JSON으로 파싱합니다.

    Args:
        client: Groq 클라이언트 객체.
        user_input: 사용자의 질문 텍스트.
        model: 분석에 사용할 LLM 모델명.

    Returns:
        dict: 파싱된 조건 정보를 담은 딕셔너리.
    """
    try:
        prompt = PARSE_PROMPT.format(user_input=user_input)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=512,
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
            
        return json.loads(content)
    except Exception as e:
        return {
            "min_price": None,
            "max_price": None,
            "min_sale_index": None,
            "max_sale_index": None,
            "sort_by": None,
            "sort_order": None,
            "keywords": None
        }


def query_books_by_numeric_conditions(df: pd.DataFrame, conditions: dict) -> list[dict]:
    """추출된 수치 필터 및 정렬 조건에 따라 데이터프레임에서 직접 도서를 검색합니다.

    Args:
        df: 도서 데이터프레임.
        conditions: 파싱된 조건 정보 딕셔너리.

    Returns:
        list[dict]: 조건에 매칭되는 상위 5권의 도서 목록.
    """
    filtered_df = df.copy()

    # 가격 조건 적용
    if conditions.get("min_price") is not None:
        filtered_df = filtered_df[filtered_df["판매가_num"] >= conditions["min_price"]]
    if conditions.get("max_price") is not None:
        filtered_df = filtered_df[filtered_df["판매가_num"] <= conditions["max_price"]]

    # 판매지수 조건 적용
    if conditions.get("min_sale_index") is not None:
        filtered_df = filtered_df[filtered_df["판매지수_num"] >= conditions["min_sale_index"]]
    if conditions.get("max_sale_index") is not None:
        filtered_df = filtered_df[filtered_df["판매지수_num"] <= conditions["max_sale_index"]]

    # 키워드 조건 적용
    if conditions.get("keywords"):
        import unicodedata
        keyword = unicodedata.normalize("NFKC", str(conditions["keywords"])).lower().strip()
        
        # 부제목 컬럼 결측치 핸들링
        subtitle_mask = filtered_df["부제목"].fillna("").apply(
            lambda x: keyword in unicodedata.normalize("NFKC", str(x)).lower()
        )
        
        filtered_df = filtered_df[
            filtered_df["제목_정규화"].str.contains(keyword, na=False) |
            filtered_df["저자_정규화"].str.contains(keyword, na=False) |
            subtitle_mask
        ]

    # 정렬 조건 적용
    sort_by = conditions.get("sort_by")
    sort_order = conditions.get("sort_order")
    
    ascending = True
    if sort_order == "desc":
        ascending = False

    if sort_by == "price":
        filtered_df = filtered_df.sort_values(by="판매가_num", ascending=ascending)
    elif sort_by == "sale_index":
        filtered_df = filtered_df.sort_values(by="판매지수_num", ascending=ascending)
    elif sort_by == "rank":
        filtered_df = filtered_df.sort_values(by="순위", ascending=ascending)
    else:
        if conditions.get("min_sale_index") is not None:
            filtered_df = filtered_df.sort_values(by="판매지수_num", ascending=False)
        elif conditions.get("min_price") is not None or conditions.get("max_price") is not None:
            filtered_df = filtered_df.sort_values(by="판매가_num", ascending=True)

    top_books = filtered_df.head(5)
    
    similar_books = []
    for rank_idx, (_, row) in enumerate(top_books.iterrows(), 1):
        similar_books.append({
            "title": row["제목"],
            "author": row["저자"],
            "publisher": row["출판사"],
            "pub_date": row["출간일"],
            "price_sale": row["판매가_num"],
            "price_original": row["정가_num"],
            "discount_rate": row["할인율_num"],
            "rank": row["순위"],
            "link": row["링크"],
            "similarity": 1.0,
            "sale_index": row["판매지수_num"]
        })
    return similar_books


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
    is_numeric_query = False
    applied_filters = []
    try:
        client = Groq(api_key=api_key)
        with st.spinner("🔍 질문 분석 중..."):
            conditions = parse_numeric_conditions(client, user_input, model)
        
        has_min_price = conditions.get("min_price") is not None
        has_max_price = conditions.get("max_price") is not None
        has_min_sale = conditions.get("min_sale_index") is not None
        has_max_sale = conditions.get("max_sale_index") is not None
        has_sort = conditions.get("sort_by") is not None
        
        if has_min_price or has_max_price or has_min_sale or has_max_sale or has_sort:
            is_numeric_query = True
            if has_min_price and has_max_price:
                applied_filters.append(f"가격: {conditions['min_price']:,}원 ~ {conditions['max_price']:,}원")
            elif has_min_price:
                applied_filters.append(f"가격: {conditions['min_price']:,}원 이상")
            elif has_max_price:
                applied_filters.append(f"가격: {conditions['max_price']:,}원 이하")
                
            if has_min_sale and has_max_sale:
                applied_filters.append(f"판매지수: {conditions['min_sale_index']:,} ~ {conditions['max_sale_index']:,}")
            elif has_min_sale:
                applied_filters.append(f"판매지수: {conditions['min_sale_index']:,} 이상")
            elif has_max_sale:
                applied_filters.append(f"판매지수: {conditions['max_sale_index']:,} 이하")
                
            if has_sort:
                sort_by_map = {"price": "가격순", "sale_index": "판매지수순", "rank": "순위순"}
                order_map = {"asc": "오름차순", "desc": "내림차순"}
                sort_str = sort_by_map.get(conditions['sort_by'], conditions['sort_by'])
                order_str = order_map.get(conditions['sort_order'], "")
                applied_filters.append(f"정렬: {sort_str} {order_str}")
                
            if conditions.get("keywords"):
                applied_filters.append(f"키워드: '{conditions['keywords']}'")
                
        if is_numeric_query:
            with st.spinner("📊 수치 조건에 맞는 도서를 직접 필터링하고 있습니다..."):
                similar_books = query_books_by_numeric_conditions(df, conditions)
                response = chat_with_groq(client, similar_books, user_input, model)
        else:
            with st.spinner("🔍 관련 도서를 벡터 공간에서 검색하고 있습니다..."):
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
        title_suffix = " (수치 필터 매칭 순)" if is_numeric_query else " (의미론적 유사도 순)"
        with st.expander(f"🔗 추천 도서 빠른 링크{title_suffix}", expanded=False):
            if is_numeric_query and applied_filters:
                st.info(f"⚙️ **적용된 필터 조건:** {', '.join(applied_filters)}")
            for book in similar_books:
                sale_index_info = f" | `판매지수: {book['sale_index']:,}`" if "sale_index" in book and book["sale_index"] > 0 else ""
                st.markdown(
                    f"📖 [{book['title']}]({book['link']}) &nbsp;&nbsp; "
                    f"`순위 #{book['rank']}` | `유사도: {book['similarity']:.2%}`{sale_index_info}"
                )
