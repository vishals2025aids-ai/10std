import json, sqlite3
import config
import seed_science_data, seed_maths_data, seed_social_data, seed_english_data, seed_tamil_data

def get_science_unit_and_topic(page):
    if 1 <= page <= 15: u = 1
    elif 16 <= page <= 31: u = 2
    elif 32 <= page <= 41: u = 3
    elif 42 <= page <= 58: u = 4
    elif 59 <= page <= 73: u = 5
    elif 74 <= page <= 90: u = 6
    elif 91 <= page <= 105: u = 7
    elif 106 <= page <= 123: u = 8
    elif 124 <= page <= 136: u = 9
    elif 137 <= page <= 154: u = 10
    elif 155 <= page <= 172: u = 11
    elif 173 <= page <= 187: u = 12
    elif 188 <= page <= 202: u = 13
    elif 203 <= page <= 217: u = 14
    elif 218 <= page <= 228: u = 15
    elif 229 <= page <= 242: u = 16
    elif 243 <= page <= 260: u = 17
    elif 261 <= page <= 273: u = 18
    elif 274 <= page <= 286: u = 19
    elif 287 <= page <= 300: u = 20
    elif 301 <= page <= 314: u = 21
    elif 315 <= page <= 326: u = 22
    else: u = 23
    unit_title, topics = seed_science_data.SCIENCE_DATA[u]
    idx = (page - 1) % len(topics)
    topic_title, en_text, ta_text = topics[idx]
    full_en = unit_title.upper() + '\n\n' + topic_title.upper() + ' (PAGE ' + str(page) + ')\n\n' + en_text
    full_ta = unit_title + '\n\n' + topic_title + ' (பக்கம் ' + str(page) + ')\n\n' + ta_text
    return unit_title, full_en, full_ta

def get_maths_unit_and_topic(page):
    if 1 <= page <= 36: u = 1
    elif 37 <= page <= 85: u = 2
    elif 86 <= page <= 160: u = 3
    elif 161 <= page <= 200: u = 4
    elif 201 <= page <= 238: u = 5
    elif 239 <= page <= 268: u = 6
    elif 269 <= page <= 300: u = 7
    else: u = 8
    chapter_title, topics = seed_maths_data.MATHS_DATA[u]
    idx = (page - 1) % len(topics)
    topic_title, en_text, ta_text = topics[idx]
    full_en = chapter_title.upper() + '\n\n' + topic_title.upper() + ' (PAGE ' + str(page) + ')\n\n' + en_text
    full_ta = chapter_title + '\n\n' + topic_title + ' (பக்கம் ' + str(page) + ')\n\n' + ta_text
    return chapter_title, full_en, full_ta

def get_social_unit_and_topic(page):
    if 1 <= page <= 20: u = 1
    elif 21 <= page <= 38: u = 2
    elif 39 <= page <= 58: u = 3
    elif 59 <= page <= 80: u = 4
    elif 81 <= page <= 110: u = 5
    elif 111 <= page <= 138: u = 6
    elif 139 <= page <= 175: u = 7
    elif 176 <= page <= 215: u = 8
    elif 216 <= page <= 250: u = 9
    elif 251 <= page <= 295: u = 10
    else: u = 11
    unit_title, topics = seed_social_data.SOCIAL_DATA[u]
    idx = (page - 1) % len(topics)
    topic_title, en_text, ta_text = topics[idx]
    full_en = unit_title.upper() + '\n\n' + topic_title.upper() + ' (PAGE ' + str(page) + ')\n\n' + en_text
    full_ta = unit_title + '\n\n' + topic_title + ' (பக்கம் ' + str(page) + ')\n\n' + ta_text
    return unit_title, full_en, full_ta

def get_english_unit_and_topic(page):
    if 1 <= page <= 50: u = 1
    elif 51 <= page <= 100: u = 2
    elif 101 <= page <= 150: u = 3
    elif 151 <= page <= 200: u = 4
    elif 201 <= page <= 250: u = 5
    elif 251 <= page <= 300: u = 6
    else: u = 7
    unit_title, topics = seed_english_data.ENGLISH_DATA[u]
    idx = (page - 1) % len(topics)
    topic_title, en_text, ta_text = topics[idx]
    full_en = unit_title.upper() + '\n\n' + topic_title.upper() + ' (PAGE ' + str(page) + ')\n\n' + en_text
    full_ta = unit_title + '\n\n' + topic_title + ' (பக்கம் ' + str(page) + ')\n\n' + ta_text
    return unit_title, full_en, full_ta

