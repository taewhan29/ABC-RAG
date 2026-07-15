import os
import re
import unicodedata

import pandas as pd


DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CSV_PATH = os.path.join(DATA_DIR, "yes24_it_bestseller.csv")


def _clean_price(value):
    if pd.isna(value) or value == "":
        return 0
    cleaned = re.sub(r"[^\d]", "", str(value))
    return int(cleaned) if cleaned else 0


def _normalize_year(value):
    if pd.isna(value) or value == "":
        return None
    match = re.search(r"(\d{4})", str(value))
    return int(match.group(1)) if match else None


def _normalize_month(value):
    if pd.isna(value) or value == "":
        return None
    match = re.search(r"(\d{4})년\s*(\d{1,2})월", str(value))
    return int(match.group(2)) if match else None


def _extract_year_month(value):
    if pd.isna(value) or value == "":
        return None
    match = re.search(r"(\d{4})년\s*(\d{1,2})월", str(value))
    if match:
        return f"{match.group(1)}-{int(match.group(2)):02d}"
    return None


def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # 원래 CSV 컬럼을 강사님 컴포넌트 규격에 맞춰 매핑 및 가공
    df["제목"] = df["도서명"]
    df["출간일"] = df["출판일"]
    df["링크"] = df["상품번호"].apply(lambda x: f"https://www.yes24.com/Product/Goods/{int(x)}" if pd.notna(x) else "")
    df["이미지"] = ""  # 원래 csv에 이미지 컬럼이 없으므로 빈 값 제공
    
    # 할인율 계산 (원래 csv에 할인율이 없으므로 계산)
    df["할인율"] = df.apply(
        lambda r: round((r["정가"] - r["판매가"]) / r["정가"] * 100, 1)
        if r["정가"] > 0
        else 0.0,
        axis=1,
    )

    df["판매가_num"] = df["판매가"].apply(_clean_price)
    df["정가_num"] = df["정가"].apply(_clean_price)
    df["할인율_num"] = pd.to_numeric(df["할인율"], errors="coerce").fillna(0).astype(int)
    df["출간년도"] = df["출간일"].apply(_normalize_year)
    df["출간월"] = df["출간일"].apply(_normalize_month)
    df["출간년월"] = df["출간일"].apply(_extract_year_month)

    df["제목_정규화"] = df["제목"].apply(
        lambda x: unicodedata.normalize("NFKC", str(x)).lower() if pd.notna(x) else ""
    )
    df["저자_정규화"] = df["저자"].apply(
        lambda x: unicodedata.normalize("NFKC", str(x)).lower() if pd.notna(x) else ""
    )

    return df


def get_top_publishers(df: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    return (
        df["출판사"]
        .value_counts()
        .head(n)
        .reset_index()
        .rename(columns={"index": "출판사", "출판사": "출판사명", "count": "도서 수"})
    )


def search_books(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query or not query.strip():
        return df
    q = unicodedata.normalize("NFKC", query).lower().strip()
    mask = df["제목_정규화"].str.contains(q, na=False) | df["저자_정규화"].str.contains(
        q, na=False
    )
    return df[mask].copy()
