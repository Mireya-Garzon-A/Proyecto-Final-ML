from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user
from forms import SignupForm, PostForm, LoginForm
from models import User

app = Flask(__name__)
app.config['SECRET_KEY'] = '7110c8ae51a4b5af97be6534caef90e4bb9bdcb3380af008f90b23a5d1616bf319bc298105da20fe'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:testing@localhost:5432/Proyecto'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

posts = []

@app.route("/")
def index():
    page = request.args.get('page', 1)
    list = request.args.get('list', 20)
    return render_template("index.html", num_posts=len(posts), posts=posts)

@app.route("/p/<string:slug>/")
def show_post(slug):
    return render_template("post_view.html", slug_title=slug)

@app.route("/admin/post/", methods=['GET', 'POST'], defaults={'post_id': None})
@app.route("/admin/post/<int:post_id>/", methods=['GET', 'POST'])
def post_form(post_id):
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        title_slug = form.title_slug.data
        content = form.content.data
        post = {'title': title, 'title_slug': title_slug, 'content': content}
        posts.append(post)
        return redirect(url_for('index'))
    return render_template("admin/post_form.html", form=form, post_id=post_id)


@app.route("/signup/", methods=["GET", "POST"])
def show_signup_form():
    form = SignupForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        next = request.args.get('next', None)
        if next:
            return redirect(next)
        return redirect(url_for('index'))
    return render_template("signup_form.html", form=form)

@app.route("/login/", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.get_by_email(form.email.data)
        if user is not None and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
    return render_template("login_form.html", form=form)

if __name__ == '__main__':
    app.run(debug=True)