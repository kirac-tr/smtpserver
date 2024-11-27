from datetime import datetime
from email import message_from_bytes
from aiosmtpd.controller import Controller
from deepstack_sdk import ServerConfig, Detection
from aiosmtpd.smtp import AuthResult, LoginPassword
import ipaddress, subprocess, asyncio, requests, shlex, email, json, cv2, os, re

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
file_remove_time  = os.environ['FILE_REMOVE_TIME']
server_auth       = {server_username.encode(): server_password.encode(),}
objects_list      = objects.split(",")
confidance_list   = confidance.split(",")
detect_dict       = {}
station_list      = []
list              = []
ip_address        = ""
now               = datetime.now()
timestamp         = int(now.timestamp())

for i in range(len(objects_list)):
    detect_dict[objects_list[i]] = confidance_list[i]

st_list = {
    "station": [
    ]
}
################################################## FACE DETECTION ##################################################

## new user added
def face_registeration(caption):
    try:
        user_image = open(f"/server/user/{caption}.jpg","rb").read()
    except FileNotFoundError:
        pass
    response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/register",
        files={"image":user_image},data={"userid":f"{caption}"}).json()
    send_message(chat_id, text =f"New person registered: {caption}")

## face list
def faces_listing():
    user_list = []
    faces = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/list").json()
    f = faces['faces']
    for u in f:
        user_list.append(u)
    result = '\n'.join(user_list)
    send_message(chat_id, text=f"Registered Persons:\n{result}")

## face delete
def face_deleting(text_list):
    user = text_list[1]+" "+text_list[2]
    response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/delete",
        data={"userid":user}).json()
    send_message(chat_id, f"{user} record has been deleted.")

## deepstack recognize send photo
def send_photo(chat_id, file, text_caption):
    data = {"chat_id": chat_id, "caption": text_caption}
    api = f"{api_url}/sendPhoto"
    with open(file, "rb") as image_file:
        req = requests.post(api, data=data, files={"photo": image_file})
    os.remove(file)
    return req.json()

## incoming picture control
def get_file(file_id, caption):
    api = f"{api_url}/getFile"
    r = requests.get(api, params={'file_id': file_id})
    file_info = r.json()['result']
    file_path = file_info['file_path']
    file_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
    r = requests.get(file_url)
    try:
        with open(f"/server/user/{caption}.jpg", "wb") as f:
            f.write(r.content)
            f.close()
    except FileNotFoundError:
        pass
    face_registeration(caption)

####################################################################################################################  

## deletes recorded videos during live broadcast  
async def records_file_remove():
    print("Video recording have been deleted.")
    try:
        listing = os.listdir("/server/records")
    except FileNotFoundError:
        pass
    try:
        for file in listing:
            if str.lower(file[-3:]) == "mkv":
                try:
                    os.remove(file)
                except FileNotFoundError:
                    pass
    except UnboundLocalError:
        pass
    try:
        send_message(chat_id, text= "Video recordings have been deleted.")
    except TypeError:
        pass

## used to capture recorded videos to group orn: devicename
def send_Video(bot_token, chat_id, video_file):
    try:
        files = {'video': open(f"/server/records/{video_file}", 'rb')}
    except FileNotFoundError:
        pass
    data = {'chat_id' : chat_id}
    r = requests.post(f"{api_url}/sendVideo",data, files=files)
    return r.json()

## It creates the data.json file to save the data in the incoming mail to the json file
with open('data.json', 'w') as f:
  json.dump(st_list, f, ensure_ascii=False)

## function used to start a live broadcast
def live_Stream(command, chat_id, station_caption):
    process = subprocess.Popen(shlex.split(command),shell=False,stdout=subprocess.PIPE)
    send_message(chat_id, text=f"Live broadcast for \"{station_caption}\" has started.  You can join by clicking the \"KATIL\" button.")

## sends the image when the object is detected and customizes its attributes
def send_message(chat_id, text):
    data={'chat_id': chat_id, 'text': text}
    req = requests.post(f"{api_url}/sendMessage",data=data)
    return req.json()

############################################# TELEGRAM BOT POLLING ############################################# 
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
############################################# BOT GETUPDATE PARSE ##############################################
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
                        device_ip = re.search("([0-9].*(?=_))", str(video_file))
                        if device_ip is not None:
                            send_Video(bot_token, chat_id,video_file)
                        else:
                            pass
        except (KeyError, IndexError, FileNotFoundError):
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
                    send_message(chat_id, text='The live broadcast has been terminated.')
                elif ipaddress.ip_address(dataset):
                    camera_path = f"rtsp://{cam_username}:{cam_password}@{dataset}:{rtsp_url}"
                    command = f"ffmpeg -hide_banner -y -loglevel error -i {camera_path} -vcodec copy -acodec copy -t 120 /server/records/{dataset}_{timestamp}.mkv -c:v libx264 -c:a aac -f flv {stream_url}{stream_key}"
                    if (os.system("kill -9 $(pgrep ffmpeg)")) == 512:
                        live_Stream(command, chat_id, station_caption)
                    else:
                        live_Stream(command, chat_id, station_caption)
                else:
                    pass
                    return dataset
            except IndexError:
                pass
        except KeyError:
            pass

## It adds the ip and device information from the mail to the data.json file.
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

