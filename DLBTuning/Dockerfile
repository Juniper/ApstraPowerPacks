FROM python:3.10.15

WORKDIR /DLBApp
COPY apstra/apstra_client.py .
COPY power_pack/power_pack.py .
COPY DLBTuning/dlb_tuner.py .
COPY DLBTuning/requirements.txt .

RUN pip install -r requirements.txt
CMD ["python3", "dlb_tuner.py"]

