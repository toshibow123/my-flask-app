from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import os

app = Flask(__name__)

# --- ① 秘密鍵は環境変数から（Koyebで設定済みのSECRET_KEYを使う） ---
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

# --- ② DB接続URLは環境変数から（Neonの接続文字列を読む） ---
db_url = os.getenv("DATABASE_URL", "")
# 一部プロバイダは "postgres://" を返すことがあるので互換のため直す
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://")

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///instance/app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# （低リソース環境向けの軽いプール設定：任意）
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "pool_size": 3,
    "max_overflow": 2,
}

# --- ③ 拡張の初期化 ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"   # 未ログインで保護ページに来たら /login へ

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# --- ④ モデル定義 ---
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    tokyo_timezone = pytz.timezone("Asia/Tokyo")
    # default/updated_at は「関数」を渡すのが安全
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(Post.tokyo_timezone))
    updated_at = db.Column(db.DateTime,
                           default=lambda: datetime.now(Post.tokyo_timezone),
                           onupdate=lambda: datetime.now(Post.tokyo_timezone))
    img_name = db.Column(db.String(100), nullable=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

# 現在のユーザー読込
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ⑤ ルーティング ---
# ルート（/）が無かったので追加
@app.route("/")
def home():
    return redirect("/index")

@app.route("/admin")
@login_required
def admin():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin.html", posts=posts)

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title")
        body = request.form.get("body")
        file = request.files.get("img")

        filename = None
        if file and file.filename:
            ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
            ext = file.filename.rsplit(".", 1)[-1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                return "画像ファイルのみアップロードできます(png/jpg/jpeg/gif)", 400
            filename = file.filename
            # /static/img へ保存（存在しない場合は作成）
            img_dir = os.path.join(app.static_folder, "img")
            os.makedirs(img_dir, exist_ok=True)
            save_path = os.path.join(img_dir, filename)
            file.save(save_path)

        post = Post(title=title, body=body, img_name=filename)
        db.session.add(post)
        db.session.commit()
        return redirect("/admin")

    return render_template("create.html", method="GET")

@app.route("/<int:post_id>/update", methods=["GET", "POST"])
@login_required
def update(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == "POST":
        post.title = request.form.get("title")
        post.body = request.form.get("body")
        db.session.commit()
        return redirect("/admin")
    return render_template("update.html", post=post)

@app.route("/<int:post_id>/delete")
@login_required
def delete(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/admin")

@app.route("/index")
def index():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("index.html", posts=posts)

@app.route("/<int:post_id>/read")
def read(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template("read.html", post=post)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect("/admin")
        return redirect("/login")  # 簡易リダイレクト（必要ならフラッシュメッセージに）
    return render_template("login.html", msg="")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/login")
