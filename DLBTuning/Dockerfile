FROM python:3.10.15

WORKDIR /DLBApp
COPY ./apstra_client.py .
COPY ./power_pack.py .
COPY ./dlb_tuner.py .
COPY ./requirements.txt .

RUN pip install -r requirements.txt
CMD ["python3", "dlb_tuner.py"]

