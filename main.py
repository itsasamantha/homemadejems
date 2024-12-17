from flask import Flask, render_template, request, redirect, flash
import pymysql
from dynaconf import Dynaconf


app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

    
def connect_db():
    conn = pymysql.connect(
        host = "10.100.34.80",
        database = "spowell_home_made",
        user = "spowell",
        password = conf.password,
        autocommit = True,
        cursorclass = pymysql.cursors.DictCursor
    )

    return conn

@app.route("/")
def index():
    return render_template("homepage.html.jinja")

@app.route("/browse")
def product_browse():
    query = request.args.get("query")
    conn = connect_db()

    cursor = conn.cursor()

    if query == None:
        cursor.execute("SELECT * FROM `Products`;")
    else:
        cursor.execute(f"SELECT * FROM `Products` WHERE `name` LIKE '%{query}%' OR `description` ;")
        return render_template("browse.html.jinja", products = results)

    results = cursor.fetchall()

    cursor.close()
    conn.close()


    return render_template("browse.html.jinja", products = results)


@app.route("/product")
def product():
    return render_template("product.html.jinja")

@app.route("/sign_in")
def sign_in():
    return render_template("sign_in.html.jinja")

@app.route("/sign_up", methods = ["POST","GET"])
def sign_up():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        address = request.form["address"]

        if password != confirm_password:
            flash("Your passwords do not match.")
            return render_template("sign_up.html.jinja")
        else:
            if len(password) < 10:
                flash("Your password should be at least 10 characters.")
            else:
                conn = connect_db()

                cursor = conn.cursor()
                try:
                    cursor.execute(f""" 
                    INSERT INTO `Customer` 
                        (`first_name`, `last_name`,`email`,`password`, `address`)
                        VALUES
                            ('{first_name}', '{last_name}', '{email}', '{password}', '{address}');

                    """)
                except pymysql.err.IntegrityError:
                    flash("There is already an account with this email.")
                else:
                    return redirect("/sign_in")
                finally:
                    cursor.close()
                    conn.close()
            

    return render_template("sign_up.html.jinja")