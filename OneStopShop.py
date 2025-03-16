from flask import Flask, request, redirect, render_template, flash, session
from bson import ObjectId
from pymongo import MongoClient
from flask_bcrypt import Bcrypt
import certifi
from dotenv import load_dotenv
import os
load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"
bcrypt = Bcrypt(app)

uri = os.getenv("MONGOURI")
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client["shopmanager"]
customer = db["customers"]
products = db["products"]
buyers = db["buyers"]
cart = db["cart"]

@app.route('/', methods=["GET"])
def frontpage():
    shops=list(customer.find())
    product=list(products.find())
    return render_template('onestopshopindex.html', shops=shops, product=product)

@app.route('/register', methods=["POST"])
def register():
    name_of_shop = request.form.get('name_of_shop')
    name_of_owner = request.form.get('name_of_owner')
    email = request.form.get('email')
    contact = request.form.get('contact')
    password = request.form.get('password')

    if not all([name_of_shop, name_of_owner, email, contact, password]):
        flash("All fields are required!", "danger")
        return redirect('/')

    existing_user = customer.find_one({"email": email})
    if existing_user:
        flash("Account already exists with this email.", "warning")
        return redirect('/')

    password = bcrypt.generate_password_hash(password)
    customer.insert_one({
        "name_of_shop": name_of_shop,
        "name_of_owner": name_of_owner,
        "email": email,
        "contact": contact,
        "password": password
    })
    flash("Sign up successful!", "success")
    return redirect('/')

@app.route('/register_as_customer', methods=["POST"])
def register_as_customer():
    name_of_customer = request.form.get('name_of_customer')
    email_of_customer = request.form.get('email_of_customer')
    contact_of_customer = request.form.get('contact_of_customer')
    password_of_customer = request.form.get('password_of_customer')

    if not all([name_of_customer, email_of_customer, contact_of_customer, password_of_customer]):
        flash("All fields are required!", "danger")
        return redirect('/')

    existing_user = customer.find_one({"email": email_of_customer})
    if existing_user:
        flash("Account already exists with this email.", "warning")
        return redirect('/')

    password_of_customer = bcrypt.generate_password_hash(password_of_customer)
    buyers.insert_one({
        "name_of_customer": name_of_customer,
        "email_of_customer": email_of_customer,
        "contact_of_customer": contact_of_customer,
        "password_of_customer": password_of_customer
    })
    flash("Sign up successful!", "success")
    return redirect('/')



@app.route('/login', methods=["POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = customer.find_one({"email": email})

        if user and bcrypt.check_password_hash(user["password"],password):
            user["_id"]=str(user["_id"])
            user["isowner"]=True
            session["user"]=user
            return redirect('/shop_home/'+user["email"])
        else:
            flash("Wrong username or password", "error")

    return render_template('onestopshopindex.html')

@app.route('/login_as_customer', methods=["POST"])
def login_as_customer():
    if request.method == "POST":
        email_of_customer = request.form["email_of_customer"]
        password_of_customer = request.form["password_of_customer"]

        user = buyers.find_one({"email_of_customer": email_of_customer})
        print(user)
        if user and bcrypt.check_password_hash(user["password_of_customer"],password_of_customer):
            user["_id"]=str(user["_id"])
            user["isowner"]=False
            session["user"]=user
            return redirect('/')
        else:
            flash("Wrong username or password", "error")

    return render_template('onestopshopindex.html')

@app.route('/shop_home/<email>', methods=["GET", "POST"])
def home(email):
    customerid=ObjectId(session["user"]["_id"])
    car=list(cart.find({"customer":customerid}))
    owner=customer.find_one({"email":email})
    all_products = list(products.find({"owner_id":ObjectId(owner["_id"])}))
    customerproducts=[]
    totalprice=0
    for items in car:
        prod=products.find_one({"_id":items["product_id"]})
        prod['quantity']=items['quantity']
        prod['price']=prod['quantity']*prod['product_price']
        totalprice+=prod['price']
        customerproducts.append(prod)
    if "user" in session:
        print(owner["_id"], session["user"]["_id"])
        if ObjectId(owner["_id"])==ObjectId(session["user"]["_id"]):
            canaddproducts=True
        else:
            canaddproducts=False
    else:
        canaddproducts=False
    return render_template('shop_home.html', products=all_products, canaddproducts=canaddproducts, cart=customerproducts, totalprice=totalprice)

@app.route('/add_stock', methods=["POST"])
def add_stock():
    data=dict(request.form)
    product=db.products.find_one({"_id":ObjectId(data["product_id"])})
    owner = session.get("user", None)
    if owner == None:
        flash("Please login to add products", "danger")
        return redirect('/')
    if str(product["owner_id"])==owner["_id"]:
        db.products.update_one({"_id":ObjectId(data["product_id"])}, {"$inc":{"product_quantity":int(data["quantity"])}})

    return redirect('/shop_home/'+owner["email"])

@app.route('/add_product', methods=["POST"])
def add_product():
    product_name = request.form.get('product_name')
    product_price = request.form.get('product_price')
    product_description = request.form.get('product_description')
    product_image = request.form.get('product_image', 'https://via.placeholder.com/150')  # Default image if not provided
    product_quantity = request.form.get('product_quantity')
    owner=session.get("user",None)
    if owner != None:
        owner_id=owner["_id"]
    else:
        flash("Please login to add products", "danger")
        return redirect('/')
    if not all([product_name, product_price, product_description, product_quantity]):
        flash("All fields are required!", "danger")
        return redirect('/shop_home/'+owner["email"])

    products.insert_one({
        "product_name": product_name,
        "product_price": float(product_price),
        "product_description": product_description,
        "product_image": product_image,
        "product_quantity": int(product_quantity),
        "owner_id": ObjectId(owner_id)
    })

    flash("Product added successfully!", "success")
    return redirect('/shop_home/'+owner["email"])

@app.route("/logout", methods=["GET"])
def logout():
    del session["user"]
    return redirect('/')

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    data=dict(request.form)
    cart = db["cart"]
    data["product_id"]=ObjectId(data["product_id"])
    data["customer"]=ObjectId(session["user"]["_id"])
    data["quantity"]=int(data["quantity"])
    finder=cart.find_one({"customer":data["customer"], "product_id":data["product_id"]})
    if finder:
        cart.update_one({"customer":data["customer"], "product_id":data["product_id"]},{"$inc":{"quantity":int(data["quantity"])}})
        products.update_one({"_id": data["product_id"]}, {"$inc": {"product_quantity": -(int(data["quantity"]))}})
    else:
        cart.insert_one(data)
        products.update_one({"_id": data["product_id"]}, {"$inc": {"product_quantity": -(int(data["quantity"]))}})
    product=db.products.find_one({"_id":ObjectId(data["product_id"])})
    owner=db.customers.find_one({"_id":ObjectId(product["owner_id"])})
    return redirect('/shop_home/'+owner["email"])
if __name__ == '__main__':
    app.debug = True
    app.run()
