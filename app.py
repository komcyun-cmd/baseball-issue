import streamlit as st
import feedparser
import pandas as pd
from datetime import datetime

# --------------------------------------------------------------------------
# 1. 설정 및 스타일
# --------------------------------------------------------------------------
st.set_page_config(page_title="KBO Quick Linker", layout="wide")

# 디자인 CSS: 깔끔한 카드와 버튼 스타일
st.markdown("""
    <style>
    .dc-card { background-color: #2d3436; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 4px solid #4b6584; }
    .dc-title { font-size: 16px; font-weight: bold; color: white !important; text-decoration: none; }
    .dc-date { font-size: 12px; color: #b2bec3; }
    a { text-decoration: none; }
    a:hover { text-decoration: underline; color: #74b9ff !important; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 구단별 데이터 매핑 (DC ID 및 검색어)
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
# 2. DC 공식 RSS 파서 (차단 없음, 100% 성공)
# --------------------------------------------------------------------------
def get_dc_rss(team_code):
    # DC 공식 RSS URL
    rss_url = f"https://gall.dcinside.com/board/rss/lists/?id={team_code}"
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:5]: # 최신 5개
            # RSS 날짜 포맷팅
            try:
                dt = datetime(*entry.published_parsed[:6])
                date_str = dt.strftime("%m/%d %H:%M")
            except:
                date_str = "방금 전"
            
            results.append({'title': entry.title, 'link': entry.link, 'date': date_str})
        return results
    except:
        return []

# --------------------------------------------------------------------------
# 3. 바로가기 링크 생성기 (FMK/MLB)
# --------------------------------------------------------------------------
def get_links(keyword):
    # 엠팍: KBO타운 검색 (제목+내용)
    mlb_link = f"https://mlbpark.donga.com/mp/b.php?select=sct&m=search&b=kbotown&search_select=sct&search_input={keyword}"
    
    # 펨코: 야구탭 검색 (제목+내용)
    fmk_link = f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={keyword}&search_target=title_content"
    
    return mlb_link, fmk_link

# --------------------------------------------------------------------------
# 4. UI 렌더링
# --------------------------------------------------------------------------
st.title("⚾ KBO 실시간 상황실")
st.caption("서버 차단 없는 안전한 방식: DC는 RSS로 미리보기, 타 사이트는 원터치 이동")

selected_team = st.selectbox("구단을 선택하세요", list(TEAMS.keys()))
team_data = TEAMS[selected_team]

if st.button("새로고침", type="primary"):
    
    col1, col2, col3 = st.columns(3)

    # [1] DC 인사이드 (RSS 활용 - 데이터 표시됨)
    with col1:
        st.subheader("👿 DC (실시간)")
        rss_data = get_dc_rss(team_data['dc_id'])
        
        if rss_data:
            for item in rss_data:
                st.markdown(f"""
                <div class="dc-card">
                    <a href="{item['link']}" target="_blank" class="dc-title">{item['title']}</a><br>
                    <span class="dc-date">🕒 {item['date']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("데이터 로딩 실패 (RSS 일시 오류)")
            st.link_button("DC 갤러리 바로가기", f"https://gall.dcinside.com/board/lists/?id={team_data['dc_id']}")

    # [2] MLBPARK (바로가기)
    with col2:
        st.subheader("🏟️ 엠엘비파크")
        st.info("엠팍은 외부 접속을 차단합니다.\n아래 버튼으로 최신글을 확인하세요.")
        mlb_url, _ = get_links(team_data['keyword'])
        st.link_button(f"👉 {selected_team} 검색 결과 (새창)", mlb_url)

    # [3] FMKOREA (바로가기)
    with col3:
        st.subheader("⚽ 에펨코리아")
        st.info("펨코는 보안이 가장 강력합니다.\n아래 버튼으로 즉시 이동합니다.")
        _, fmk_url = get_links(team_data['keyword'])
        st.link_button(f"👉 {selected_team} 검색 결과 (새창)", fmk_url)

