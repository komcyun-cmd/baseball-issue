import streamlit as st
import cloudscraper
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

# --------------------------------------------------------------------------
# 1. 강력한 스크래퍼 설정 (모바일 브라우저 위장)
# --------------------------------------------------------------------------
st.set_page_config(page_title="Real-time KBO Monitor", layout="wide")

# 모바일 User-Agent 사용 (PC보다 차단 확률이 현저히 낮음)
MOBILE_UA = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Referer': 'https://www.google.com'
}

# Cloudscraper 인스턴스 (보안 우회용)
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'mobile': True})

# 구단별 키워드 및 ID 매핑
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
# 2. 날짜 필터링 로직 (단순화 & 강화)
# --------------------------------------------------------------------------
def is_fresh(date_str):
    """
    XX:XX (오늘) -> 무조건 True
    MM.DD (날짜) -> 어제/오늘이면 True, 아니면 False
    """
    date_str = date_str.strip()
    
    # 1. 시간으로 표시되면 오늘 글임 (예: 14:22)
    if ":" in date_str and len(date_str) < 8:
        return True
    
    # 2. 날짜로 표시되면 (예: 02.19 or 2024.02.19)
    try:
        # 숫자와 점(.)만 남기고 제거
        clean_date = re.sub(r'[^0-9.]', '', date_str)
        parts = clean_date.split('.')
        
        now = datetime.now()
        
        # 연도가 없는 경우 (MM.DD)
        if len(parts) == 2:
            post_date = datetime(now.year, int(parts[0]), int(parts[1]))
        # 연도가 있는 경우 (YYYY.MM.DD)
        elif len(parts) == 3:
            year = int(parts[0])
            if year < 100: year += 2000 # 24.02.19 대응
            post_date = datetime(year, int(parts[1]), int(parts[2]))
        else:
            return False # 형식 불명

        # 48시간 이내 체크
        diff = now - post_date
        return diff.days <= 2
    except:
        return True # 파싱 에러나면 안전하게 포함

# --------------------------------------------------------------------------
# 3. 크롤링 엔진 (전략 수정됨)
# --------------------------------------------------------------------------

