import streamlit as st
import feedparser
import requests
import urllib.parse
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 설정 및 헤더 (차단 방지용 필수 키)
# --------------------------------------------------------------------------
st.set_page_config(page_title="KBO Dashboard", layout="wide")

# 일반 브라우저인 척 속이는 헤더 (이게 없어서 DC가 차단했던 것임)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

st.markdown("""
    <style>
    .dc-card { background-color: #2d3436; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 4px solid #4b6584; }
    .dc-title { font-size: 16px; font-weight: bold; color: white !important; text-decoration: none; }
    .dc-date { font-size: 12px; color: #b2bec3; }
    a { text-decoration: none; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

TEAMS = {
    "한화 이글스": {"dc_id": "hanwhaeagles_new", "keyword": "한화"},
    "KIA 타이거즈": {"dc_id": "tigers_new", "keyword": "KIA"},
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
# 2. DC RSS (헤더 추가로 차단 우회)
# --------------------------------------------------------------------------
def get_dc_rss_secure(team_code):
    url = f"https://gall.dcinside.com/board/rss/lists/?id={team_code}"
    try:
        # requests로 헤더를 달아서 원본 데이터를 가져옴 (이 과정이 핵심)
        response = requests.get(url, headers=HEADERS, timeout=5)
        
        if response.status_code == 200:
            # 가져온 데이터를 feedparser에게 먹임
            feed = feedparser.parse(response.content)
            results = []
            for entry in feed.entries[:5]:
                try:
                    dt = datetime(*entry.published_parsed[:6])
                    date_str = dt.strftime("%m/%d %H:%M")
                except:
                    date_str = "최신"
                results.append({'title': entry.title, 'link': entry.link, 'date': date_str})
            return results
        else:
            return None # 서버 에러
    except Exception:
        return None # 연결 실패

# --------------------------------------------------------------------------
# 3. 링크 생성 (한글 깨짐 방지 인코딩 적용)
# --------------------------------------------------------------------------
def get_safe_links(keyword):
    # 한글을 URL 기계어(%ED%95...)로 변환
    encoded_keyword = urllib.parse.quote(keyword)
    
    # 엠팍 (제목+내용 검색)
    mlb = f"https://mlbpark.donga.com/mp/b.php?select=sct&m=search&b=kbotown&search_select=sct&search_input={encoded_keyword}"
    
    # 펨코 (제목+내용 검색)
    fmk = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={encoded_keyword}&search_target=title_content"
    
    return mlb, fmk

# --------------------------------------------------------------------------
# 4. 화면 구성
# --------------------------------------------------------------------------
st.title("⚾ KBO Live Monitor")

selected_team = st.selectbox("구단 선택", list(TEAMS.keys()))
team_data = TEAMS[selected_team]

if st.button("데이터 가져오기", type="primary"):
    col1, col2, col3 = st.columns(3)
    
    # [1] DC Inside
    with col1:
        st.subheader("👿 DC (실시간)")
        data = get_dc_rss_secure(team_data['dc_id'])
        
        if data:
            for item in data:
                st.markdown(f"""
                <div class="dc-card">
                    <a href="{item['link']}" target="_blank" class="dc-title">{item['title']}</a><br>
                    <span class="dc-date">{item['date']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            # RSS 실패 시에도 당황하지 않고 버튼 노출
            st.warning("RSS 수신 지연")
            st.link_button("갤러리 바로가기", f"https://gall.dcinside.com/board/lists/?id={team_data['dc_id']}")

    # 링크 생성 (인코딩 적용됨)
    mlb_url, fmk_url = get_safe_links(team_data['keyword'])

    # [2] MLBPARK
    with col2:
        st.subheader("🏟️ 엠팍")
        st.info("검색어 자동 인코딩 완료")
        st.link_button("검색 결과 보기 (새창)", mlb_url)

    # [3] FMKOREA
    with col3:
        st.subheader("⚽ 펨코")
        st.info("보안 접속 (새창 이동)")
        st.link_button("검색 결과 보기 (새창)", fmk_url)
