from email import message_from_bytes
from aiosmtpd.controller import Controller
from deepstack_sdk import ServerConfig, Detection
from aiosmtpd.smtp import AuthResult, LoginPassword
import ipaddress, subprocess, schedule, asyncio, logging, requests, shlex, time, json, cv2, os, re


bot_token         = os.environ['TELEGRAM_TOKEN']
api_url           = f"https://api.telegram.org/bot{bot_token}"
chat_id           = os.environ['TELEGRAM_CHAT_ID']
deepstack_ip      = os.environ['DEEPSTACK_IP']
deepstack_port    = os.environ['DEEPSTACK_PORT']
stream_key        = os.environ['STREAM_KEY']
stream_url        = os.environ['STREAM_URL']
server_ip         = os.environ['SERVER_IP']
server_port       = os.environ['SERVER_PORT']
rtsp_url          = os.environ['RTSP_URL']
server_username   = os.environ['SERVER_USERNAME']
server_password   = os.environ['SERVER_PASSWORD']
cam_username      = os.environ['CAM_USERNAME']
cam_password      = os.environ['CAM_PASSWORD']
device_regex      = os.environ['DEVICE_REGEX']
objects           = os.environ['OBJECTS']
confidance        = os.environ['CONFIDANCE']
objects_list      = objects.split(",")
confidance_list   = confidance.split(",")
station_list      = []
list              = []
ip_address        = ""
device_name       = ""
server_auth = {server_username.encode(): server_password.encode(),}

logging.basicConfig(level = logging.INFO,
                    format = '%(asctime)s:%(levelname)s:%(name)s:%(message)s')

detect_dict = {}
for i in range(len(objects_list)):
    detect_dict[objects_list[i]] = confidance_list[i]

st_list = {
    "station": [
    ]
}
################################################## FACE DETECTION ##################################################

def face_registeration(caption):
    user_image = open(f"/server/user/{caption}.jpg","rb").read()
    response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/register",
        files={"image":user_image},data={"userid":f"{caption}"}).json()
    send_message(chat_id, text =f"Yeni kişi kaydedildi: {caption}")

def face_recognition(file="image.jpg"):
    image_data = open(file,"rb").read()
    faces = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/list").json()
    response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/recognize",
        files={"image":image_data},data={"min_confidence":confidance}).json()
    for user in response["predictions"]:
        if user['userid'] in faces['faces']:
            text_caption = f"{user['userid']} {device_name} istasyonunda!!!"
            send_Photo(chat_id, file, text_caption)
    os.remove('image.jpg')

def faces_listing():
    user_list = []
    faces = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/list").json()
    f = faces['faces']
    for u in f:
        user_list.append(u)
    result = '\n'.join(user_list)
    send_message(chat_id, text=f"Kayıtlı Kişiler:\n{result}")

def face_deleting(text_list):
    user = text_list[1]+" "+text_list[2]
    response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/delete",
        data={"userid":user}).json()
    send_message(chat_id, f"{user} adlı kayıt silindi.")

def send_message(chat_id, text):
    data={'chat_id': chat_id, 'text': text}
    req = requests.post(f"{api_url}/sendMessage",data=data)
    return req.json()

def send_photo(chat_id, file, text_caption):
    data = {"chat_id": chat_id, "caption": text_caption}
    api = f"{api_url}/sendPhoto"
    with open(file, "rb") as image_file:
        req = requests.post(api, data=data, files={"photo": image_file})
    return req.json()

def get_file(file_id, caption):
    api = f"{api_url}/getFile"
    r = requests.get(api, params={'file_id': file_id})
    file_info = r.json()['result']
    file_path = file_info['file_path']
    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    r = requests.get(file_url)
    with open(f"/server/user/{caption}.jpg", "wb") as f:
        f.write(r.content)
        f.close()
    face_registeration(caption)
####################################################################################################################    
def records_file_remove():
    listing = os.listdir("/server/records")
    for file in listing:
        if str.lower(file[-3:]) == "mkv":
            os.remove(file)
    try:
        send_Message(chat_id, text= "Video kayıtları silindi.")
    except TypeError:
        pass

def send_Video(bot_token, chat_id, video_file):
    files = {'video': open(f"/server/records/{video_file}", 'rb')}
    data = {'chat_id' : chat_id}
    r = requests.post(f"{api_url}/sendVideo",data, files=files)
    return r.json()

with open('data.json', 'w') as f:
  json.dump(st_list, f, ensure_ascii=False)

def live_Stream(command, chat_id, station_caption):
    process = subprocess.Popen(shlex.split(command),shell=False,stdout=subprocess.PIPE)
    send_Message(chat_id, text=f"\"{station_caption}\" için canlı yayın başladı. \n\"KATIL\" butonuna tıklayarak canlı yayına katılabilirsiniz.")

