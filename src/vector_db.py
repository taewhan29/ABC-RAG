"""Yes24 IT 모바일 베스트셀러 데이터를 ChromaDB 벡터 데이터베이스로 관리하고 유사 도서 검색을 제공하는 모듈.

이 모듈은 klue/bert-base 모델을 로드하여 사용자의 질의를 실시간 임베딩하고,
data 디렉토리에 정의된 vectors.tsv와 yes24_it_bestseller.csv를 기반으로
ChromaDB 데이터베이스에 적재 및 조회하는 기능을 전담합니다.
"""

import os
import pandas as pd
import numpy as np
import chromadb
from data_loader import load_data

# 경로 설정
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(SRC_DIR), "data")
VECTORS_PATH = os.path.join(DATA_DIR, "vectors.tsv")

# 지연 초기화를 위한 전역 변수
_MODEL = None
_TOKENIZER = None


def _get_embedding_model():
    """klue/bert-base 임베딩 모델과 토크나이저를 지연 초기화하여 반환합니다.

    Returns:
        tuple: (Transformers 모델 객체, Transformers 토크나이저 객체)
    """
    global _MODEL, _TOKENIZER
    if _MODEL is None or _TOKENIZER is None:
        import torch
        from transformers import AutoModel, AutoTokenizer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_name = "klue/bert-base"
        _TOKENIZER = AutoTokenizer.from_pretrained(model_name)
        _MODEL = AutoModel.from_pretrained(model_name).to(device)
    return _MODEL, _TOKENIZER


def get_query_embedding(query: str) -> list[float]:
    """사용자가 입력한 질의 문장을 klue/bert-base [CLS] 토큰 벡터로 임베딩합니다.

    Args:
        query: 질문 또는 검색어 문자열.

    Returns:
        list[float]: 768차원의 플로트 리스트 형식 벡터.
    """
    import torch

    model, tokenizer = _get_embedding_model()
    device = next(model.parameters()).device

    # 문장 토크나이징 및 디바이스 업로드
    inputs = tokenizer(
        query,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512
    ).to(device)

    # 모델 추론을 통해 CLS 토큰 임베딩 획득
    with torch.no_grad():
        outputs = model(**inputs)

    # [CLS] 토큰 위치는 인덱스 0번
    emb = outputs.last_hidden_state[0, 0].cpu().numpy()
    return emb.tolist()


def init_vector_db() -> chromadb.Collection:
    """ChromaDB 로컬 벡터 데이터베이스를 초기화하고 도서 데이터를 적재합니다.

    최초 1회 실행 시 `data/vectors.tsv`와 `yes24_it_bestseller.csv`를 1:1로 매칭하여
    ChromaDB `yes24_books` 컬렉션에 적재하며, 이후 실행 시에는 적재 단계를 스킵합니다.

    Returns:
        chromadb.Collection: 초기화된 ChromaDB 컬렉션 객체.
    """
    # PersistentClient 생성
    client = chromadb.PersistentClient(path=os.path.join(DATA_DIR, "chromadb_store"))

    # 코사인 유사도 측정을 위해 cosine space로 컬렉션 생성
    collection = client.get_or_create_collection(
        name="yes24_books",
        metadata={"hnsw:space": "cosine"}
    )

    # 도서 메타데이터 로드
    df = load_data()

    # 데이터가 이미 모두 로드되어 있다면 적재 과정 스킵 (동적으로 데이터 크기 비교)
    if collection.count() >= len(df):
        return collection

    # 기존 저장된 768차원 임베딩 로드
    vectors = pd.read_csv(VECTORS_PATH, sep="\t", header=None).values

    ids = []
    embeddings = []
    metadatas = []
    documents = []

    for idx, row in df.iterrows():
        # ChromaDB 메타데이터 구축 (nested 객체나 null은 배제하고 string, int, float으로 타입 정제)
        meta = {
            "title": str(row["제목"]) if pd.notna(row["제목"]) else "",
            "author": str(row["저자"]) if pd.notna(row["저자"]) else "",
            "publisher": str(row["출판사"]) if pd.notna(row["출판사"]) else "",
            "pub_date": str(row["출간일"]) if pd.notna(row["출간일"]) else "",
            "price_sale": int(row["판매가_num"]) if pd.notna(row["판매가_num"]) else 0,
            "price_original": int(row["정가_num"]) if pd.notna(row["정가_num"]) else 0,
            "discount_rate": int(row["할인율_num"]) if pd.notna(row["할인율_num"]) else 0,
            "rank": int(row["순위"]) if pd.notna(row["순위"]) else 0,
            "link": str(row["링크"]) if pd.notna(row["링크"]) else "",
        }

        ids.append(f"book_{idx}")
        embeddings.append(vectors[idx].tolist())
        metadatas.append(meta)
        documents.append(str(row["제목"]))

    # 데이터 일괄 적재 (중복 방지를 위해 upsert 사용)
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents
    )

    return collection


def search_similar_books(query: str, top_n: int = 5) -> list[dict]:
    """사용자 질의와 의미적으로 유사한 도서를 ChromaDB에서 조회하여 목록을 반환합니다.

    Args:
        query: 사용자 질문.
        top_n: 가져올 도서 수 (기본값 5).

    Returns:
        list[dict]: 검색된 도서 메타데이터와 유사도를 담은 딕셔너리 목록.
    """
    collection = init_vector_db()

    # 질문 임베딩 생성
    query_vector = get_query_embedding(query)

    # 유사 벡터 조회
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_n
    )

    formatted_results = []
    if results and "metadatas" in results and results["metadatas"]:
        metadatas = results["metadatas"][0]
        # distances[0]은 코사인 거리이므로, 1 - distance를 취해 유사도로 변환
        distances = results["distances"][0] if "distances" in results else [0.0] * len(metadatas)

        for meta, dist in zip(metadatas, distances):
            similarity = 1.0 - float(dist)
            formatted_results.append({
                "title": meta.get("title", ""),
                "author": meta.get("author", ""),
                "publisher": meta.get("publisher", ""),
                "pub_date": meta.get("pub_date", ""),
                "price_sale": meta.get("price_sale", 0),
                "price_original": meta.get("price_original", 0),
                "discount_rate": meta.get("discount_rate", 0),
                "rank": meta.get("rank", 0),
                "link": meta.get("link", ""),
                "similarity": similarity
            })

    return formatted_results
