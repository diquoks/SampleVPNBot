FROM python

LABEL authors="diquoks"

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["/bin/bash", "-c", "cd code ; python main.py"]