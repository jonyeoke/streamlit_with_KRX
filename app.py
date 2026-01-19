# 표준 라이브러리
import datetime
from io import BytesIO

# 서드파티 라이브러리
import streamlit as st
import pandas as pd
import FinanceDataReader as fdr
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. 캐싱 설정 (로딩 속도 개선) ---
@st.cache_data(ttl=3600)
def get_krx_company_list() -> pd.DataFrame:
    try:
        url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
        df_listing = pd.read_html(url, header=0, flavor='bs4', encoding='EUC-KR')[0]
        
        df_listing = df_listing[['회사명', '종목코드']].copy()
        df_listing['종목코드'] = df_listing['종목코드'].apply(lambda x: f'{x:06}')
        return df_listing
    except Exception as e:
        st.error(f"상장사 명단을 불러오는 데 실패했습니다: {e}")
        return pd.DataFrame(columns=['회사명', '종목코드'])

def get_stock_code_by_company(company_name: str, company_df: pd.DataFrame) -> str:
    if company_name.isdigit() and len(company_name) == 6:
        return company_name
    
    codes = company_df[company_df['회사명'] == company_name]['종목코드'].values
    if len(codes) > 0:
        return codes[0]
    else:
        return None

# --- 2. 페이지 설정 및 세션 상태 초기화 ---
st.set_page_config(page_title="주가 분석 대시보드", layout="wide")

# 다운로드 시 데이터가 사라지지 않도록 세션 상태에 저장
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# 날짜 설정
today = datetime.datetime.now()
jan_1 = datetime.date(today.year, 1, 1)

# --- 3. 사이드바 UI ---
st.sidebar.header("조회 조건 설정")

# <br> 태그를 사용하여 줄바꿈 적용
company_name_input = st.sidebar.text_input(
    '조회할 회사를 입력하세요 (쉼표로 구분)<br>ex) 삼성전자, LG, SK하이닉스'
)

selected_dates = st.sidebar.date_input(
    "조회할 기간을 선택하세요",
    (jan_1, today),
)

confirm_btn = st.sidebar.button('조회하기')

# KRX 명단 미리 로드 (캐싱 적용됨)
krx_df = get_krx_company_list()

# --- 4. 데이터 수집 로직 (버튼 클릭 시 실행) ---
if confirm_btn:
    if not company_name_input:
        st.warning("조회할 회사 이름을 입력하세요.")
    else:
        try:
            all_prices = []
            company_list = [name.strip() for name in company_name_input.split(',')]
            
            # 날짜 포맷 변환
            start_date = selected_dates[0].strftime("%Y-%m-%d")
            end_date = selected_dates[1].strftime("%Y-%m-%d")

            # 로딩 바(spinner) 사용
            with st.spinner("데이터를 불러오는 중입니다..."):
                for name in company_list:
                    code = get_stock_code_by_company(name, krx_df)
                    if code:
                        df = fdr.DataReader(code, start_date, end_date)
                        if not df.empty:
                            df['Company'] = name
                            all_prices.append(df)
                    else:
                        st.error(f"'{name}'을(를) 찾을 수 없습니다.")

            if all_prices:
                # 합쳐진 데이터를 세션 상태에 보관
                st.session_state.final_df = pd.concat(all_prices)
            else:
                st.session_state.final_df = None
                st.info("조회된 데이터가 없습니다.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# --- 5. 화면 출력 로직 (세션 상태에 데이터가 있으면 항상 표시) ---
if st.session_state.final_df is not None:
    final_df = st.session_state.final_df
    
    # --- 데이터 전처리 및 표 출력 ---
    st.subheader("📅 일자별 상세 데이터")
    
    # 시간 제거 및 그룹화
    display_df = final_df.reset_index()
    display_df['Date'] = pd.to_datetime(display_df['Date']).dt.date # 시간 제거 핵심
    display_df = display_df.set_index(['Date', 'Company']).sort_index(ascending=[False, True])

    st.dataframe(display_df, use_container_width=True)

    # --- Plotly 시각화 ---
    st.subheader("📈 주가 추이 비교")
    fig = px.line(
        final_df.reset_index(),
        x="Date", 
        y="Close", 
        color="Company",
        title=f"종가 기준 주가 추이",
        labels={'Close': '가격', 'Date': '날짜', 'Company': '기업명'},
        template="plotly_white"
    )
    # x축 날짜 포맷 정리
    fig.update_xaxes(tickformat="%Y-%m-%d")
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 엑셀 다운로드 기능 ---
    # 다운로드 버튼을 눌러도 세션 상태 덕분에 화면이 유지됨
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 그룹화된 형태(display_df)로 저장하고 싶다면 display_df 사용
        display_df.to_excel(writer, index=True, sheet_name='Stock_Data')
    
    st.download_button(
        label="📥 엑셀 파일 다운로드",
        data=output.getvalue(),
        file_name=f"주가조회_결과_{today.strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )