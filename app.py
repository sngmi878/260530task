
# 최신 시황정보 리포트 주요키워드 안내 및 요약
import traceback
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv
import html as html_parser
from urllib.parse import urljoin

load_dotenv()

# 1. 프롬프트 개선 (출력 형식을 조금 더 명확하게 지시)
SUMMARIZE_PROMPT = """다음 제공된 작성일자별 시황정보를 토대로 주요 키워드 3개를 뽑아주세요.
각 키워드에 대한 설명은 1~2문장으로 함께 제공해주세요.
키워드와 별개로 일자별 시황정보 리포트의 전반적인 내용을 500자 이내로 요약하여 보여주세요.
========
{content}
========
"""

def init_page():
    st.set_page_config(page_title="최신 시황정보 리포트")
    st.header("최신 시황정보를 키워드로 알아보기")
    st.sidebar.title("Options")

def select_model(temperature = 0):
    models = ("gpt-5.5", "gpt-5.4-mini")
    model = st.sidebar.radio("Choose a model:", models)
    if model == 'gpt-5.5':
        return ChatOpenAI(temperature = temperature, model = 'gpt-5.5')
    else:
        return ChatOpenAI(temperature = temperature, model = 'gpt-5.4-mini')

def init_chain():
    llm = select_model()
    prompt = ChatPromptTemplate.from_messages([
        ('user', SUMMARIZE_PROMPT)])
    chain = prompt | llm | StrOutputParser()
    return chain


def get_latest_report_urls():

    response = requests.get(
        "https://finance.naver.com/research/market_info_list.naver?page=1",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://finance.naver.com/"
        }
    )

    response.encoding = "euc-kr"

    soup = BeautifulSoup(response.text, "html.parser")

    latest_date = soup.select_one("td.date").get_text(strip=True)

    report_urls = []

    for row in soup.select("table.type_1 tr"):

        date_td = row.select_one("td.date")
        report_link = row.select_one(
            "a[href*='market_info_read.naver']"
        )

        if not date_td or not report_link:
            continue

        if date_td.get_text(strip=True) == latest_date:

            # href 원본 그대로 추출
            href = report_link.get("href")

            # &amp; -> &
            href = html_parser.unescape(href)

            # 절대 URL 변환
            full_url = urljoin(
                "https://finance.naver.com/research/",
                href
            )

            report_urls.append(full_url)

    return latest_date, report_urls

def get_content():

    contents = []

    for url in report_urls:

            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )

            html = BeautifulSoup(response.text, "html.parser")

            title = html.select_one("th.view_sbj")
            content = html.select_one("td.view_cnt")

            contents.append({
                "title": title.get_text(strip=True) if title else "",
                "content": content.get_text("\n", strip=True) if content else ""
            })

    return contents

def main():
    init_page()

    chain = init_chain()

    if st.button("최신 시황정보 분석하기"):

        try:
            with st.spinner("최신 시황정보 URL 수집중..."):
                latest_date, urls = get_latest_report_urls()

                # get_content()에서 report_urls를 사용하므로 전역변수로 저장
                global report_urls
                report_urls = urls

            st.subheader(f"최신 작성일 : {latest_date}")
            st.write(f"수집된 리포트 수 : {len(report_urls)}건")

            with st.spinner("리포트 본문 크롤링중..."):
                reports = get_content()

            # title + content를 하나의 문자열로 결합
            combined_content = ""

            for i, report in enumerate(reports, start=1):
                combined_content += f"""
[리포트 {i}]
제목: {report['title']}

본문:
{report['content']}

------------------------------
"""

            if not combined_content.strip():
                st.error("수집된 리포트 본문이 없습니다.")
                return

            with st.spinner("최신 시황정보 분석중..."):
                result = chain.invoke({
                    "content": combined_content
                })

            st.subheader("분석 결과")
            st.write(result)

            with st.expander("수집된 리포트 원문 보기"):
                for i, report in enumerate(reports, start=1):
                    st.markdown(f"### {i}. {report['title']}")
                    st.write(report["content"])

        except Exception as e:
            st.error("오류가 발생했습니다.")
            st.code(traceback.format_exc())

main()
