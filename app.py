import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd

# --------------------------------------------------------------------------
# 1. 설정: 브라우저처럼 위장하기 위한 Scraper 설정
# --------------------------------------------------------------------------
st.set_page_config(page_title="KBO Hot Issue Monitor", layout="wide")

# Cloudscraper 인스턴스 생성 (봇 탐지 우회용)
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
)

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

# --------------------------------------------------------------------------
# 2. 날짜 파싱 로직 (가장 중요한 부분)
# --------------------------------------------------------------------------
def is_within_48_hours(date_text):
    """
    다양한 날짜 형식을 처리하여 48시간 이내인지 판별
    형식 예: '14:22' (오늘), '02.18' (올해), '2024.02.18' (전체)
    """
    try:
        date_text = date_text.strip()
        now = datetime.now()
        post_date = None

        # Case 1: 시간만 있는 경우 (예: 14:22) -> 오늘 게시물
        if ":" in date_text and len(date_text) <= 5:
            return True
        
        # Case 2: 날짜만 있는 경우 (예: 02.18 or 2024.02.18)
        date_text = date_text.replace('-', '.').replace('/', '.') # 구분자 통일
        
        parts = date_text.split('.')
        if len(parts) == 2: # MM.DD -> 올해 연도 붙임
            post_date = datetime(now.year, int(parts[0]), int(parts[1]))
        elif len(parts) == 3: # YYYY.MM.DD
            year = int(parts[0])
            # 2자리 연도(24.02.18)인 경우 처리
            if year < 100: year += 2000 
            post_date = datetime(year, int(parts[1]), int(parts[2]))
            
        if post_date:
            diff = now - post_date
            return diff.days <= 2 # 48시간(2일) 이내
            
        return False # 파싱 불가 시 제외
    except Exception:
        return True # 에러나면 일단 보여줌 (안전장치)

# --------------------------------------------------------------------------
# 3. 크롤링 함수 (Cloudscraper 적용)
# --------------------------------------------------------------------------

@st.cache_data(ttl=300)
def get_dc_issues(team_name):
    team_info = TEAMS.get(team_name)
    # 일반 탭 대신 '개념글' 탭 접근
    url = f"https://gall.dcinside.com/board/lists/?id={team_info['dc_id']}&exception_mode=recommend"
    
    try:
        # requests 대신 scraper 사용
        response = scraper.get(url, timeout=10)
        
        if response.status_code != 200:
            return [{'title': f"접속 실패 (Code: {response.status_code})", 'link': '#'}]

        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('tr.ub-content.us-post')
        
        results = []
        for row in rows:
            # 공지사항 제외
            if 'ub-notice' in row.get('class', []): continue

            title_tag = row.select_one('.gall_tit a')
            date_tag = row.select_one('.gall_date')
            
            if title_tag and date_tag:
                date_str = date_tag.get('title', date_tag.text.strip())
                if not is_within_48_hours(date_str): continue
                
                title = title_tag.text.strip()
                link = "https://gall.dcinside.com" + title_tag['href']
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
                
        return results if results else [{'title': "48시간 내 인기글 없음", 'link': '#'}]
    except Exception as e:
        return [{'title': f"에러: {str(e)}", 'link': '#'}]

@st.cache_data(ttl=300)
def get_mlbpark_issues(team_name):
    keyword = TEAMS[team_name]['keyword']
    url = f"https://mlbpark.donga.com/mp/b.php?b=kbotown&search_select=subject&search_input={keyword}"
    
    try:
        response = scraper.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('.tbl_type01 tbody tr')
        
        results = []
        for row in rows:
            if 'notice' in row.get('class', []): continue
            
            title_tag = row.select_one('.tit a')
            date_tag = row.select_one('.date')
            
            if title_tag and date_tag:
                if not is_within_48_hours(date_tag.text.strip()): continue
                
                title = title_tag.text.strip()
                link = title_tag['href']
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
        return results if results else [{'title': "48시간 내 인기글 없음", 'link': '#'}]
    except Exception as e:
        return [{'title': f"에러: {str(e)}", 'link': '#'}]

@st.cache_data(ttl=300)
def get_fmkorea_issues(team_name):
    keyword = TEAMS[team_name]['keyword']
    # 펨코 통합검색 URL
    url = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={keyword}&search_target=title_content"
    
    try:
        response = scraper.get(url, timeout=10)
        
        if response.status_code != 200:
             return [{'title': f"펨코 차단됨 (Code: {response.status_code})", 'link': '#'}]

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 검색 결과 선택자 (구조 변경 대비 2가지 체크)
        items = soup.select('.li.li_best2_pop0') # 인기글 스타일
        if not items:
            items = soup.select('.searchResult > li') # 일반 리스트 스타일
            
        results = []
        for item in items:
            # 날짜 태그 확인
            time_tag = item.select_one('.time')
            if not time_tag: time_tag = item.select_one('.regdate') # 다른 클래스명 대비

            title_tag = item.select_one('dl > dt > a')
            
            if title_tag and time_tag:
                if not is_within_48_hours(time_tag.text.strip()): continue
                
                title = title_tag.text.strip()
                href = title_tag['href']
                link = "https://www.fmkorea.com" + href if 'fmkorea' not in href else href
                
                results.append({'title': title, 'link': link})
                if len(results) >= 3: break
                
        return results if results else [{'title': "48시간 내 인기글 없음", 'link': '#'}]
    except Exception as e:
        return [{'title': f"에러: {str(e)}", 'link': '#'}]

# --------------------------------------------------------------------------
# 4. UI 구성
# --------------------------------------------------------------------------
st.title("⚾ KBO Hot Issue (48h Real-time)")
st.caption("※ 에펨코리아/디시는 보안이 강력하여 로딩에 3~5초 소요될 수 있습니다.")

selected_team = st.selectbox("구단 선택", list(TEAMS.keys()))

if st.button("새로고침", type="primary"):
    with st.spinner(f'{selected_team} 이슈를 수집 중입니다... (Cloudscraper 작동)'):
        col1, col2, col3 = st.columns(3)
        
        # 데이터 수집
        dc = get_dc_issues(selected_team)
        mlb = get_mlbpark_issues(selected_team)
        fmk = get_fmkorea_issues(selected_team)
        
        # 결과 출력 함수
        def show_card(col, name, data, icon):
            with col:
                st.subheader(f"{icon} {name}")
                st.divider()
                for item in data:
                    if item['link'] == '#':
                        st.error(item['title']) # 에러나면 빨간색 표시
                    else:
                        st.markdown(f"**[{item['title']}]({item['link']})**")
                        st.markdown("---")

        show_card(col1, "DC (48h)", dc, "👿")
        show_card(col2, "MLBPARK (48h)", mlb, "🏟️")
        show_card(col3, "FMKOREA (48h)", fmk, "⚽")

