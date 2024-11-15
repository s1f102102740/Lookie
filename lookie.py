import os
import glob
import subprocess
import base64
import requests
import time
from openai import OpenAI
from picamera2 import Picamera2
from pydub import AudioSegment
from pydub.playback import play
import io
import re
import asyncio
import shutil

OPENAI_API_KEY = "APIKEY"
OPENAI_API_BASE = "APIBASE"

IP_ADDLESS = "VOICEVOX_HOSTIP"

camera = Picamera2()

textlist = []
if os.path.exists("voice"):
    shutil.rmtree("voice")

os.makedirs("voice")

prompt = """あなたは最高のマスコットです。名前はルキです。自分のことはルキといってください。以下の ＃手順 を忠実に守って #テーマ に関する文章を50〜150字で日本語で作成してください。
        ＃テーマ:【画像に写っている一番近くにいる人はあなたに会いに来てくれた人です。その人の特徴や服装、服の色などを取り上げながら、ですます調の可愛らしい口調で褒めてください。また、最初に挨拶をしてください。そして、最後は別れの挨拶をしてください。】
        
        ＃手順:
        ・出力する前に何文字になったかをカウントしてください。
        ・カウントした結果、文字数の条件を満たしていることが確認できた場合に限ってタスクを終了してください。
        ・カウントした結果、文字数の条件を満たしていない場合は、文字数の条件を満たせるまで文字を追加したり削除したりして処理を繰り返してください
        ・文章の文字数は表記しないでください

        ＃文字数・下限:【50】字　・上限【150】字
        """

def capture():
    camera.start_and_capture_file("./test.jpg", delay=0.5)
    


def encode_image(image):
    with open(image, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_API_BASE)

def make_voice(text, num):
    host = IP_ADDLESS
    port = "50021"
    params = {
        "text" : text,
        "speaker" : 58
    }

    
    query = requests.post(
        f'http://{host}:{port}/audio_query',
        params = params
    )
    query_data = query.json()

    synthesis = requests.post(
        f"http://{host}:{port}/synthesis",
        params = params,
        json=query_data
        )
    

    with open(f"voice/{num}.wav", mode="wb") as f:
        f.write(synthesis.content)
    
        
def playwav(i):
    max_attempts = 16
    cnt = 0
    if i == 0:
        while True:
            path = os.path.abspath(f"voice/{i}.wav")
            if os.path.exists(path):
                with open(f"texts/{i}.txt", mode="w") as f:
                    f.write(textlist[i])
                with open(path, "rb") as f:
                    data = f.read()
                    audio = AudioSegment.from_file(io.BytesIO(data), format="wav")
                    play(audio)
                i += 1
                cnt = 0
                break
            else:
                time.sleep((cnt/10)**2)
                cnt += 1
    while True:
        path = os.path.abspath(f"voice/{i}.wav")
        if os.path.exists(path):
            with open(f"texts/{i}.txt", mode="w") as f:
                    f.write(textlist[i])
            with open(path, "rb") as f:
                data = f.read()
                audio = AudioSegment.from_file(io.BytesIO(data), format="wav")
                play(audio)
            i += 1
            cnt = 0
        
        else:
            if cnt >= max_attempts:
                for filename in os.listdir("voice"):
                    os.remove(f"voice/{filename}")
                if not os.path.isdir("voice"):
                    os.mkdir("voice")
                print("End")
                for p in glob.glob(os.path.join("texts/","*")):
                    if os.path.isfile(p):
                        os.remove(p)
                break

            else:
                time.sleep((cnt/10)**2)
                print(F"file:{i} Attempt number:{cnt}")
                cnt += 1

def Lookie():
    capture()
    time.sleep(1)
    image = "test.jpg"
    base64_image = encode_image(image)
    responce = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": [
                {
                "type": "text",
                "text": prompt
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail":"low"
                    }
                }
            ]
            }
        ],
        model="gpt-4o-mini",
        stream=True,
    )
    collected_chunks = []
    collected_messages = []
    i = 0

    asyncio.new_event_loop().run_in_executor(None, playwav, 0)

    for chunk in responce:
        collected_chunks.append(chunk)
        chunk_message = chunk.choices[0].delta.content
        if chunk_message != None:
            if re.match(r"[!?！？、。]", chunk_message):
                sentence = "".join(collected_messages)
                asyncio.new_event_loop().run_in_executor(None, make_voice, sentence, i)
                print(sentence)
                textlist.append(sentence)
                collected_messages = []
                i += 1
            else:
                collected_messages.append(chunk_message)
    print(textlist)
    os.remove("./test.jpg")