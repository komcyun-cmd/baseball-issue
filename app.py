import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
import re

st.set_page_config(page_title="KBO Hot Issues", layout="wide")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

TEAMS = {
    "한화 이글스": {"dc_id": "hanwhaeagles_new", "keyword": "한화"},
    "KIA 타이거즈": {"dc_id": "tigers_new", "keyword": "기아"},
    "롯데 자이언츠": {"dc_id": "giants_new2", "keyword": "롯데"},
    "LG 트윈스": {"dc_id": "lgtwins_new", "keyword": "LG"},
    "두산 베어스": {"dc_id": "doosanbears_new1", "keyword": "두산"},
    "삼성 라이온즈": {"dc_id": "samsunglions_new", "keyword": "삼성"},
    "SSG 랜더스": {"dc_id": "wyverns_new", "keyword": "SSG"},
    "키움 히어로즈": {"dc_id": "heros_new", "keyword": "키움"},
    "NC 다이노스": {"dc_id": "ncdinos", "keyword": "NC"},
    "KT 위즈": {"dc_id": "ktwiz", "keyword": "KT"}
}

# --- 날짜 필터링 헬퍼 함수 ---
def is_within_48_hours(date_str):
    """
    날짜 문자열을 받아 현재 시간 기준 48시간 이내인지 판단
    형식 예: '14:22' (오늘), '05.21' (날짜), '2024.05.21'
    """
    try:
        now = datetime.now()
        
        # 1. 시간만 있는 경우 (오늘 게시물) -> 무조건 통과
        if ':' in date_str and len(date_str) <= 5: 
            return True
        
        # 2. 날짜만 있는 경우 (MM.DD 또는 YYYY.MM.DD)
        # 구분자를 . 또는 - 로 통일
        date_str = date_str.replace('-', '.')
        
        # 연도가 없는 경우 (MM.DD) -> 올해로 가정
        if len(date_str) <= 5:
            date_str = f"{now.year}.{date_str}"
            
        post_date = datetime.strptime(date_str, "%Y.%m.%d")
        
        # 48시간(2일) 이내인지 확인
        diff = now - post_date
        return diff.days <= 2
    except:
        return True # 파싱 실패 시 안전하게 포함시킴

# --- 크롤러 ---
@st.cache_data(ttl=300)
def get_dc_issues(team_name):
    team_info = TEAMS.get(team_name)
    url = f"https://gall.dcinside.com/board/lists/?id={team_info['dc_id']}&exception_mode=recommend"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('tr.ub-content.us-post')
        
        results = []
        for row in rows:
            date_tag = row.select_one('.gall_date')
            title_tag = row.select_one('.gall_tit a')
            
            if title_tag and date_tag:
                date_text = date_tag.get('title', date_tag.text.strip()) # title 속성에 정확한 시간이 있을 수 있음
                if not is_within_48_hours(date_text):
                    continue # 48시간 지남 -> 스킵
                
                title = title_tag.text.strip()
                link = "https://gall.dcinside.com" + title_tag['href']
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
        return results
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_mlbpark_issues(team_name):
    keyword = TEAMS[team_name]['keyword']
    url = f"https://mlbpark.donga.com/mp/b.php?b=kbotown&search_select=subject&search_input={keyword}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('.tbl_type01 tbody tr')
        
        results = []
        for row in rows:
            if 'notice' in row.get('class', []): continue
            
            date_tag = row.select_one('.date')
            a_tag = row.select_one('.tit a')
            
            if a_tag and date_tag:
                if not is_within_48_hours(date_tag.text.strip()):
                    continue
                
                title = a_tag.text.strip()
                link = a_tag['href']
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
        return results
    except Exception:
        return []

@st.cache_data(ttl=300)
def get_fmkorea_issues(team_name):
    keyword = TEAMS[team_name]['keyword']
    url = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={keyword}&search_target=title_content"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        items = soup.select('.li.li_best2_pop0') or soup.select('.searchResult > li')
        
        results = []
        for item in items:
            time_tag = item.select_one('.time')
            a_tag = item.select_one('dl > dt > a')
            
            if a_tag and time_tag:
                # 펨코 시간 포맷: 14:22, 2024.05.21
                if not is_within_48_hours(time_tag.text.strip()):
                    continue

                title = a_tag.text.strip()
                link = "https://www.fmkorea.com" + a_tag['href'] if 'fmkorea' not in a_tag['href'] else a_tag['href']
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
        return results
    except Exception:
        return []

# --- UI ---
st.title("⚾ KBO Hot Issue (48시간 이내)")
selected_team = st.selectbox("구단 선택", list(TEAMS.keys()))

if st.button("새로고침"):
    with st.spinner('최신 글을 검색 중...'):
        col1, col2, col3 = st.columns(3)
        dc = get_dc_issues(selected_team)
        mlb = get_mlbpark_issues(selected_team)
        fmk = get_fmkorea_issues(selected_team)
        
        def show_list(col, name, data):
            with col:
                st.subheader(name)
                if not data:
                    st.info("최근 48시간 내 인기글이 없거나 로딩 실패")
                for item in data:
                    st.markdown(f"- [{item['title']}]({item['link']})")

        show_list(col1, "DC (48h)", dc)
        show_list(col2, "MLBPARK (48h)", mlb)
        show_list(col3, "FMKOREA (48h)", fmk)
