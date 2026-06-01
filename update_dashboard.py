import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

DRIVE_FOLDER_ID = "1MRKdVhxdUEZFmbje7h0T6oulf8T4il7P"
SERVICE_ACCOUNT_FILE = "service_account.json"
DASHBOARD_HTML = "index.html"

ITEM_NAME_MAP = {
    "\ube0c\ub8e8\ud074\ub9b0": "\ube0c\ub8e8\ud074\ub9b0 475ml",
    "\uace8\ub4e0\uc5d0\ub77c": "\uace8\ub4e0\uc5d0\ub77c 475ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \ub2e4\ud06c \ube14\ub80c\ub4dc, 750ml": "\uc5d0\uc2a4\ud504\ub808\uc18c 750ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \ub2e4\ud06c \ube14\ub80c\ub4dc, 900ml": "\uc5d0\uc2a4\ud504\ub808\uc18c 900ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778, 475ml": "\uc5d0\uc2a4\ud504\ub808\uc18c \ub514\uce74\ud398\uc778 475ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778, 750ml": "\uc5d0\uc2a4\ud504\ub808\uc18c \ub514\uce74\ud398\uc778 750ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778, 900ml": "\uc5d0\uc2a4\ud504\ub808\uc18c \ub514\uce74\ud398\uc778 900ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561 \uc5d1\uc2a4\uc624": "\uc5d0\uc2a4\ud504\ub808\uc18c \uc5d1\uc2a4\uc624 400ml",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ud30c\uc6b0\ub354 \ucee4\ud53c": "\ud30c\uc6b0\ub354 \ucee4\ud53c \uc5d0\uc2a4\ud504\ub808\uc18c 30g",
    "\uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561, 1\uac1c, 400ml": "\uc5b8\ub354\ud504\ub808\uc154 \uc5d0\uc2a4\ud504\ub808\uc18c 400ml",
    "\uace0\ub18d\ub3c4 \uc5d0\uc2a4\ud504\ub808\uc18c \ucee4\ud53c\uc6d0\uc561": "10\ube0c\ub9ad\uc2a4 \uc5d0\uc2a4\ud504\ub808\uc18c 200ml",
    "\ube14\ub799 \uc564 \ud654\uc774\ud2b8 \ucee4\ud53c\uc6d0\uc561 \uc624\ub9ac\uc9c0\ub110": "\ube14\ub799\uc564\ud654\uc774\ud2b8 \uc624\ub9ac\uc9c0\ub110 200ml",
    "\ube14\ub799 \uc564 \ud654\uc774\ud2b8 \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778": "\ube14\ub799\uc564\ud654\uc774\ud2b8 \ub514\uce74\ud398\uc778 200ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ucf00\ub0d0, 500ml": "\ucf00\ub0d0 500ml",
    "\ub0c9\uc7a5 \ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ucf00\ub0d0, 500ml": "\ucf00\ub0d0 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8\uc6d0\uc561 \ucf00\ub0d0, 750ml": "\ucf00\ub0d0 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \ucf00\ub0d0, 1L": "\ucf00\ub0d0 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8\uc6d0\uc561 \uc608\uac00\uccb4\ud504, 500ml": "\uc608\uac00\uccb4\ud504 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \uc608\uac00\uccb4\ud504, 750ml": "\uc608\uac00\uccb4\ud504 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \uc608\uac00\uccb4\ud504, 1L": "\uc608\uac00\uccb4\ud504 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8\uc6d0\uc561 \uacfc\ud14c\ub9d0\ub77c, 500ml": "\uacfc\ud14c\ub9d0\ub77c 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \uacfc\ud14c\ub9d0\ub77c, 750ml": "\uacfc\ud14c\ub9d0\ub77c 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \uacfc\ud14c\ub9d0\ub77c, 1L": "\uacfc\ud14c\ub9d0\ub77c 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778 DECAF BLEND, 500ml": "\ub514\uce74\ud398\uc778 \ube14\ub79c\ub4dc 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778 DECAF BLEND, 750ml": "\ub514\uce74\ud398\uc778 \ube14\ub79c\ub4dc 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ub514\uce74\ud398\uc778 DECAF BLEND, 1\uac1c, 750ml": "\ub514\uce74\ud398\uc778 \ube14\ub79c\ub4dc 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \ub514\uce74\ud398\uc778, 1L": "\ub514\uce74\ud398\uc778 1L",
    "\uc5b8\ub354\ud504\ub808\uc154 \ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \ub514\uce74\ud398\uc778, 475ml": "\ub514\uce74\ud398\uc778 475ml",
    "\uc77c\uc0c1\uae30\uc900 \ucf5c\ub4dc\ube0c\ub8e8, 1L": "\uc77c\uc0c1\uae30\uc900 1L",
    "\uc77c\uc0c1\uae30\uc900 \ucf5c\ub4dc\ube0c\ub8e8 \ub514\uce74\ud398\uc778, 1L": "\uc77c\uc0c1\uae30\uc900 \ub514\uce74\ud398\uc778 1L",
    "\uc77c\uc0c1\uae30\uc900 \ucf5c\ub4dc\ube0c\ub8e8 \uc5d0\ud2f0\uc624\ud53c\uc544 \ube14\ub80c\ub4dc": "\uc77c\uc0c1\uae30\uc900 \uc5d0\ud2f0\uc624\ud53c\uc544 1L",
    "\uc77c\uc0c1\uae30\uc900 \ucf5c\ub4dc\ube0c\ub8e8 \ucf5c\ub86c\ube44\uc544 \ube14\ub80c\ub4dc": "\uc77c\uc0c1\uae30\uc900 \ucf5c\ub86c\ube44\uc544 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ube0c\ub77c\uc9c8, 500ml": "\ube0c\ub77c\uc9c8 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \ube0c\ub77c\uc9c8, 1L": "\ube0c\ub77c\uc9c8 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ucf5c\ub86c\ube44\uc544, 500ml": "\ucf5c\ub86c\ube44\uc544 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ucf5c\ub86c\ube44\uc544, 1\uac1c, 500ml": "\ucf5c\ub86c\ube44\uc544 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \uc2dc\uadf8\ub2c8\ucc98, 1L": "\uc2dc\uadf8\ub2c8\ucc98 1L",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ud5e4\uc774\uc998\ub137\ud5a5, 500ml": "\ud5e4\uc774\uc998\ub137\ud5a5 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \ud5e4\uc774\uc998\ub137\ud5a5, 1\uac1c, 500ml": "\ud5e4\uc774\uc998\ub137\ud5a5 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \uc544\uc774\ub9ac\uc26c": "\uc544\uc774\ub9ac\uc26c\ud5a5 400ml",
    "\ucd08\ucf5c\ub9bf\ud5a5 \ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561, 300ml": "\ucd08\ucf5c\ub9bf\ud5a5 \ucf5c\ub4dc\ube0c\ub8e8 300ml",
    "\ubc14\ub2d0\ub77c\ud5a5 \ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561, 300ml": "\ubc14\ub2d0\ub77c\ud5a5 \ucf5c\ub4dc\ube0c\ub8e8 300ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561 \uc2a4\ubaa8\ud0a4, 500ml": "\uc2a4\ubaa8\ud0a4 500ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \uc6d0\uc561 \ud30c\ub098\ub9c8 \uac8c\uc774\uc0e4": "\ud30c\ub098\ub9c8 \uac8c\uc774\uc0e4 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ud50c\ub808\uc774\ubc84 \ucf5c\ub809\uc158 6\uc885 \uc138\ud2b8, 300ml": "\ucf5c\ub4dc\ube0c\ub8e8 \ud50c\ub808\uc774\ubc84 \ucf5c\ub809\uc158",
    "\ucf54\ub784 \ube14\ub988 \ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c\uc6d0\uc561": "\ucf54\ub784\ube14\ub984 750ml",
    "\ucf5c\ub4dc\ube0c\ub8e8 \ucee4\ud53c \uc6d0\uc561 \ucf00\ub0d0 500ml + \ub514\uce74\ud398\uc778 500ml \uc138\ud2b8": "\ud578\ub514\uc5c4 \uc6d0\uc561 500ml \uae30\ud504\ud2b8\ud328\ud0a4\uc9c0 (\ucf00\ub0d0, \ub514\uce74\ud398\uc778 \ube14\ub79c\ub4dc)",
}