def send_Photo(file, device_name, ip_address):
    keyboard=json.dumps({'inline_keyboard':[
        [{'text':'Canlı Video Başlat','callback_data':ip_address}],
        [{'text':'Canlı Videoyu Sonlandır','callback_data':'stop'}]]})
    api = f"{api_url}/sendPhoto"
    with open(file, "rb") as image_file:
        multipart_form_data = {
        'photo': (image_file),
        'action': (None, 'send'),
        'chat_id': (None, chat_id),
        'caption': (None, f"{device_name} {ip_address}"),
        'parse_mode': (None, 'Markdown'),
        'reply_markup': (None, keyboard )
        }
        req = requests.post(api, files=multipart_form_data)
    return req.json()

def send_Message(chat_id, text):
    data={'chat_id': chat_id, 'text': text}
    req = requests.post(f"{api_url}/sendMessage",data=data)
    return req.json()

def get_url(urls):
    response = requests.get(urls)
    content = response.content.decode('utf8')
    return content

def get_json(urls): 
    content = get_url(urls)
    js      = json.loads(content)
    return js

def get_updates(offset=None): 
    urls = f"{api_url}/getUpdates?timeout=60"
    if offset:
        urls += f"&offset={offset}"
    js = get_json(urls)
    return js

def get_last_update_id(updates): 
    update_ids = []
    for update in updates['result']:
        update_ids.append(int(update['update_id']))
    return max(update_ids)

def echo_all_updates(updates):
    for update in updates['result']:
        try:
            chat_id = update['message']['chat']['id']
            command_message = update['message']['text']
            f = open('data.json')
            data = json.load(f)
            for i in data['station']:
                if command_message.upper() == i['name']:
                    listing = os.listdir("/server/records")
                    for video_file in listing:
                        if str.lower(video_file[:-4]) == i['ip']:
                            send_Video(bot_token, chat_id,video_file)
        except (KeyError, IndexError):
            pass
        try:
            command_message = update['message']['text']
            text_list = command_message.split(" ")
            if command_message == "/list":
                faces_listing()
            if text_list[0] == "/remove":
                face_deleting(text_list)
            if update['message']['caption']:
                pass
        except (IndexError, KeyError):
                pass
        try:
            photo   = update['message']['photo'][-1]
            file_id = photo['file_id']
            caption = update['message']['caption']
            get_file(file_id,caption)
        except (KeyError, IndexError):
            pass
        try:
            dataset = update['callback_query']['data']
            station_caption = update['callback_query']['message']['caption']
            chat_id = update['callback_query']['message']['chat']['id']
            try:
                if dataset == 'stop':
                    useer = update['callback_query']['message']['from']['username']
                    os.system("kill -9 $(pgrep ffmpeg)")
                    send_Message(chat_id, text='Canlı yayın sonlandırıldı.')
                elif ipaddress.ip_address(dataset):
                    camera_path = f"rtsp://{cam_username}:{cam_password}@{dataset}:{rtsp_url}"
                    command = f"ffmpeg -hide_banner -y -loglevel error -i {camera_path} -vcodec copy -acodec copy -t 120 /server/records/{dataset}.mkv -c:v libx264 -c:a aac -f flv {stream_url}{stream_key}"
                    if (os.system("kill -9 $(pgrep ffmpeg)")) == 512:
                        live_Stream(command, chat_id, station_caption)
                    else:
                        live_Stream(command, chat_id, station_caption)
                else:
                    pass
                    return dataset
            except IndexError as e:
                print(e)
        except KeyError as e:
            print(e)

def write_json(new_data,device_name, filename='data.json'):
    with open(filename,mode='r+') as file:
        file_data = json.load(file)
        key = len(file_data['station'])
        for i in range(key):
            data = file_data['station'][i]['name']
            station_list.append(data)
        if device_name in station_list:
            pass
        else:
            file_data["station"].append(new_data)
            file.seek(0)
            json.dump(file_data, file, indent = 4)

def authenticator(server, session, envelope, mechanism, auth_data):
    assert isinstance(auth_data, LoginPassword)
    username = auth_data.login
    password = auth_data.password
    if server_auth.get(username) == password:
        return AuthResult(success=True)
    else:
        return AuthResult(success=False, handled=False)

