from flask import Flask, render_template, request, redirect, flash, abort

import flask_login

import pymysql
from dynaconf import Dynaconf


app = Flask(__name__)

conf = Dynaconf(
    settings_file = ["settings.toml"]
)

app.secret_key = conf.secret_key

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

    
class User:
    is_authenticated = True
    is_anonymous = False
    is_active = True

    def __init__(self, user_id, email, first_name, last_name):
        self.id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name

    def get_id(self):
        return str(self.id)


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


@login_manager.user_loader
def load_user(user_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM `Customer` WHERE `id` = {user_id};")

    result = cursor.fetchone()

    cursor.close()
    conn.close()

    if result is not None:
        return User(result["id"], result["email"], result["first_name"],result["last_name"])


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

    results = cursor.fetchall()

    cursor.close()
    conn.close()


    return render_template("browse.html.jinja", products = results)


@app.route("/product/<product_id>")
def product(product_id):
    conn = connect_db()

    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM `Products` WHERE `id` = {product_id};")

    result = cursor.fetchone()

    if result is None:
        abort(404)

    cursor.close()
    conn.close()

    return render_template("product.html.jinja", product = result)

@app.route("/product/<product_id>/cart", methods = ["POST"])
@flask_login.login_required
def add_to_cart(product_id):
    quantity = request.form["quantity"]
    customer_id = flask_login.current_user.id

    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute(f""" 
                    INSERT INTO `Cart`
                        (`quantity`,`customer_id`,`product_id`)
                    VALUES
                        ("{quantity}","{customer_id}","{product_id}")
                    ON DUPLICATE KEY UPDATE
                        `quantity` = `quantity` + {quantity};
                 """)
    return redirect("/cart") 



@app.route("/sign_up", methods = ["POST","GET"])
def sign_up():
    if flask_login.current_user.is_authenticated:
        return redirect("/") 
    else:
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

@app.route("/sign_in",methods = ["POST","GET"])
def sign_in():
    if flask_login.current_user.is_authenticated:
        return redirect("/") 
    else:
        if request.method == "POST":
            email = request.form["email"].strip()
            password = request.form["password"]

            conn = connect_db()
            cursor = conn.cursor()


            
            cursor.execute(f"SELECT * FROM `Customer` WHERE `email` = '{email}';")
            result = cursor.fetchone()

            if result is None:
                flash("Your email or password is incorrect")
            elif password != result["password"]:
                flash("Your email or password is incorrect")
            else:
                user = User(result["id"], result["email"], result["first_name"],result["last_name"])
                flask_login.login_user(user)

                return redirect('/')


        return render_template("sign_in.html.jinja")


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return redirect('/')

@app.route('/cart')
@flask_login.login_required
def cart():
    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    cursor.execute(f"""
                    SELECT `name`, `price`, `quantity`, `image`, `color`, `product_id`, `Cart`.`id`
                    FROM `Cart`
                    JOIN `Products` ON `Products`.`id` = `product_id`
                    WHERE `customer_id` = {customer_id}
                    """)

    results = cursor.fetchall()

    total = 0

    for product in results:
        quantity = product["quantity"]
        price = product["price"]
        tot = quantity * price
        total = tot + total


    cursor.close()
    conn.close()
    return render_template("cart.html.jinja", products= results, total = total)


@app.route("/cart/<cart_id>/delete", methods = ["POST"])
def remove_product(cart_id):

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"DELETE FROM `Cart` WHERE `id` {cart_id};") 
    
    cursor.close()
    conn.close()

    return redirect("/cart")
    

@app.route("/cart/<cart_id>/update", methods = ["POST","GET"])
def update_quantity(cart_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(f"""UPDATE `Cart`
                       SET `quantity` = {new_quantity}
    ;""") 

    cursor.close()
    conn.close()

    return redirect("/cart")