def convert_item_name(itemnm):
    for keyword, converted in ITEM_NAME_MAP.items():
        if keyword in itemnm:
            return converted
    return None


def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)


def list_files(service, folder_id):
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, modifiedTime, mimeType)"
    ).execute()
    files = results.get("files", [])
    all_files = []
    for f in files:
        if f.get("mimeType") == "application/vnd.google-apps.folder":
            sub_files = list_files(service, f["id"])
            all_files.extend(sub_files)
        else:
            all_files.append(f)
    return all_files


def download_file(service, file_id):
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


def parse_json_files(json_contents):
    stock_map = defaultdict(int)
    seen_vendor_items = set()
    for content in json_contents:
        try:
            data = json.loads(content.decode("utf-8"))
        except Exception:
            data = json.loads(content.decode("cp949", errors="ignore"))
        for p in data.get("products", []):
            vendoritemid = p.get("vendoritemid")
            itemnm = p.get("itemnm", "")
            stock = p.get("stockQuantity", 0) or 0
            if vendoritemid in seen_vendor_items:
                continue
            seen_vendor_items.add(vendoritemid)
            if any(x in itemnm for x in ["2개", "3개", "4개", "5개", "6개", "7개", "2입", "3입"]):
                continue
            converted = convert_item_name(itemnm)
            if converted:
                stock_map[converted] += stock
    return dict(stock_map)


