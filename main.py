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

    def __init__(self, user_id, email, first_name, last_name, address):
        self.id = user_id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.address = address

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
        return User(result["id"], result["email"], result["first_name"],result["last_name"],result["address"])


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

    cursor.execute(f"SELECT * FROM `Products` WHERE `id` = '{product_id}';") 

    result = cursor.fetchone()

    if result is None:
        abort(404)


    cursor.execute(f"""SELECT `first_name`,`last_name`,`customer_id`,`written_review`,`rating`,`Review`.`id`
                        FROM `Review`
                        JOIN `Customer` ON `Customer`.`id` = `customer_id`
                        WHERE `product_id` = {product_id};
                    """)

    

    review_result = cursor.fetchall()

    total = 0
    for review in review_result:
        total = total + review['rating']

    if len(review_result) != 0:
        average = total/len(review_result)
    else:
        average = "There are no reviews"


    cursor.close()
    conn.close()

    return render_template("product.html.jinja", product = result, reviews = review_result, average_rating = average)

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
                user = User(result["id"], result["email"], result["first_name"],result["last_name"],result["address"])
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

    cursor.execute(f"DELETE FROM `Cart` WHERE `id` = {cart_id};")

    cursor.close()
    conn.close()

    return redirect("/cart")
    

@app.route("/cart/<cart_id>/update", methods = ["POST"])
def update_quantity(cart_id):

    new_quantity = request.form["new_quantity"]

    conn = connect_db()
    cursor = conn.cursor()
        

    cursor.execute(f"""UPDATE `Cart`
                       SET `quantity` = {new_quantity} WHERE `id` = {cart_id} ;
                    """) 

    cursor.close()
    conn.close()

    return redirect("/cart")


@app.route("/checkout")
def checkout_page():
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
    count = 0

    for product in results:
        quantity = product["quantity"]
        price = product["price"]
        tot = quantity * price
        total = tot + total
        count = count+1
        
    


    cursor.close()
    conn.close()
    return render_template("checkout.html.jinja", products= results, total = total, count= count)




@app.route("/thank_you")
def thank_you():
    return render_template("thankyou.html.jinja")

@app.route("/sale", methods = ["POST","GET"])

def sale():
    if flask_login.current_user.is_authenticated:
        conn = connect_db()
        cursor = conn.cursor()
        
        customer_id = flask_login.current_user.id
        status = "recieved"
        name = request.form["name"]
        card_num = request.form["card_num"]
        expiration = request.form["expire"]
        cvv = request.form["cvv"]

        cursor.execute(f""" 
                        INSERT INTO `Sale`
                        (`customer_id`, `status`,`name_on_card`,`card_number`,`expiration`,`CVV`)
                        VALUES
                        ("{customer_id}","{status}","{name}","{card_num}","{expiration}","{cvv}");
                        """)

        sale_id = cursor.lastrowid

        cursor.execute(f"SELECT * FROM `Cart` WHERE customer_id = '{customer_id}';")
        
        sale_result = cursor.fetchall()
        
        for sale in sale_result:
            product = sale["product_id"]
            qty = sale["quantity"]
            cursor.execute (f"""
                            INSERT INTO `SaleProduct` 
                            (`sale_id`,`product_id`,`quantity`) 
                            VALUES 
                            ("{sale_id}","{product}","{qty}");
                            """)
        
        cursor.execute (f"DELETE FROM `Cart` WHERE `customer_id` = '{customer_id}'")

        return redirect("/thank_you")
    else:
        return redirect("/sign_in")

@app.route("/product/<product_id>/product", methods = ["POST"])
@flask_login.login_required
def add_review(product_id):

    conn = connect_db()
    cursor = conn.cursor()


    customer_id = flask_login.current_user.id
    written_review = request.form["written_review"]
    rating = request.form["rating"]

    cursor.execute(f""" 
                    INSERT INTO `Review`
                        (`written_review`,`rating`,`product_id`,`customer_id`)
                    VALUES
                        ("{written_review}","{rating}","{product_id}","{customer_id}")
                    ON DUPLICATE KEY UPDATE
                        `written_review` = "{written_review}", `rating` = "{rating}";
                 """)
    
    cursor.close()
    conn.close()
                 
    return redirect(f"/product/{product_id}")
    
    
@app.route("/orders")
def orders():

    conn = connect_db()
    cursor = conn.cursor()

    customer_id = flask_login.current_user.id

    cursor.execute(f"SELECT * FROM `Sale` WHERE `customer_id` = {customer_id};")
    
    results = cursor.fetchall()


    cursor.close()
    conn.close()    

    return render_template("orders.html.jinja", results = results)