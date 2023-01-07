FROM ubuntu:latest

RUN apt-get update && apt install python3 python3-pip libsm6 libxext6 ffmpeg libfontconfig1 libxrender1 libgl1-mesa-glx nmap nano -y

WORKDIR /server/records
WORKDIR /server
ADD main.py .
ADD requirements.txt .
RUN pip install -r /server/requirements.txt

CMD ["python3", "/server/main.py"]