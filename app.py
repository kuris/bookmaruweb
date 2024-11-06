from flask import Flask, render_template, request, jsonify
import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_books():
    keyword = request.form.get('keyword')
    if not keyword:
        return jsonify({"error": "검색어를 입력하세요."}), 400

    url = "https://www.yes24.com/Product/Search"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }
    params = {'domain': 'ALL', 'query': keyword}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        books = []
        items = soup.select('#yesSchList > li')
        for item in items:
            title_elem = item.select_one('div.item_info div.info_row.info_name a.gd_name')
            if not title_elem:
                continue
            title = title_elem.text.strip()
            goods_no = title_elem['href'].split('/')[-1]
            book_url = f"https://www.yes24.com/Product/Goods/{goods_no}"
            image_url = f"http://image.yes24.com/goods/{goods_no}/XL"
            author_elem = item.select_one('a[href*="query"][href*="author"]')
            author = author_elem.text.strip() if author_elem else "저자 미상"
            publisher_elem = item.select_one('span.authPub > a:nth-child(2), a[href*="PublisherId"]')
            publisher = publisher_elem.text.strip() if publisher_elem else "출판사 미상"
            price_elem = item.select_one('div.info_row.info_price strong.price')
            price = price_elem.text.strip() if price_elem else "가격 정보 없음"

            books.append({
                "title": title,
                "author": author,
                "publisher": publisher,
                "price": price,
                "url": book_url,
                "image_url": image_url
            })
        return jsonify({"books": books})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/view_contents', methods=['POST'])
def view_contents():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "URL이 제공되지 않았습니다."}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        contents_div = soup.select_one('#infoset_toc')

        if contents_div:
            # 특정 태그들을 텍스트 형식으로 변환하여 서식 유지
            for br in contents_div.find_all("br"):
                br.replace_with("\n")  # <br> 태그를 줄바꿈으로 변환
            for li in contents_div.find_all("li"):
                li.insert_before("- ")  # <li> 항목 앞에 '-' 추가
                li.append("\n")  # 항목 끝에 줄바꿈 추가
            for p in contents_div.find_all("p"):
                p.append("\n\n")  # <p> 태그 뒤에 두 줄바꿈 추가 (문단 구분)

            formatted_contents = contents_div.get_text(separator="\n").strip()  # 최종 텍스트 추출 및 정리
            return jsonify({"contents": formatted_contents})
        
        return jsonify({"error": "목차 정보가 없습니다."})
    
    except Exception as e:
        return jsonify({"error": f"목차를 불러오는 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/save_text', methods=['POST'])
def save_contents_to_text():
    data = request.get_json()
    contents = data.get('contents')
    title = data.get('title')

    if not contents or not title:
        return jsonify({"error": "저장할 목차 내용이 없습니다."}), 400

    folder_path = "saved_texts"
    os.makedirs(folder_path, exist_ok=True)
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(folder_path, f"{title}_{current_time}.txt")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(contents)
        return jsonify({"message": f"텍스트로 저장되었습니다: {file_path}"})
    except Exception as e:
        return jsonify({"error": f"파일 저장 중 오류가 발생했습니다: {str(e)}"}), 500

@app.route('/create_note', methods=['POST'])
def create_reading_note():
    data = request.get_json()
    contents = data.get('contents')
    title = data.get('title')
    author = data.get('author')
    publisher = data.get('publisher')

    if not contents or not title:
        return jsonify({"error": "독서노트를 생성할 목차 내용이 없습니다."}), 400

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    reading_note_template = f"""
=== 독서노트 ===
작성일: {current_time}
[도서 정보]
제목: {title}
저자: {author}
출판사: {publisher}
[목차 정보]
{contents}
[독서 메모]
- 주요 내용:
- 인상 깊은 구절:
- 나의 생각:
- 실천할 점:
"""

    folder_path = "saved_texts"
    os.makedirs(folder_path, exist_ok=True)
    
    safe_title = title.replace('/', '_').replace('\\', '_')
    file_name = f"{safe_title}_독서노트_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    file_path = os.path.join(folder_path, file_name)

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(reading_note_template)
        return jsonify({"message": f"독서노트가 생성되었습니다: {file_path}"})
    except Exception as e:
        return jsonify({"error": f"독서노트 생성 중 오류가 발생했습니다: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)