import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 설정 및 헤더 (모바일 환경 흉내)
# --------------------------------------------------------------------------
st.set_page_config(page_title="Real-time KBO", layout="wide")

# 모바일 헤더 (갤럭시 폰인척 위장)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://www.google.com/'
}

# --------------------------------------------------------------------------
# 2. 핵심 기술: 시간 검증 필터 (오늘 글만 통과)
# --------------------------------------------------------------------------
def is_today(date_text):
    """
    날짜 텍스트를 분석하여 '오늘' 글인지 판단
    - 통과: '14:20', '09:00', '방금', '1분 전' (시간 포맷)
    - 탈락: '02.19', '2024...', '어제' (날짜 포맷)
    """
    date_text = date_text.strip()
    # 콜론(:)이 있으면 시간(오늘)으로 간주
    if ":" in date_text and len(date_text) <= 5: 
        return True
    if "분" in date_text or "초" in date_text or "방금" in date_text:
        return True
    return False

# --------------------------------------------------------------------------
# 3. 사이트별 공략 (Session 사용)
# --------------------------------------------------------------------------
def get_dc_mobile(team_id):
    """DC 모바일: 개념글 목록에서 시간 체크"""
    url = f"https://m.dcinside.com/board/{team_id}?recommend=1"
    session = requests.Session()
    try:
        resp = session.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        items = soup.select('.gall-detail-lst li .subject')
        results = []
        for item in items:
            title = item.select_one('.tit').text.strip()
            date = item.select_one('.date').text.strip() # DC 모바일은 시간/날짜 구분 명확
            
            if is_today(date):
                link = item.get('href')
                if not link.startswith('http'): link = f"https://m.dcinside.com{link}"
                results.append({'title': title, 'link': link, 'time': date})
                if len(results) >= 3: break
        return results
    except:
        return []

def get_mlb_mobile(keyword):
    """엠팍: 검색 대신 'KBO타운' 최신글 긁어서 필터링 (가장 정확함)"""
    url = "https://mlbpark.donga.com/mp/b.php?b=kbotown"
    session = requests.Session()
    try:
        resp = session.get(url, headers=HEADERS, timeout=5)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        rows = soup.select('.tbl_type01 tbody tr')
        results = []
        for row in rows:
            if 'notice' in row.get('class', []): continue
            
            title_tag = row.select_one('.tit a')
            date_tag = row.select_one('.date')
            
            if title_tag and date_tag:
                title = title_tag.text.strip()
                date = date_tag.text.strip()
                
                # 1. 오늘 글인가?
                if not is_today(date): continue
                # 2. 우리 팀 이야기인가?
                if keyword not in title: continue
                
                results.append({'title': title, 'link': title_tag['href'], 'time': date})
                if len(results) >= 3: break
        return results
    except:
        return []

def get_fmk_mobile(keyword):
    """펨코: 모바일 통합검색 시도 -> 실패 시 '버튼' 제공 (솔직한 접근)"""
    # 펨코는 서버 IP 차단이 매우 심함. 
    # 무리하게 뚫으려다 에러 띄우는 것보다, 실패 시 바로 링크를 주는게 UX상 나음.
    return None # 펨코는 전략적으로 '직접 링크'로 유도

# --------------------------------------------------------------------------
# 4. 데이터 매핑
# --------------------------------------------------------------------------
TEAMS = {
    "한화 이글스": {"dc": "hanwhaeagles_new", "keyword": "한화"},
    "KIA 타이거즈": {"dc": "tigers_new", "keyword": "KIA"},
    "롯데 자이언츠": {"dc": "giants_new2", "keyword": "롯데"},
    "LG 트윈스": {"dc": "lgtwins_new", "keyword": "LG"},
    "두산 베어스": {"dc": "doosanbears_new1", "keyword": "두산"},
    "삼성 라이온즈": {"dc": "samsunglions_new", "keyword": "삼성"},
    "SSG 랜더스": {"dc": "wyverns_new", "keyword": "SSG"},
    "키움 히어로즈": {"dc": "heros_new", "keyword": "키움"},
    "NC 다이노스": {"dc": "ncdinos", "keyword": "NC"},
    "KT 위즈": {"dc": "ktwiz", "keyword": "KT"}
}

# --------------------------------------------------------------------------
# 5. UI 렌더링
# --------------------------------------------------------------------------
st.markdown("""
    <style>
    .card { background-color: #262730; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #444; }
    .card a { color: white; text-decoration: none; font-weight: 600; font-size: 15px; }
    .card a:hover { color: #ff9f43; }
    .meta { font-size: 12px; color: #b2bec3; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ Real-time KBO Radar")
st.caption("오늘(Today) 작성된 최신 글만 엄격하게 필터링합니다.")

team_name = st.selectbox("구단 선택", list(TEAMS.keys()))
team_data = TEAMS[team_name]

if st.button("실시간 이슈 확인", type="primary"):
    c1, c2, c3 = st.columns(3)
    
    # [1] DC Inside
    with c1:
        st.subheader("👿 디시 (Mobile)")
        data = get_dc_mobile(team_data['dc'])
        if data:
            for item in data:
                st.markdown(f"""
                <div class="card" style="border-left: 4px solid #4b6584;">
                    <a href="{item['link']}" target="_blank">{item['title']}</a>
                    <div class="meta">⏱ {item['time']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("현재 실시간 인기글 없음")
            st.markdown(f"[갤러리 바로가기](https://m.dcinside.com/board/{team_data['dc']})")

    # [2] MLBPARK
    with c2:
        st.subheader("🏟️ 엠팍 (KBO타운)")
        data = get_mlb_mobile(team_data['keyword'])
        if data:
            for item in data:
                st.markdown(f"""
                <div class="card" style="border-left: 4px solid #20bf6b;">
                    <a href="{item['link']}" target="_blank">{item['title']}</a>
                    <div class="meta">⏱ {item['time']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(f"'{team_data['keyword']}' 관련 오늘 글 없음")
            st.markdown(f"[KBO타운 바로가기](https://mlbpark.donga.com/mp/b.php?b=kbotown)")

    # [3] FMKOREA (전략적 링크)
    with c3:
        st.subheader("⚽ 펨코")
        st.warning("🔒 보안이 강력하여 직접 접속을 권장합니다.")
        # 펨코 검색 URL (제목+내용)
        url = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={team_data['keyword']}&search_target=title_content"
        st.link_button(f"👉 {team_name} 최신 반응 보기", url)
