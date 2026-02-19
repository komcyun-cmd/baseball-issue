import streamlit as st
import feedparser # RSS 파싱용 라이브러리
import urllib.parse
from datetime import datetime, timedelta
import pandas as pd

# --------------------------------------------------------------------------
# 1. 설정 및 디자인
# --------------------------------------------------------------------------
st.set_page_config(page_title="KBO Radar Final", layout="wide")

# CSS: 버튼 및 스타일 디자인
st.markdown("""
    <style>
    .big-font { font-size:18px !important; font-weight: bold; }
    .card { background-color: #262730; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #444; }
    .source-tag { font-size: 12px; padding: 3px 6px; border-radius: 4px; margin-right: 5px; }
    .dc { background-color: #4b6584; color: white; }
    .mlb { background-color: #20bf6b; color: white; }
    .fmk { background-color: #3867d6; color: white; }
    a { text-decoration: none; color: #ffffff !important; }
    a:hover { color: #ff4b4b !important; }
    </style>
    """, unsafe_allow_html=True)

# 구단별 검색 키워드 매핑
TEAMS = {
    "한화 이글스": "한화",
    "KIA 타이거즈": "KIA", # 기아는 검색어 혼동이 있어 영어 KIA 권장
    "롯데 자이언츠": "롯데",
    "LG 트윈스": "LG",
    "두산 베어스": "두산",
    "삼성 라이온즈": "삼성",
    "SSG 랜더스": "SSG",
    "키움 히어로즈": "키움",
    "NC 다이노스": "NC",
    "KT 위즈": "KT"
}

# --------------------------------------------------------------------------
# 2. 핵심 로직: Google News RSS 우회 (차단 방지)
# --------------------------------------------------------------------------
def get_google_rss_issues(site_url, keyword):
    """
    사이트 직접 접속 대신 구글 뉴스 RSS를 통해 우회 접속
    장점: IP 차단 안 당함, 속도 빠름
    단점: 아주 실시간(1분 전) 글은 없을 수 있음 -> 버튼으로 보완
    """
    # 검색 쿼리: site:fmkorea.com "한화" when:1d (1일 이내)
    encoded_query = urllib.parse.quote(f'site:{site_url} "{keyword}" when:2d')
    rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        feed = feedparser.parse(rss_url)
        results = []
        for entry in feed.entries[:5]: # 상위 5개
            title = entry.title
            # 구글 RSS 제목에서 사이트 이름 제거 (예: "제목 - 에펨코리아")
            if "-" in title:
                title = title.rsplit("-", 1)[0].strip()
            
            link = entry.link
            pub_date = entry.published_parsed
            
            # 날짜 포맷팅
            date_str = f"{pub_date.tm_mon}/{pub_date.tm_mday} {pub_date.tm_hour}:{pub_date.tm_min:02d}"
            
            results.append({'title': title, 'link': link, 'date': date_str})
        return results
    except Exception:
        return []

# --------------------------------------------------------------------------
# 3. 직접 링크 생성기 (데이터 없을 때 비상용)
# --------------------------------------------------------------------------
def get_direct_link(site_code, keyword):
    if site_code == "DC":
        # 디시 통합검색 (최신순)
        return f"https://search.dcinside.com/combine/q/{keyword}/w/gall/s/date"
    elif site_code == "MLB":
        # 엠팍 검색
        return f"https://mlbpark.donga.com/mp/b.php?select=sct&m=search&b=kbotown&search_select=sct&search_input={keyword}"
    elif site_code == "FMK":
        # 펨코 검색
        return f"https://www.fmkorea.com/search.php?mid=baseball&search_keyword={keyword}&search_target=title_content"
    return "#"

# --------------------------------------------------------------------------
# 4. UI 렌더링
# --------------------------------------------------------------------------
st.title("⚾ KBO 통합 대시보드 (RSS Ver.)")
st.caption("서버 차단을 우회하여 구글이 수집한 데이터를 보여줍니다. 만약 내용이 없으면 버튼을 눌러주세요.")

selected_team_name = st.selectbox("구단을 선택하세요", list(TEAMS.keys()))
keyword = TEAMS[selected_team_name]

if st.button("새로고침", type="primary"):
    
    col1, col2, col3 = st.columns(3)
    
    # 1. 디시인사이드
    with col1:
        st.subheader("👿 디시인사이드")
        data = get_google_rss_issues("dcinside.com", keyword)
        if data:
            for item in data:
                st.markdown(f"""
                <div class="card" style="border-left: 5px solid #4b6584;">
                    <a href="{item['link']}" target="_blank"><b>{item['title']}</b></a><br>
                    <span style="color:grey; font-size:0.8em;">{item['date']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("최신 수집 데이터 없음")
            st.link_button(f"👉 {keyword} 갤러리/검색 바로가기", get_direct_link("DC", keyword))

    # 2. 엠엘비파크
    with col2:
        st.subheader("🏟️ 엠엘비파크")
        data = get_google_rss_issues("mlbpark.donga.com", keyword)
        if data:
            for item in data:
                st.markdown(f"""
                <div class="card" style="border-left: 5px solid #20bf6b;">
                    <a href="{item['link']}" target="_blank"><b>{item['title']}</b></a><br>
                    <span style="color:grey; font-size:0.8em;">{item['date']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("최신 수집 데이터 없음")
            st.link_button(f"👉 엠팍 '{keyword}' 검색 결과 보기", get_direct_link("MLB", keyword))

    # 3. 에펨코리아
    with col3:
        st.subheader("⚽ 에펨코리아")
        data = get_google_rss_issues("fmkorea.com", keyword)
        # 펨코는 RSS도 잘 안 잡힐 때가 많음 -> 버튼 유도
        if data:
            for item in data:
                st.markdown(f"""
                <div class="card" style="border-left: 5px solid #3867d6;">
                    <a href="{item['link']}" target="_blank"><b>{item['title']}</b></a><br>
                    <span style="color:grey; font-size:0.8em;">{item['date']}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("보안이 강력하여 직접 이동이 빠릅니다.")
            st.link_button(f"👉 펨코 '{keyword}' 탭 바로가기", get_direct_link("FMK", keyword))