## smtp server username password verification
def authenticator(server, session, envelope, mechanism, auth_data):
    assert isinstance(auth_data, LoginPassword)
    username = auth_data.login
    password = auth_data.password
    if server_auth.get(username) == password:
        return AuthResult(success=True)
    else:
        return AuthResult(success=False, handled=False)

## mail server class
class SMTPHandler:
    ## async mail control
    async def handle_DATA(self, server, session, envelope):
        remote_ip = []
        device_name = ""
        for ip in session.peer:
            remote_ip.append(ip)
        ## get mail content
        msg = message_from_bytes(envelope.content)
        subject = email.header.decode_header(msg['subject'])[0][0]
        sender = msg['from']
        ip_address = remote_ip[0]
        print("\n******************************************************* - MAIL CONTENTS - *******************************************************\n")
        print("Subject    :", subject.upper())
        print("Sender     :", sender)
        if msg.is_multipart():
            ## msg.walk() all data in the mail
            for part in msg.walk():
                content = str(part.get('Content-Disposition'))
                ctype = part.get_content_type()
                if (ctype == 'text/plain' or ctype == 'text/html'):
                    body = part.get_payload(decode=True)
                    ## warning!!! add the appropriate regex code for your system where desired
                    try:
                        device = re.search(device_regex, str(body))
                        print("\nBody       :", body)
                        print("\nDevice Name:", device[0])
                        print("Remote IP  :", ip_address)
                        device_name = device[0]
                        aDict = {
                                    'name':device_name,
                                    'ip':ip_address,
                            }
                        write_json(aDict,device_name)
                    except (IndexError, TypeError):
                        print("Device Name: Device Name is not defined.")
                        device_name = "Device name not found. Checking log MAIL CONTENTS \
                        edit the regex code that finds your Device Name from the body block."
                        if device_name == "Device name not found. Checking log MAIL CONTENTS \
                        edit the regex code that finds your Device Name from the body block.":
                            pass
                if (ctype == 'application/x-msdownload' or ctype == 'application/octet-stream' or ctype == 'image/jpeg' or ctype == 'image/png' or ctype == 'multipart/mixed' or ctype == 'multipart/alternative' or ctype == 'multipart/form-data' ) and 'attachment;' in content:
                    ## save the base64 image received in the mail to the file
                    open('latest.jpg', 'wb').write(part.get_payload(decode=True,))
                    image_data  = open('latest.jpg',"rb").read()
                    response    = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/detection",files={"image":image_data}).json()
                    coordinates = [] 
                    mlistp      = []
                    try:
                        ## object detection
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
                                ## plot detected object with opencv
                                for i in range(len(mlistp)):
                                    imgdr = cv2.rectangle(img, (mlistp[i][0], mlistp[i][1]), \
                                            (mlistp[i][2], mlistp[i][3]),(0,255,0), 2)
                                    imgdr = cv2.putText(imgdr, mlistp[i][4], (mlistp[i][2], mlistp[i][3]+10), \
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.4,(255,255,255), 1)
                                    cv2.imwrite("image.jpg",imgdr)
                        os.remove('latest.jpg')
                        ## After saving the detected object with opencv, checking if it is in the directory and sending it as a message and doing face recognition
                        if os.path.exists('/server/image.jpg'):
                            def send_Photo(file, device_name, ip_address):
                                keyboard=json.dumps({'inline_keyboard':[
                                    [{'text':'Start live video','callback_data':ip_address}],
                                    [{'text':'End live video','callback_data':'stop'}]]})
                                api = f"{api_url}/sendPhoto"
                                with open(file, "rb") as image_file:
                                    form_data = {
                                    'photo': (image_file),
                                    'action': (None, 'send'),
                                    'chat_id': (None, chat_id),
                                    'caption': (None, f"{device_name} {ip_address}"),
                                    'parse_mode': (None, 'Markdown'),
                                    'reply_markup': (None, keyboard )
                                    }
                                    req = requests.post(api, files=form_data)
                                return req.json()
                            send_Photo('image.jpg', device_name, ip_address)
                            os.remove('image.jpg')
                            open('face.jpg', 'wb').write(part.get_payload(decode=True,))
                            image_data = open("face.jpg","rb").read()
                            faces = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/list").json()
                            print("Face list  :",faces)
                            response = requests.post(f"http://{str(deepstack_ip)}:{str(deepstack_port)}/v1/vision/face/recognize",
                                files={"image":image_data},data={"min_confidence":float(confidance)}).json()
                            print("Detect list:",response)
                            for user in response["predictions"]:
                                if user['userid'] in faces['faces']:
                                    text_caption = f"{user['userid']} is at {device_name} station!!!"
                                    file = 'face.jpg'
                                    send_photo(chat_id, file, text_caption)
                                else:
                                    os.remove('face.jpg')                                 
                    except (FileNotFoundError, KeyError):
                        pass
        
        return '250 OK'

## It is a process that runs every 24 hours. Deletes recorded videos
async def run_at_specific_time(hour, minute, func):
    now = datetime.now()
    if now.hour == hour and now.minute == minute:
        await func()

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
        hour, minute = file_remove_time.split(":")
        asyncio.run(run_at_specific_time(int(hour), int(minute), records_file_remove))
        ## Telegram is used to keep the bot alive.
        updates = get_updates(last_update_id)
        if updates is not None:
            if len(updates['result']) > 0:
                last_update_id = get_last_update_id(updates) + 1
                echo_all_updates(updates)
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("The server has been stopped.")
