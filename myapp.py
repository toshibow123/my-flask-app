from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import pytz
from datetime import datetime
import os

app = Flask(__name__)

# 環境変数から設定を取得（本番環境用）
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY', os.urandom(24))

#ログイン管理システムのようなもの
login_manager = LoginManager()
login_manager.init_app(app)

db = SQLAlchemy()

# データベース接続設定（環境変数から取得）
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    # Neonやその他のクラウドデータベース用
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    # ローカル開発用（フォールバック）
    DB_INFO = {
        'user':'postgres',
        'password':'toshifumi4989',
        'host':'localhost',
        'name':'postgres'
    }
    SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://{user}:{password}@{host}/{name}'.format(**DB_INFO)
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
db.init_app(app)

migrate = Migrate(app,db)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.String(1000), nullable=False)
    tokyo_timezone = pytz.timezone('Asia/Tokyo')
    created_at = db.Column(db.DateTime, nullable=False,default=datetime.now(tokyo_timezone))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now(tokyo_timezone))
    
    img_name = db.Column(db.String(100),nullable=True)

class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

#現在のユーザーを識別するための関数
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/admin")
@login_required
def admin():
    posts = Post.query.order_by(Post.created_at.desc()).all()
    return render_template("admin.html", posts=posts)

@app.route("/create", methods=['GET','POST'])
@login_required
def create():
    if request.method == 'POST':
        #2.リクエストできた情報の取得
        title = request.form.get('title')
        body = request.form.get('body')
        #1. 画像情報の取得
        file = request.files['img']
        #2. 画像ファイル名の取得
        filename = file.filename

        # 画像ファイルのみを許可する
        ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
        ext = filename.rsplit('.', 1)[-1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            #拡張子が画像以外ならエラー画面やメッセージを返す
            return "画像ファイルのみアップロードできます(png/jpg/jpeg/gif)",400

        #3. データベースのファイル名を保存
        post = Post(title=title, body=body, img_name=filename)
        #4. 画像を保存する
        save_path = os.path.join(app.static_folder, 'img', filename)
        file.save(save_path)
        db.session.add(post)
        db.session.commit()
        return redirect("/admin")
    elif request.method == 'GET':
        return render_template('create.html', method='GET')
    
@app.route("/<int:post_id>/update", methods=['GET','POST'])
@login_required
def update(post_id):
    post = Post.query.get(post_id)
    if request.method == 'POST':
        #2.リクエストできた情報の取得
        post.title = request.form.get('title')
        post.body = request.form.get('body')
        db.session.commit()
        return redirect("/admin")
    elif request.method == 'GET':
        return render_template('update.html', post=post)
    
@app.route("/<int:post_id>/delete")
@login_required
def delete(post_id):
    post = Post.query.get(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect("/admin")

@app.route("/")
def home():
    return redirect("/index")

@app.route("/index")
def index():
    posts = Post.query.all()
    return render_template("index.html", posts=posts)

@app.route("/<int:post_id>/read")
def read(post_id):
    post = Post.query.get(post_id)
    return render_template("read.html", post=post)

@app.route("/signup", methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        #2.リクエストできた情報の取得
        username = request.form.get('username')
        password = request.form.get('password')
        hashed_pass = generate_password_hash(password)
        user = User(username=username, password=hashed_pass)
       
        db.session.add(user)
        db.session.commit()
        return redirect("/login")
    elif request.method == 'GET':
        return render_template('signup.html')
    
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # ユーザー名とパスワードの受け取り
        username = request.form.get('username')
        password = request.form.get('password')
        # ユーザー名をもとにデータベースから情報を取得
        user = User.query.filter_by(username=username).first()
        # 入力パスワードとデータベースのパスワードが一致しているか確認
        if check_password_hash(user.password, password=password):
            #一致していればログイン⇒管理画面へリダイレクト
            login_user(user)
            return redirect('/admin')
        else:
            # 間違っている場合、エラー文と共にログイン画面へリダイレクトさせる
            return redirect('/login', msg="ユーザ名/パスワードが違います")
    elif request.method == 'GET':
        return render_template('login.html', msg='')
    
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect('login')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)    