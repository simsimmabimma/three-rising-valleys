import streamlit as st
import pandas as pd
import boto3
from io import BytesIO
import re
from datetime import datetime

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Swing Low Stock Scanner", layout="wide")
st.title("📉 Monthly Swing Low Scanner (3–6 Months)")

# ---------- S3 FILE DOWNLOAD ----------
def get_s3_file(bucket, key):
    session = boto3.Session()
    s3 = session.client('s3')
    obj = s3.get_object(Bucket=bucket, Key=key)
    return BytesIO(obj['Body'].read())

# ---------- COLUMN INFERENCE ----------
def infer_columns(df):
    col_map = {}
    for col in df.columns:
        col_l = col.lower()
        if 'symbol' in col_l or 'ticker' in col_l:
            col_map['symbol'] = col
        elif re.search(r'date|time', col_l):
            col_map['date'] = col
        elif 'open' in col_l:
            col_map['open'] = col
        elif 'high' in col_l:
            col_map['high'] = col
        elif 'low' in col_l:
            col_map['low'] = col
        elif 'close' in col_l:
            col_map['close']()_
