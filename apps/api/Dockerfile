FROM python:3.12-slim
WORKDIR /app
# 国内 pip 源，避免构建期卡在 pypi.org
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
      "fastapi>=0.115" "uvicorn>=0.30" "psycopg[binary]>=3.2"
COPY app/ /app/
EXPOSE 6700
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6700"]