@st.cache_data(ttl=120)
def get_dc_mobile(team_name):
    """전략: 모바일 페이지(m.dcinside) 사용 -> 차단 우회 및 파싱 용이"""
    team_info = TEAMS.get(team_name)
    # 모바일용 추천(개념)글 목록
    url = f"https://m.dcinside.com/board/{team_info['dc_id']}?recommend=1"
    
    try:
        resp = scraper.get(url, headers=MOBILE_UA, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 모바일 리스트 구조
        items = soup.select('.gall-detail-lst li .subject')
        
        results = []
        for item in items:
            title_txt = item.select_one('.tit').text.strip()
            # 모바일 날짜: <span class="date">14:22</span>
            date_txt = item.select_one('.date').text.strip()
            
            if is_fresh(date_txt):
                link = item.get('href', '#') # 링크 추출
                # 링크가 상대경로인 경우 처리
                if not link.startswith('http'):
                    link = f"https://m.dcinside.com{link}"
                    
                results.append({'title': title_txt, 'link': link, 'date': date_txt})
                if len(results) >= 3: break
                
        return results if results else [{'title': '48시간 내 개념글 없음', 'link': '#', 'date': '-'}]
    except Exception as e:
        return [{'title': f'DC 접속 실패: {e}', 'link': '#', 'date': 'Error'}]

@st.cache_data(ttl=120)
def get_mlb_filter(team_name):
    """전략: 검색 기능 포기 -> 최신글 목록(3페이지) 긁어서 '팀명' 필터링 (최신성 보장)"""
    keyword = TEAMS[team_name]['keyword']
    base_url = "https://mlbpark.donga.com/mp/b.php?b=kbotown"
    
    results = []
    try:
        # 1~2페이지만 빠르게 스캔
        for page in range(1, 3):
            url = f"{base_url}&p={page * 30}" # 엠팍 페이징 계산
            resp = scraper.get(url, headers=MOBILE_UA, timeout=5)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            rows = soup.select('.tbl_type01 tbody tr')
            for row in rows:
                if 'notice' in row.get('class', []): continue # 공지 제외

                title_tag = row.select_one('.tit a')
                date_tag = row.select_one('.date')
                
                if title_tag and date_tag:
                    title_txt = title_tag.text.strip()
                    date_txt = date_tag.text.strip()
                    
                    # 1. 날짜 먼저 체크
                    if not is_fresh(date_txt): continue
                    
                    # 2. 제목에 팀 이름이 있는지 체크 (이게 핵심)
                    if keyword in title_txt:
                        results.append({'title': title_txt, 'link': title_tag['href'], 'date': date_txt})
                        if len(results) >= 3: return results
                        
        return results if results else [{'title': f'{keyword} 관련 최신글 없음', 'link': '#', 'date': '-'}]
    except Exception as e:
        return [{'title': f'엠팍 접속 실패: {e}', 'link': '#', 'date': 'Error'}]

@st.cache_data(ttl=120)
def get_fmk_google_fallback(team_name):
    """전략: 펨코 직접 접속 시도 -> 실패시 구글 검색 결과 사용"""
    keyword = TEAMS[team_name]['keyword']
    
    # 1차 시도: 펨코 통합검색 (Cloudscraper)
    target_url = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={keyword}&search_target=title_content"
    
    try:
        resp = scraper.get(target_url, headers=MOBILE_UA, timeout=5)
        
        # 403 Forbidden 등 차단 확인
        if resp.status_code != 200 or "Cloudflare" in resp.text:
            raise Exception("Blocked")

        soup = BeautifulSoup(resp.text, 'html.parser')
        items = soup.select('.li.li_best2_pop0') # 인기글
        if not items: items = soup.select('.searchResult > li') # 일반글

        results = []
        for item in items:
            title_tag = item.select_one('dl > dt > a')
            time_tag = item.select_one('.time') or item.select_one('.regdate')
            
            if title_tag and time_tag:
                date_txt = time_tag.text.strip()
                if is_fresh(date_txt):
                    # 링크 처리
                    raw_link = title_tag['href']
                    link = f"https://www.fmkorea.com{raw_link}" if 'fmkorea' not in raw_link else raw_link
                    results.append({'title': title_tag.text.strip(), 'link': link, 'date': date_txt})
                    if len(results) >= 3: return results
        
        if results: return results

    except Exception:
        # 2차 시도 (실패 시): 그냥 에러 메시지 대신 '직접 링크' 제공
        # 구글 검색을 긁는 건 더 위험하므로 사용자에게 우회 링크 제공이 가장 확실함
        pass

    return [{'title': '🚫 펨코 보안 차단됨 (클릭하여 직접 보기)', 'link': target_url, 'date': 'Link'}]


# --------------------------------------------------------------------------
# 4. UI 렌더링
# --------------------------------------------------------------------------
st.title("⚾ KBO Radar (Final Ver.)")
st.markdown("---")

selected_team = st.selectbox("구단을 선택하세요", list(TEAMS.keys()))

if st.button("새로고침 (데이터 가져오기)", type="primary"):
    
    col1, col2, col3 = st.columns(3)
    
    # 1. DC Mobile
    with col1:
        st.subheader("👿 DC (Mobile)")
        with st.spinner('DC 접속 중...'):
            data = get_dc_mobile(selected_team)
            st.divider()
            for item in data:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item['date']}")
                st.write("")

    # 2. MLBPark Filter
    with col2:
        st.subheader("🏟️ 엠팍 (KBO타운)")
        with st.spinner('엠팍 최신글 스캔 중...'):
            data = get_mlb_filter(selected_team)
            st.divider()
            for item in data:
                st.markdown(f"**[{item['title']}]({item['link']})**")
                st.caption(f"🕒 {item['date']}")
                st.write("")

    # 3. FMKorea (w/ Fallback)
    with col3:
        st.subheader("⚽ 펨코 (야구탭)")
        with st.spinner('펨코 뚫는 중...'):
            data = get_fmk_google_fallback(selected_team)
            st.divider()
            for item in data:
                if item['date'] == 'Link':
                    st.warning(f"[{item['title']}]({item['link']})")
                else:
                    st.markdown(f"**[{item['title']}]({item['link']})**")
                    st.caption(f"🕒 {item['date']}")
                st.write("")
