FROM python:3.10.4-alpine

# cchardet, and multiple other dependencies require GCC to build.
RUN apk add --no-cache build-base libffi-dev

WORKDIR /

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

COPY . .

EXPOSE 5000

CMD [ "gunicorn", "-w $((`nproc` * 2 + 1))", "-k uvicorn.workers.UvicornWorker", "-b 0.0.0.0:5000", "app:app" ]