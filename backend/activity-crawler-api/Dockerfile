FROM python:3.11-slim

WORKDIR /app

# 파이썬 출력 버퍼링 비활성화 (Docker 로그 실시간 확인용)
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 데이터 저장 디렉토리 생성
RUN mkdir -p /app/data

CMD ["python", "run.py"]
