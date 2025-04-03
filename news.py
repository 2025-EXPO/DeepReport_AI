import requests
import logging
import time
from bs4 import BeautifulSoup

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("aitimes_crawler.log"), logging.StreamHandler()],
)


class AITimesAgent:
    def __init__(self, start_idx=168551):
        self.base_url = "https://www.aitimes.com/news/articleView.html?idxno="
        self.current_idx = start_idx
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/91.0.4472.124 Safari/537.36"
        }

    def check_article_exists(self, soup):
        """기사가 존재하는지 확인하고 상태를 반환"""
        if soup.find(string=lambda text: text and "존재하지 않는 링크" in text):
            return False
        if soup.find(string=lambda text: text and "노출대기중인 기사" in text):
            return False
        return bool(soup.select_one("h3.heading")) and bool(soup.select_one("#article-view-content-div"))

    def parse_article(self, soup, article_id):
        """기사 정보 파싱"""
        try:
            title = soup.select_one("h3.heading").text.strip()
            paragraphs = soup.select("#article-view-content-div p")
            content = "\n".join([p.text.strip() for p in paragraphs])

            return {
                "id": article_id,
                "title": title,
                "content": content,
                "url": f"{self.base_url}{article_id}",
                "crawled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        except Exception as e:
            logging.error(f"기사 파싱 중 오류 발생 (ID: {article_id}): {e}")
            return None

    def crawl_next_article(self):
        """다음 기사 크롤링"""
        while True:
            url = f"{self.base_url}{self.current_idx}"
            try:
                response = requests.get(url, headers=self.headers)
                soup = BeautifulSoup(response.text, "html.parser")

                if self.check_article_exists(soup):
                    article_data = self.parse_article(soup, self.current_idx)
                    self.current_idx += 1
                    return article_data

            except Exception as e:
                logging.error(f"ID {self.current_idx} 크롤링 중 오류 발생: {e}")

            self.current_idx += 1  # 다음 기사로 이동
            time.sleep(1)  # 과부하 방지를 위한 대기
