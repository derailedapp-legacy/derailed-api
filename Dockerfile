FROM python:3.10.4-alpine

# cchardet, and multiple other dependencies require GCC to build.
RUN apk add --no-cache build-base libffi-dev

WORKDIR /
COPY requirements.txt requirements.txt

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

ENV STORAGE_URI=redis://redis:6379
ENV MONGO_URI=mongodb://mongo:27017
ENV KAFKA_URI=kafka:9092

COPY . .

EXPOSE 5000

CMD [ "./entrypoint.sh" ]