def parse_delivery_excel(content):
    df = pd.read_excel(io.BytesIO(content), sheet_name=None)
    # 첫 번째 시트 사용
    sheet_name = list(df.keys())[0]
    df = df[sheet_name]
    df.columns = [str(c).strip() for c in df.columns]
    print("컬럼 목록:", list(df.columns))

    col_date = next((c for c in df.columns if "출고일" in str(c)), None)
    col_name = next((c for c in df.columns if "품명" in str(c)), None)
    col_qty = next((c for c in df.columns if str(c).strip() == "수량"), None)

    if not col_date:
        col_date = next((c for c in df.columns if "납품일자" in str(c) or "주문일" in str(c)), None)
    if not col_name:
        col_name = next((c for c in df.columns if "품목명" in str(c)), None)
    if not col_qty:
        col_qty = next((c for c in df.columns if "수량" in str(c)), None)

    print(f"날짜={col_date}, 품명={col_name}, 수량={col_qty}")

    if not all([col_date, col_name, col_qty]):
        raise ValueError(f"필수 컬럼 없음: 날짜={col_date}, 품명={col_name}, 수량={col_qty}")

    df2 = df[[col_date, col_name, col_qty]].copy()
    df2.columns = ["date", "name", "qty"]
    df2["date"] = pd.to_datetime(df2["date"], errors="coerce")
    df2["qty"] = pd.to_numeric(df2["qty"], errors="coerce").fillna(0).astype(int)
    df2 = df2.dropna(subset=["date", "name"])
    df2 = df2[df2["qty"] > 0]

    # 제외 품목 필터
    EXCLUDE_NAMES = ["레몬생강즙", "애사비", "레몬즙"]
    df2 = df2[~df2["name"].str.contains("|".join(EXCLUDE_NAMES), na=False)]
    return df2


def calc_daily_avg(df, name):
    item_df = df[df["name"] == name]
    if item_df.empty:
        return 0.0
    total = item_df["qty"].sum()
    date_range = (item_df["date"].max() - item_df["date"].min()).days + 1
    return round(float(total) / max(date_range, 1), 1)


def build_overview_data(stock_map, delivery_df):
    all_names = sorted(set(list(stock_map.keys()) + list(delivery_df["name"].unique())))
    result = []
    for i, name in enumerate(all_names, 1):
        stock = int(stock_map.get(name, 0))
        daily_sell = calc_daily_avg(delivery_df, name)
        if daily_sell > 0:
            days = round(stock / daily_sell, 1)
        else:
            days = 999
        if days <= 7:
            urgency = "긴급"
        elif days <= 14:
            urgency = "빠른납품필요"
        elif days <= 21:
            urgency = "예의주시"
        else:
            urgency = "여유"
        expected = round(daily_sell * 14)
        need = max(expected - stock, 0)
        result.append({
            "no": i,
            "name": name,
            "stock": stock,
            "dailySell": daily_sell,
            "days": days,
            "urgency": urgency,
            "expected": expected,
            "need": need,
        })
    return result


