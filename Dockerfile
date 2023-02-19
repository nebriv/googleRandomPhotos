FROM python

RUN apt update
RUN apt install -y libopencv-dev python3-opencv
WORKDIR /app

COPY requirements.txt /app
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r requirements.txt

RUN pip3 install gunicorn

COPY app /app
COPY start.sh /app
COPY gunicorn.conf /app
COPY logging.conf /app

ENTRYPOINT ["/app/start.sh"]