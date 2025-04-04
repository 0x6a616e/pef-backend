FROM python:3.13

WORKDIR /app

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./src /app/src

EXPOSE 80

CMD [ "fastapi" , "run", "src/main.py", "--port", "80" ]
