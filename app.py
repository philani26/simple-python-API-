from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '12345'
app.config['MYSQL_DB'] = 'flaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()
    result = cur.execute("select * from articles")
    articles = cur.fetchall()
    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No articles found'
        return render_template('articles.html', msg=msg)
    cur.close()


@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()
    cur.execute("select * from articles where id=%s", [id])
    article = cur.fetchone()
    return render_template('article.html', article=article)


class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=2, max=50)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=50)])
    password = PasswordField('Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password)values(%s,%s,%s,%s)",
                    (name, email, username, password))
        mysql.connection.commit()

        cur.close()
        flash('You now registerd you can login')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_c = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute(
            "SELECT * FROM users WHERE username=%s", [username])
        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_c, password):
                session['logged_in'] = True
                session['username'] = username
                flash('You now logged in', 'success')
                return redirect(url_for('dashbord'))

            else:
                error = 'Invalid username or password'
                return render_template('login.html', error=error)
            cur.close()
        else:
            error = 'No user found'
            return render_template('login.html', error=error)

    return render_template('login.html')


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargrs):
        if 'logged_in' in session:
            return f(*args, **kwargrs)
        else:
            flash('Unauthorized Please login', 'danger')
            return redirect(url_for('login'))
    return wrap


@app.route('/dashbord')
@is_logged_in
def dashbord():
    cur = mysql.connection.cursor()
    result = cur.execute("select * from articles")
    articles = cur.fetchall()
    if result > 0:
        return render_template('dashbord.html', articles=articles)
    else:
        msg = 'No Articles found'

    return render_template('dashbord.html', msg=msg)


class ArticlesForm(Form):
    title = StringField('Title', [validators.Length(min=4, max=200)])
    body = TextAreaField('Body', [validators.Length(min=30)])


@app.route('/add_articles', methods=['GET', 'POST'])
def add_articles():
    form = ArticlesForm(request.form)
    if request.method == 'POST' and form.validate:
        title = form.title.data
        body = form.body.data

        cur = mysql.connection.cursor()
        cur.execute("insert into articles(title, body, author) values(%s, %s, %s)",
                    (title, body, session['username']))
        mysql.connection.commit()
        cur.close()
        flash('Article is added')
        return redirect(url_for('dashbord'))
    return render_template('add_articles.html', form=form)


@app.route('/edit_article/<string:id>/', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    cur = mysql.connection.cursor()
    cur.execute('select * from articles where id=%s', [id])
    article = cur.fetchone()
    cur.close()
    form = ArticlesForm(request.form)
    form.title.data = article['title']
    form.body.data = article['body']
    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']
        cur = mysql.connection.cursor()
        cur.execute(
            'update articles set title=%s, body=%s where id=%s', (title, body, id))
        mysql.connection.commit()
        cur.close()
        flash('Article is updated successfully', 'success')
        return redirect(url_for('dashbord'))
    return render_template('edit_article.html', form=form)


@app.route('/delete_article/<string:id>/', methods=['POST'])
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute('delete from articles where id=%s', [id])
    mysql.connection.commit()
    cur.close()
    flash('Article Deleted')
    return redirect(url_for('dashbord'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You are now logout', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.secret_key = 'secret12354'
    app.run(debug=True)