class SMTPHandler:
    async def handle_DATA(self, server, session, envelope):
        remote_ip = []
        for ip in session.peer:
            remote_ip.append(ip)
        m = message_from_bytes(envelope.content)
        if m.is_multipart():
            for part in m.walk():
                ctype = part.get_content_type()
                disposition = str(part.get('Content-Disposition'))
                if ctype == 'text/html':
                    body = part.get_payload(decode=True)
                    print("\n******************************************************* - text/html MAIL CONTENTS - *******************************************************\n")
                    print(body)
                    device = re.search(device_regex, str(body))
                    print("\n")
                    print(device)
                    print("\n*******************************************************************************************************************************************\n")
                    global ip_address
                    ip_address = remote_ip[0]
                    list.append(ip_address)
                    try:
                        global device_name
                        device_name = device[0]
                        aDict = {
                                    'name':device_name,
                                    'ip':ip_address,
                            }
                        write_json(aDict,device_name)
                    except (IndexError, TypeError):
                        device_name = "Cihaz adı bulunamadı. Log'u kontrol ederek gelen text/html MAIL CONTENTS \
                        veya text/plain MAIL CONTENTS body bloğundan Cihaz Adınızı bulan regex kodunu düzenleyin."
                        if device_name == "Cihaz adı bulunamadı. Log'u kontrol ederek gelen text/html MAIL CONTENTS \
                        veya text/plain MAIL CONTENTS body bloğundan Cihaz Adınızı bulan regex kodunu düzenleyin.":
                            pass
                if  ctype == 'text/plain':
                    body = part.get_payload(decode=True)
                    print("\n******************************************************* - text/plain MAIL CONTENTS - *******************************************************\n")
                    print(body)
                    device = re.search(device_regex, str(body))
                    print("\n")
                    print(device)
                    print("\n*******************************************************************************************************************************************\n")
                    ip_address = remote_ip[0]
                    list.append(ip_address)
                    try:
                        device_name = device[0]
                        aDict = {
                                    'name':device_name,
                                    'ip':ip_address,
                            }
                        write_json(aDict,device_name)
                    except (IndexError, TypeError):
                        device_name = "Cihaz adı bulunamadı. Log'u kontrol ederek gelen text/html MAIL CONTENTS \
                        veya text/plain MAIL CONTENTS body bloğundan Cihaz Adınızı bulan regex kodunu düzenleyin."
                        if device_name == "Cihaz adı bulunamadı. Log'u kontrol ederek gelen text/html MAIL CONTENTS \
                        veya text/plain MAIL CONTENTS body bloğundan Cihaz Adınızı bulan regex kodunu düzenleyin.":
                            pass
                if (ctype == 'application/x-msdownload' or ctype == 'application/octet-stream' or ctype == 'image/jpeg' or ctype == 'image/png' or ctype == 'multipart/mixed' or ctype == 'multipart/alternative' ) and 'attachment;' in disposition:
                    open('latest.jpg', 'wb').write(part.get_payload(decode=True,))
                    image_data  = open('latest.jpg',"rb").read()
                    response    = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/detection",files={"image":image_data}).json()
                    coordinates = [] 
                    mlistp      = []
                    for object in response["predictions"]:
                        for key, value in detect_dict.items():
                            if (object['label'] == key and object['confidence']>=float(value)):
                                y1 = int(object["y_max"])
                                y2 = int(object["y_min"])
                                x1 = int(object["x_max"])
                                x2 = int(object["x_min"])
                                z1 = object["label"]
                                coordinates=([x1,y2,x2,y1,z1])
                                mlistp.append(coordinates)
                                img= cv2.imread('latest.jpg')
                        i=0
                        for i in range(len(mlistp)):
                            imgdr = cv2.rectangle(img, (mlistp[i][0], mlistp[i][1]), \
                                    (mlistp[i][2], mlistp[i][3]),(0,255,0), 2)
                            imgdr = cv2.putText(imgdr, mlistp[i][4], (mlistp[i][2], mlistp[i][3]+10), \
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.4,(255,255,255), 1)
                            cv2.imwrite("image.jpg",imgdr)
        try:
            os.remove('latest.jpg')
            send_Photo('image.jpg', device_name, ip_address)
            face_recognition('image.jpg')
        except FileNotFoundError:
            pass
        return '250 OK'
schedule.every().day.at("00:00").do(records_file_remove)
def main():
    server = Controller(SMTPHandler(),
        hostname=server_ip,
        port=server_port,
        authenticator=authenticator,
        auth_required=True,
        auth_require_tls=False,)
    server.start()
    last_update_id = None
    while True:
        schedule.run_pending()
        updates = get_updates(last_update_id)
        if updates is not None:
            if len(updates['result']) > 0:
                last_update_id = get_last_update_id(updates) + 1
                echo_all_updates(updates)
if __name__ == '__main__':
    try:
        try:
            main()
        except requests.exceptions.ConnectionError:
            main()
    except KeyboardInterrupt:
        print("Server Durduruldu.")