def get_tamil_unit_and_topic(page):
    if 1 <= page <= 38: u = 1
    elif 39 <= page <= 76: u = 2
    elif 77 <= page <= 115: u = 3
    elif 116 <= page <= 155: u = 4
    elif 156 <= page <= 195: u = 5
    elif 196 <= page <= 235: u = 6
    elif 236 <= page <= 275: u = 7
    elif 276 <= page <= 315: u = 8
    else: u = 9
    unit_title, topics = seed_tamil_data.TAMIL_DATA[u]
    idx = (page - 1) % len(topics)
    topic_title, en_text, ta_text = topics[idx]
    full_ta = unit_title + '\n\n' + topic_title + ' (பக்கம் ' + str(page) + ')\n\n' + ta_text + '\n\n' + en_text
    return unit_title, full_ta, full_ta

def generate_all():
    records = []
    subjects = ['science', 'maths', 'social', 'english', 'tamil']
    for subj in subjects:
        for p in range(1, 351):
            if subj == 'science':
                chapter, text_en, text_ta = get_science_unit_and_topic(p)
                lang = 'en'
            elif subj == 'maths':
                chapter, text_en, text_ta = get_maths_unit_and_topic(p)
                lang = 'en'
            elif subj == 'social':
                chapter, text_en, text_ta = get_social_unit_and_topic(p)
                lang = 'en'
            elif subj == 'english':
                chapter, text_en, text_ta = get_english_unit_and_topic(p)
                lang = 'en'
            elif subj == 'tamil':
                chapter, text_en, text_ta = get_tamil_unit_and_topic(p)
                lang = 'ta'
            rec = {
                'page_id': subj + '_p' + str(p),
                'subject': subj,
                'chapter': chapter,
                'page': p,
                'text': text_en,
                'text_ta': text_ta,
                'language': lang
            }
            records.append(rec)
    return records

def run():
    recs = generate_all()
    print('Generated', len(recs), 'records')
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.PAGES_JSONL, 'w', encoding='utf-8') as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    print('Written to pages.jsonl')

    conn = sqlite3.connect(str(config.DB_PATH))
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS chunks')
    cur.execute('DROP TABLE IF EXISTS pages')

    cur.execute('CREATE TABLE pages (page_id TEXT PRIMARY KEY, subject TEXT NOT NULL, chapter TEXT NOT NULL, page INTEGER NOT NULL, text TEXT NOT NULL, text_ta TEXT, language TEXT NOT NULL)')
    cur.execute('CREATE INDEX idx_pages_num_subj ON pages(page, subject)')

    cur.execute('CREATE TABLE chunks (chunk_id INTEGER PRIMARY KEY, page_id TEXT NOT NULL, text TEXT NOT NULL, FOREIGN KEY (page_id) REFERENCES pages(page_id))')

    def chunk_words(text, size=180, overlap=30):
        words = text.split()
        if not words:
            return []
        if len(words) <= size:
            return [ ' '.join(words) ]
        chunks = []
        step = max(1, size - overlap)
        for start in range(0, len(words), step):
            piece = ' '.join(words[start : start + size])
            chunks.append(piece)
            if start + size >= len(words):
                break
        return chunks

    chunk_id = 0
    for r in recs:
        cur.execute('INSERT INTO pages VALUES (?, ?, ?, ?, ?, ?, ?)', (r['page_id'], r['subject'], r['chapter'], r['page'], r['text'], r['text_ta'], r['language']))

        for piece in chunk_words(r['text']):
            cur.execute('INSERT INTO chunks VALUES (?, ?, ?)', (chunk_id, r['page_id'], piece))
            chunk_id += 1


    conn.commit()
    conn.close()
    print('Database populated with', len(recs), 'pages and', chunk_id, 'chunks')

if __name__ == '__main__':
    run()
