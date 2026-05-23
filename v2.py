import pandas as pd
import time
import os
from datetime import datetime, timedelta  # 💡 timedelta 추가됨
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

print("🚀 [버전 2.4] 대시보드 양식 맞춤형 크롤러 시작 (날짜 선택 기능 추가)...")

# ══════════════════════════════════════════════════════════════════
# 💡 [추가] 조회할 날짜 입력받기
# ══════════════════════════════════════════════════════════════════
user_date = input("📅 조회할 체크인 날짜를 입력하세요 (예: 2026-05-25, 오늘 날짜는 그냥 엔터!): ").strip()

if user_date:
    try:
        checkin_date = datetime.strptime(user_date, "%Y-%m-%d").date()
    except ValueError:
        print("❌ 날짜 형식이 잘못되었습니다 (YYYY-MM-DD). 기본값인 오늘 날짜로 진행합니다.")
        checkin_date = datetime.now().date()
else:
    checkin_date = datetime.now().date()

checkout_date = checkin_date + timedelta(days=1)

print(f"🎯 셋팅 완료! 조회 일정: {checkin_date} ~ {checkout_date}")
print("-" * 50)
# ══════════════════════════════════════════════════════════════════

# 1. 대상 지점 코드 불러오기
try:
    with open('yanolja_ids.txt', 'r', encoding='utf-8') as f:
        place_ids = [line.strip() for line in f.readlines() if line.strip()]
except:
    with open('yanolja_ids.txt', 'r', encoding='cp949') as f:
        place_ids = [line.strip() for line in f.readlines() if line.strip()]

# 2. 브라우저 세팅 (백그라운드 모드)
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
crawled_data = []

# 3. 크롤링 시작
for idx, pid in enumerate(place_ids):
    # 💡 [수정] url 끝에 checkinDate와 checkoutDate 파라미터 추가!
    url = f"https://nol.yanolja.com/stay/domestic/{pid}?checkinDate={checkin_date}&checkoutDate={checkout_date}"
    print(f"[{idx+1}/{len(place_ids)}] 👉 {pid} 수집 중...")
    
    try:
        driver.get(url)
        time.sleep(3.5)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # 숙소명 추출
        try: place_name = soup.find('h1').text.strip()
        except: place_name = f"지점_{pid}"

        room_cards = soup.find_all('div', class_=lambda c: c and 'pc:flex-row' in c and 'pc:py-20' in c)
        
        for card in room_cards:
            room_name = card.find('h2').text.strip() if card.find('h2') else "알수없음"
            rent_price, stay_price = 0, 0
            rent_status, stay_status = "마감", "마감"
            
            # 숙박 정보
            stay_label = card.find('span', string='숙박')
            if stay_label:
                stay_block = stay_label.find_parent('div', class_=lambda c: c and 'box-border' in c)
                p_tag = stay_block.find('span', class_=lambda c: c and 'typography-subtitle-18-bold' in c)
                if p_tag: stay_price = int(p_tag.text.replace(',', '').strip())
                if not stay_block.find(string=lambda t: t and '예약마감' in t): stay_status = "판매중"

            # 대실 정보
            rent_label = card.find('span', string='대실')
            if rent_label:
                rent_block = rent_label.find_parent('div', class_=lambda c: c and 'box-border' in c)
                p_tag = rent_block.find('span', class_=lambda c: c and 'typography-subtitle-18-bold' in c)
                if p_tag: rent_price = int(p_tag.text.replace(',', '').strip())
                if not rent_block.find(string=lambda t: t and '예약마감' in t): rent_status = "판매중"

            # 💡 [수정] "체크인" 컬럼에 실제 조회한 날짜 넣기
            crawled_data.append({
                "지점코드": pid,
                "숙소명": place_name,
                "객실타입": room_name,
                "대실상태": rent_status,
                "대실금액": rent_price,
                "숙박상태": stay_status,
                "숙박금액": stay_price,
                "수집일시": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "체크인": checkin_date.strftime("%Y-%m-%d") # 💡 빈 칸 대신 실제 날짜 입력!
            })
            
    except Exception as e:
        print(f"   ❌ 에러: {pid}")

driver.quit()

# 4. 저장 (data 폴더 안에 저장)
if crawled_data:
    df = pd.DataFrame(crawled_data)
    # 컬럼 순서 강제 재배치
    column_order = ["지점코드", "숙소명", "객실타입", "대실상태", "대실금액", "숙박상태", "숙박금액", "수집일시", "체크인"]
    df = df[column_order]
    
    # data 폴더가 없으면 생성
    if not os.path.exists('data'):
        os.makedirs('data')
    
    # 최종 저장
    df.to_csv('data/price_data_new.csv', index=False, encoding='utf-8-sig')
    print(f"\n🎉 모든 작업 완료! 'data/price_data_new.csv' 파일이 업데이트 되었습니다.")