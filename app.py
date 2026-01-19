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

# company_df 인자를 추가하여 중복 로드를 방지합니다.
def get_stock_code_by_company(company_name: str, company_df: pd.DataFrame) -> str:
    if company_name.isdigit() and len(company_name) == 6:
        return company_name
    
    codes = company_df[company_df['회사명'] == company_name]['종목코드'].values
    if len(codes) > 0:
        return codes[0]
    else:
        return None

# 날짜 설정
today = datetime.datetime.now()
jan_1 = datetime.date(today.year, 1, 1)

# 사이드바 설정
st.sidebar.header("조회 조건 설정")
company_name_input = st.sidebar.text_input('조회할 회사를 입력하세요 (쉼표로 구분)')
selected_dates = st.sidebar.date_input(
    "조회할 기간을 선택하세요",
    (jan_1, today),
)
confirm_btn = st.sidebar.button('조회하기')

# KRX 명단 미리 로드
krx_df = get_krx_company_list()

# --- 메인 로직 ---
if confirm_btn:
    if not company_name_input:
        st.warning("조회할 회사 이름을 입력하세요.")
    else:
        try:
            all_prices = []
            company_list = [name.strip() for name in company_name_input.split(',')]
            
            # 날짜 포맷 변환 (FinanceDataReader용)
            start_date = selected_dates[0].strftime("%Y-%m-%d")
            end_date = selected_dates[1].strftime("%Y-%m-%d")

            for name in company_list:
                code = get_stock_code_by_company(name, krx_df)
                if code:
                    with st.info(f"{name}({code}) 데이터를 불러오는 중..."):
                        df = fdr.DataReader(code, start_date, end_date)
                        if not df.empty:
                            df['Company'] = name  # 기업명 컬럼 추가
                            all_prices.append(df)
                else:
                    st.info(f"'{name}'을(를) 찾을 수 없습니다.")

            if all_prices:
                # 모든 데이터 합치기
                final_df = pd.concat(all_prices)

                # 표 출력
                st.subheader("📅 일자별 상세 데이터")
                display_df = final_df.reset_index()
                display_df['Date'] = pd.to_datetime(display_df['Date']).dt.date
                display_df = display_df.set_index(['Date', 'Company']).sort_index(ascending=[False, True])

                st.dataframe(display_df, use_container_width=True)

                # 1. Plotly 시각화
                st.subheader("📈 주가 추이 비교")
                fig = px.line(
                    final_df.reset_index(),
                    x="Date", 
                    y="Close", 
                    color="Company",
                    title=f"종가 기준 추이 비교",
                    labels={'Close': '종가', 'Date': '날짜', 'Company': '기업명'}
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 2. 엑셀 다운로드 기능
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    final_df.to_excel(writer, index=True, sheet_name='Stock_Data')
                
                st.download_button(
                    label="📥 엑셀 파일 다운로드",
                    data=output.getvalue(),
                    file_name=f"주가조회_결과.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("조회된 데이터가 없습니다.")

        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")
            import traceback
            st.error(traceback.format_exc()) # 상세 에러 출력