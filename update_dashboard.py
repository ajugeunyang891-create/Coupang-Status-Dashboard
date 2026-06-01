"""
       
  JSON +    HTML  .
"""

import json
import os
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

#   
DRIVE_FOLDER_ID = "1MRKdVhxdUEZFmbje7h0T6oulf8T4il7P"
SERVICE_ACCOUNT_FILE = "service_account.json"
DASHBOARD_HTML = "index.html"

#   itemnm →    
ITEM_NAME_MAP = {
    # 
    "": " 475ml",
    # 
    "": " 475ml",
    #  
    "   , 750ml": " 750ml",
    "   , 900ml": " 900ml",
    "  , 475ml": "  475ml",
    "  , 750ml": "  750ml",
    "  , 900ml": "  900ml",
    "  ": "  400ml",
    "  ": "   30g",
    " , 1, 400ml": "  400ml",
    "  ": "10  200ml",
    #  
    "   ": " 475ml",
    "   ": " 475ml",
    "     ": "  200ml",
    "     ": "  200ml",
    "    ": "  200ml",
    "    ": "  200ml",
    "   , 475ml": " 475ml",
    "  , 1, 400ml": "  400ml",
    "  , 400ml": "  400ml",
    # 
    "  , 500ml": " 500ml",
    "   , 500ml": " 500ml",
    " , 750ml": " 750ml",
    "  , 1L": " 1L",
    # 
    " , 500ml": " 500ml",
    "  , 750ml": " 750ml",
    "  , 1L": " 1L",
    # 
    " , 500ml": " 500ml",
    "  , 750ml": " 750ml",
    "  , 1L": " 1L",
    #  
    "   DECAF BLEND, 500ml": "  500ml",
    "   DECAF BLEND, 750ml": "  750ml",
    "   DECAF BLEND, 1, 750ml": "  750ml",
    # 
    "  , 1L": " 1L",
    "   , 475ml": " 475ml",
    "  ": "  30g",
    # 
    " , 1L": " 1L",
    "  , 1L": "  1L",
    "   ": "  1L",
    "   ": "  1L",
    # 
    "  , 500ml": " 500ml",
    "  , 1L": " 1L",
    # 
    "  , 500ml": " 500ml",
    "  , 1, 500ml": " 500ml",
    # 
    "  , 1L": " 1L",
    # 
    "  , 500ml": " 500ml",
    "  , 1, 500ml": " 500ml",
    # 
    "  ": " 400ml",
    # 
    "  , 300ml": "  300ml",
    # 
    "  , 300ml": "  300ml",
    # 
    "  , 500ml": " 500ml",
    #  
    "   ": "  750ml",
    #  
    "   6 , 300ml": "  ",
    # 
    "   ": " 750ml",
    #  
    "    500ml +  500ml ": "  500ml  (,  )",
}


def convert_item_name(itemnm: str) -> str | None:
    """ itemnm   """
    for keyword, converted in ITEM_NAME_MAP.items():
        if keyword in itemnm:
            return converted
    return None


#     
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
    return results.get("files", [])


def download_file(service, file_id) -> bytes:
    request = service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue()


#  JSON  
def parse_json_files(json_contents: list[bytes]) -> dict:
    """ JSON     (  )"""
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

            #  vendoritem 
            if vendoritemid in seen_vendor_items:
                continue
            seen_vendor_items.add(vendoritemid)

            #   
            if any(x in itemnm for x in ["2", "3", "4", "5", "6", "7", "2", "3"]):
                continue

            #   
            converted = convert_item_name(itemnm)
            if converted:
                stock_map[converted] += stock

    return dict(stock_map)


#     
def parse_delivery_excel(content: bytes) -> pd.DataFrame:
    """  // """
    df = pd.read_excel(io.BytesIO(content), sheet_name="Sheet2")

    #  
    df.columns = [str(c).strip() for c in df.columns]

    # , ,  
    df = df[["", "  ", ""]].copy()
    df.columns = ["date", "name", "qty"]

    #  
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["qty"] = pd.to_numeric(df["qty"], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["date", "name"])
    df = df[df["qty"] > 0]

    return df


#     
def calc_daily_avg(df: pd.DataFrame, name: str) -> float:
    """   """
    item_df = df[df["name"] == name]
    if item_df.empty:
        return 0.0
    total = item_df["qty"].sum()
    if item_df["date"].nunique() == 0:
        return 0.0
    date_range = (item_df["date"].max() - item_df["date"].min()).days + 1
    return round(total / max(date_range, 1), 1)


