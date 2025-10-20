FROM python:3.11-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードをコピー
COPY . .

# 静的ファイル用のディレクトリを作成
RUN mkdir -p static/img

# ポートを公開
EXPOSE 8080

# アプリケーションを実行
CMD ["gunicorn", "myapp:app", "--bind", "0.0.0.0:8080"]