def build_pattern_data(delivery_df):
    all_dates = sorted(delivery_df["date"].dt.strftime("%m/%d").unique())
    all_names = sorted(delivery_df["name"].unique())
    result = []
    for name in all_names:
        item_df = delivery_df[delivery_df["name"] == name]
        total = int(item_df["qty"].sum())
        date_range = (item_df["date"].max() - item_df["date"].min()).days + 1
        daily = round(float(total) / max(date_range, 1), 1)
        vals = []
        for d in all_dates:
            day_qty = item_df[item_df["date"].dt.strftime("%m/%d") == d]["qty"].sum()
            vals.append(int(day_qty))
        result.append({"name": name, "total": total, "daily": daily, "vals": vals})
    return result, all_dates


def inject_data_to_html(html_path, overview, pattern_data, pattern_dates, update_date):
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    overview_js = "const OVERVIEW = " + json.dumps(overview, ensure_ascii=False) + ";"
    html = re.sub(r"const OVERVIEW = \[.*?\];", overview_js, html, flags=re.DOTALL)

    dates_js = "const PATTERN_DATES = " + json.dumps(pattern_dates, ensure_ascii=False) + ";"
    html = re.sub(r"const PATTERN_DATES = \[.*?\];", dates_js, html, flags=re.DOTALL)

    pattern_js = "const PATTERN_DATA = " + json.dumps(pattern_data, ensure_ascii=False) + ";"
    html = re.sub(r"const PATTERN_DATA = \[.*?\];", pattern_js, html, flags=re.DOTALL)

    html = re.sub(r"재고기준: [\d-]+", f"재고기준: {update_date}", html)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML 업데이트 완료: {html_path}")


def main():
    print("구글 드라이브에서 파일 다운로드 중...")
    service = get_drive_service()
    files = list_files(service, DRIVE_FOLDER_ID)

    json_contents = []
    delivery_content = None
    latest_date = None

    for f in files:
        name = f["name"].lower()
        print(f"발견: {f['name']}")
        if name.endswith(".txt") and ("json" in name or "쿠팡" in f["name"]):
            content = download_file(service, f["id"])
            json_contents.append(content)
            print("  -> JSON 파일 로드")
        elif name.endswith(".xlsx") and ("납품" in f["name"] or "delivery" in name):
            delivery_content = download_file(service, f["id"])
            mod_time = f.get("modifiedTime", "")
            if mod_time:
                latest_date = mod_time[:10]
            print("  -> 납품내역 엑셀 로드")

    if not json_contents:
        print("JSON 파일을 찾을 수 없습니다.")
        sys.exit(1)
    if delivery_content is None:
        print("납품내역 엑셀 파일을 찾을 수 없습니다.")
        sys.exit(1)

    update_date = latest_date or datetime.now().strftime("%Y-%m-%d")

    print("데이터 파싱 중...")
    stock_map = parse_json_files(json_contents)
    print(f"  재고 품목 수: {len(stock_map)}")

    delivery_df = parse_delivery_excel(delivery_content)
    print(f"  납품 내역 행수: {len(delivery_df)}")

    print("대시보드 데이터 계산 중...")
    overview = build_overview_data(stock_map, delivery_df)
    pattern_data, pattern_dates = build_pattern_data(delivery_df)
    print(f"  발주예측 품목: {len(overview)}")
    print(f"  납품패턴 품목: {len(pattern_data)}")
    print(f"  납품패턴 날짜: {len(pattern_dates)}")

    print("HTML 업데이트 중...")
    inject_data_to_html(DASHBOARD_HTML, overview, pattern_data, pattern_dates, update_date)
    print(f"완료! 재고기준일: {update_date}")


if __name__ == "__main__":
    main()