def build_overview_data(stock_map: dict, delivery_df: pd.DataFrame) -> list:
    """  """
    all_names = sorted(set(list(stock_map.keys()) + list(delivery_df["name"].unique())))
    result = []

    for i, name in enumerate(all_names, 1):
        stock = stock_map.get(name, 0)
        daily_sell = calc_daily_avg(delivery_df, name)

        if daily_sell > 0:
            days = round(stock / daily_sell, 1)
        else:
            days = 999

        if days <= 7:
            urgency = ""
        elif days <= 14:
            urgency = ""
        elif days <= 21:
            urgency = ""
        else:
            urgency = ""

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


def build_pattern_data(delivery_df: pd.DataFrame) -> list:
    """  """
    all_dates = sorted(delivery_df["date"].dt.strftime("%m/%d").unique())
    all_names = sorted(delivery_df["name"].unique())

    result = []
    for name in all_names:
        item_df = delivery_df[delivery_df["name"] == name]
        total = int(item_df["qty"].sum())
        date_range = (item_df["date"].max() - item_df["date"].min()).days + 1
        daily = round(total / max(date_range, 1), 1)

        vals = []
        for d in all_dates:
            day_qty = item_df[item_df["date"].dt.strftime("%m/%d") == d]["qty"].sum()
            vals.append(int(day_qty))

        result.append({
            "name": name,
            "total": total,
            "daily": daily,
            "vals": vals,
        })

    return result, all_dates


#  HTML  
def inject_data_to_html(html_path: str, overview: list, pattern_data: list,
                         pattern_dates: list, stock_map: dict, update_date: str):
    """HTML      """
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    # OVERVIEW  
    overview_js = "const OVERVIEW = " + json.dumps(overview, ensure_ascii=False) + ";"
    html = re.sub(r"const OVERVIEW = \[.*?\];", overview_js, html, flags=re.DOTALL)

    # PATTERN_DATES 
    dates_js = "const PATTERN_DATES = " + json.dumps(pattern_dates, ensure_ascii=False) + ";"
    html = re.sub(r"const PATTERN_DATES = \[.*?\];", dates_js, html, flags=re.DOTALL)

    # PATTERN_DATA 
    pattern_js = "const PATTERN_DATA = " + json.dumps(pattern_data, ensure_ascii=False) + ";"
    html = re.sub(r"const PATTERN_DATA = \[.*?\];", pattern_js, html, flags=re.DOTALL)

    #   
    html = re.sub(
        r": [\d-]+",
        f": {update_date}",
        html
    )

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f" HTML  : {html_path}")


#   
def main():
    print("     ...")
    service = get_drive_service()
    files = list_files(service, DRIVE_FOLDER_ID)

    json_contents = []
    delivery_content = None
    latest_date = None

    for f in files:
        name = f["name"].lower()
        print(f"   : {f['name']}")

        if name.endswith(".txt") and ("json" in name or "" in f["name"]):
            content = download_file(service, f["id"])
            json_contents.append(content)
            print(f"    → JSON  ")

        elif name.endswith(".xlsx") and ("" in f["name"] or "delivery" in name):
            delivery_content = download_file(service, f["id"])
            mod_time = f.get("modifiedTime", "")
            if mod_time:
                latest_date = mod_time[:10]
            print(f"    →   ")

    if not json_contents:
        print(" JSON    .")
        sys.exit(1)
    if delivery_content is None:
        print("      .")
        sys.exit(1)

    update_date = latest_date or datetime.now().strftime("%Y-%m-%d")

    print(f"\n   ...")
    stock_map = parse_json_files(json_contents)
    print(f"    : {len(stock_map)}")

    delivery_df = parse_delivery_excel(delivery_content)
    print(f"    : {len(delivery_df)}")

    print(f"\n    ...")
    overview = build_overview_data(stock_map, delivery_df)
    pattern_data, pattern_dates = build_pattern_data(delivery_df)

    print(f"   : {len(overview)}")
    print(f"   : {len(pattern_data)}")
    print(f"   : {len(pattern_dates)}")

    print(f"\n HTML  ...")
    inject_data_to_html(
        DASHBOARD_HTML, overview, pattern_data,
        pattern_dates, stock_map, update_date
    )

    print(f"\n ! : {update_date}")


if __name__ == "__main__":
    main()
