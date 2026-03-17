"""
Restaurant Management System - Flask Backend
Customer: menu, cart, reservations, order tracking.
Admin: CRUD meals, order management, analytics.
"""
import os
from datetime import datetime
from functools import wraps

from flask_wtf.csrf import CSRFProtect
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
    session,
    send_from_directory,
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
    UserMixin,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access this page."

# --- Models ---


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default="Customer")  # Admin | Customer

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "Admin"


class Meal(db.Model):
    __tablename__ = "meals"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(40), nullable=False)  # appetizer, main, dessert
    image_url = db.Column(db.String(256), default="/static/images/meals/default.svg")
    order_items = db.relationship("OrderItem", backref="meal", lazy=True)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(40), default="New")  # New, In Preparation, Delivered
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    guest_name = db.Column(db.String(120))
    guest_phone = db.Column(db.String(40))
    user = db.relationship("User", backref="orders")
    items = db.relationship("OrderItem", backref="order", lazy=True, cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)


class CartItem(db.Model):
    __tablename__ = "cart_items"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)


class Reservation(db.Model):
    __tablename__ = "reservations"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.String(10), nullable=False)  # e.g. "18:00"
    num_people = db.Column(db.Integer, nullable=False)
    guest_name = db.Column(db.String(120))
    guest_phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)

    return decorated


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Customer routes ---


@app.route("/")
def index():
    return render_template("customer/index.html")


@app.route("/menu")
def show_menu():
    category = request.args.get("category")
    search = request.args.get("search", "").strip()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    query = Meal.query
    if category and category in Config.MEAL_CATEGORIES:
        query = query.filter(Meal.category == category)
    if search:
        query = query.filter(
            db.or_(
                Meal.name.ilike(f"%{search}%"),
                Meal.description.ilike(f"%{search}%"),
            )
        )
    if min_price is not None:
        query = query.filter(Meal.price >= min_price)
    if max_price is not None:
        query = query.filter(Meal.price <= max_price)

    meals = query.order_by(Meal.category, Meal.name).all()
    return render_template("customer/menu.html", meals=meals)


@app.route("/cart")
def cart_page():
    return render_template("customer/cart.html")


def merge_session_cart_into_user(user):
    cart = session.get("cart", [])
    if not cart:
        return
    existing_items = {
        item.meal_id: item for item in CartItem.query.filter_by(user_id=user.id).all()
    }
    changed = False
    for entry in cart:
        meal_id = entry.get("meal_id")
        qty = entry.get("quantity", 1) or 1
        if not meal_id or qty <= 0:
            continue
        if meal_id in existing_items:
            existing_items[meal_id].quantity = (
                existing_items[meal_id].quantity or 0
            ) + qty
        else:
            db.session.add(
                CartItem(user_id=user.id, meal_id=meal_id, quantity=qty)
            )
        changed = True
    if changed:
        session["cart"] = []
        db.session.commit()


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow}


@app.route("/reservations", methods=["GET", "POST"])
def reservations():
    if request.method == "POST":
        date_str = request.form.get("date")
        time_val = request.form.get("time")
        num_people = request.form.get("num_people", type=int)
        guest_name = request.form.get("guest_name")
        guest_phone = request.form.get("guest_phone")
        if not all([date_str, time_val, num_people, guest_name, guest_phone]):
            flash("Please fill all fields.", "danger")
            return redirect(url_for("reservations"))
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date.", "danger")
            return redirect(url_for("reservations"))
        r = Reservation(
            user_id=current_user.id if current_user.is_authenticated else None,
            date=date_obj,
            time=time_val,
            num_people=num_people,
            guest_name=guest_name,
            guest_phone=guest_phone,
        )
        db.session.add(r)
        db.session.commit()
        flash("Reservation submitted successfully.", "success")
        return redirect(url_for("reservations"))
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return render_template("customer/reservations.html", today=today)


@app.route("/order-tracking")
def order_tracking():
    order_id = request.args.get("order_id")
    order = None
    if order_id:
        order = Order.query.get(order_id)
        if order and current_user.is_authenticated and order.user_id != current_user.id:
            order = None
    return render_template("customer/order_tracking.html", order=order)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if request.method == "POST":
        if current_user.is_authenticated:
            cart_items = [
                {"meal_id": item.meal_id, "quantity": item.quantity}
                for item in CartItem.query.filter_by(user_id=current_user.id).all()
            ]
        else:
            cart_items = session.get("cart", [])
        if not cart_items:
            flash("Your cart is empty.", "warning")
            return redirect(url_for("show_menu"))
        guest_name = request.form.get("guest_name")
        guest_phone = request.form.get("guest_phone")
        if not guest_name or not guest_phone:
            flash("Name and phone are required.", "danger")
            return redirect(url_for("checkout"))
        total = 0.0
        order = Order(
            user_id=current_user.id if current_user.is_authenticated else None,
            total_price=0,
            status="New",
            guest_name=guest_name,
            guest_phone=guest_phone,
        )
        db.session.add(order)
        db.session.flush()
        for item in cart_items:
            meal = Meal.query.get(item["meal_id"])
            if meal:
                qty = item.get("quantity", 1)
                total += meal.price * qty
                db.session.add(OrderItem(order_id=order.id, meal_id=meal.id, quantity=qty))
        order.total_price = round(total, 2)
        if current_user.is_authenticated:
            CartItem.query.filter_by(user_id=current_user.id).delete()
        else:
            session["cart"] = []
        db.session.commit()
        session["order_just_placed"] = order.id
        flash("Order placed successfully.", "success")
        return redirect(url_for("order_tracking", order_id=order.id))
    return render_template("customer/checkout.html")


# --- Cart API (session-based, no login required for adding to cart) ---


@csrf.exempt
@app.route("/api/cart/add", methods=["POST"])
def api_cart_add():
    data = request.get_json() or {}
    meal_id = data.get("meal_id")
    try:
        meal_id = int(meal_id)
    except (TypeError, ValueError):
        meal_id = None
    quantity = data.get("quantity", 1)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1
    if quantity <= 0:
        quantity = 1
    if not meal_id or Meal.query.get(meal_id) is None:
        return jsonify({"success": False, "message": "Invalid meal"}), 400
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, meal_id=meal_id).first()
        if item:
            item.quantity = (item.quantity or 0) + quantity
        else:
            db.session.add(
                CartItem(user_id=current_user.id, meal_id=meal_id, quantity=quantity)
            )
        db.session.commit()
        cart_count = sum(
            i.quantity or 0
            for i in CartItem.query.filter_by(user_id=current_user.id).all()
        )
        return jsonify({"success": True, "cart_count": cart_count})
    cart = session.get("cart", [])
    found = False
    for item in cart:
        if item["meal_id"] == meal_id:
            item["quantity"] = item.get("quantity", 0) + quantity
            found = True
            break
    if not found:
        cart.append({"meal_id": meal_id, "quantity": quantity})
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "cart_count": sum(i.get("quantity", 1) for i in cart)})


@csrf.exempt
@app.route("/api/cart/update", methods=["POST"])
def api_cart_update():
    data = request.get_json() or {}
    meal_id = data.get("meal_id")
    try:
        meal_id = int(meal_id)
    except (TypeError, ValueError):
        meal_id = None
    quantity = data.get("quantity", 0)
    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 0
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, meal_id=meal_id).first()
        if quantity <= 0:
            if item:
                db.session.delete(item)
        else:
            if item:
                item.quantity = quantity
            else:
                db.session.add(
                    CartItem(user_id=current_user.id, meal_id=meal_id, quantity=quantity)
                )
        db.session.commit()
        cart_count = sum(
            i.quantity or 0
            for i in CartItem.query.filter_by(user_id=current_user.id).all()
        )
        return jsonify({"success": True, "cart_count": cart_count})
    cart = session.get("cart", [])
    cart = [i for i in cart if i["meal_id"] != meal_id]
    if quantity > 0:
        cart.append({"meal_id": meal_id, "quantity": quantity})
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "cart_count": sum(i.get("quantity", 1) for i in cart)})


@csrf.exempt
@app.route("/api/cart/remove", methods=["POST"])
def api_cart_remove():
    data = request.get_json() or {}
    meal_id = data.get("meal_id")
    try:
        meal_id = int(meal_id)
    except (TypeError, ValueError):
        meal_id = None
    if current_user.is_authenticated:
        item = CartItem.query.filter_by(user_id=current_user.id, meal_id=meal_id).first()
        if item:
            db.session.delete(item)
            db.session.commit()
        cart_count = sum(
            i.quantity or 0
            for i in CartItem.query.filter_by(user_id=current_user.id).all()
        )
        return jsonify({"success": True, "cart_count": cart_count})
    cart = session.get("cart", [])
    cart = [i for i in cart if i["meal_id"] != meal_id]
    session["cart"] = cart
    session.modified = True
    return jsonify({"success": True, "cart_count": sum(i.get("quantity", 1) for i in cart)})


@csrf.exempt
@app.route("/api/cart")
def api_cart():
    items = []
    total = 0.0
    if current_user.is_authenticated:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        for item in cart_items:
            meal = Meal.query.get(item.meal_id)
            if meal:
                qty = item.quantity or 1
                items.append(
                    {
                        "meal_id": meal.id,
                        "name": meal.name,
                        "price": meal.price,
                        "image_url": meal.image_url,
                        "quantity": qty,
                        "subtotal": round(meal.price * qty, 2),
                    }
                )
                total += meal.price * qty
        count = sum(i.quantity or 1 for i in cart_items)
        return jsonify({"items": items, "total": round(total, 2), "count": count})
    cart = session.get("cart", [])
    for item in cart:
        meal = Meal.query.get(item["meal_id"])
        if meal:
            qty = item.get("quantity", 1)
            items.append(
                {
                    "meal_id": meal.id,
                    "name": meal.name,
                    "price": meal.price,
                    "image_url": meal.image_url,
                    "quantity": qty,
                    "subtotal": round(meal.price * qty, 2),
                }
            )
            total += meal.price * qty
    return jsonify({"items": items, "total": round(total, 2), "count": sum(i.get("quantity", 1) for i in cart)})


# --- Auth ---


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            merge_session_cart_into_user(user)
            next_url = request.args.get("next") or url_for("index")
            return redirect(next_url)
        flash("Invalid email or password.", "danger")
    return render_template("auth/login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        if User.query.filter_by(username=username).first():
            flash("Username already taken.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))
        user = User(username=username, email=email, role="Customer")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        merge_session_cart_into_user(user)
        flash("Registration successful.", "success")
        return redirect(url_for("index"))
    return render_template("auth/register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))


# --- Admin routes ---


@app.route("/admin")
@admin_required
def admin_dashboard():
    return redirect(url_for("admin_orders"))


@app.route("/admin/meals", methods=["GET"])
@admin_required
def admin_meals():
    meals = Meal.query.order_by(Meal.category, Meal.name).all()
    return render_template("admin/meals.html", meals=meals)


@app.route("/admin/meals/create", methods=["GET", "POST"])
@admin_required
def admin_meal_create():
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price", type=float)
        category = request.form.get("category")
        image_url = request.form.get("image_url") or "/static/images/meals/default.svg"
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            upload_folder = app.config.get("UPLOAD_FOLDER")
            if upload_folder:
                os.makedirs(upload_folder, exist_ok=True)
                save_path = os.path.join(upload_folder, filename)
                image_file.save(save_path)
                image_url = "/static/images/meals/" + filename
        if not all([name, price is not None, category]):
            flash("Name, price and category are required.", "danger")
            return redirect(url_for("admin_meal_create"))
        meal = Meal(name=name, description=description, price=price, category=category, image_url=image_url)
        db.session.add(meal)
        db.session.commit()
        flash("Meal created.", "success")
        return redirect(url_for("admin_meals"))
    return render_template("admin/meal_form.html", meal=None)


@app.route("/admin/meals/<int:meal_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_meal_edit(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    if request.method == "POST":
        meal.name = request.form.get("name") or meal.name
        meal.description = request.form.get("description")
        meal.price = request.form.get("price", type=float) or meal.price
        meal.category = request.form.get("category") or meal.category
        new_image_url = request.form.get("image_url")
        image_file = request.files.get("image_file")
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            upload_folder = app.config.get("UPLOAD_FOLDER")
            if upload_folder:
                os.makedirs(upload_folder, exist_ok=True)
                save_path = os.path.join(upload_folder, filename)
                image_file.save(save_path)
                meal.image_url = "/static/images/meals/" + filename
        elif new_image_url:
            meal.image_url = new_image_url
        db.session.commit()
        flash("Meal updated.", "success")
        return redirect(url_for("admin_meals"))
    return render_template("admin/meal_form.html", meal=meal)


@app.route("/admin/meals/<int:meal_id>/delete", methods=["POST"])
@admin_required
def admin_meal_delete(meal_id):
    meal = Meal.query.get_or_404(meal_id)
    db.session.delete(meal)
    db.session.commit()
    flash("Meal deleted.", "success")
    return redirect(url_for("admin_meals"))


@app.route("/admin/orders")
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template("admin/orders.html", orders=orders)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def admin_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    status = request.form.get("status") or request.get_json().get("status") if request.is_json else None
    if status and status in Config.ORDER_STATUSES:
        order.status = status
        db.session.commit()
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": True, "status": order.status})
        flash("Order status updated.", "success")
    return redirect(url_for("admin_orders"))


@app.route("/admin/analytics")
@admin_required
def admin_analytics():
    from sqlalchemy import func

    # Best-selling meals: sum of quantity per meal
    best = (
        db.session.query(Meal.id, Meal.name, func.sum(OrderItem.quantity).label("total_qty"))
        .join(OrderItem, OrderItem.meal_id == Meal.id)
        .group_by(Meal.id, Meal.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
        .all()
    )
    labels = [m.name for m in best]
    data = [m.total_qty or 0 for m in best]
    return render_template("admin/analytics.html", labels=labels, data=data)


# --- API for admin order status (AJAX) ---


@app.route("/api/admin/order/<int:order_id>/status", methods=["POST"])
@admin_required
def api_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json() or {}
    status = data.get("status")
    if status and status in Config.ORDER_STATUSES:
        order.status = status
        db.session.commit()
        return jsonify({"success": True, "status": order.status})
    return jsonify({"success": False}), 400


# --- Init DB and seed ---


def init_db():
    db.create_all()
    if User.query.filter_by(role="Admin").first() is None:
        admin = User(username="admin", email="admin@restaurant.com", role="Admin")
        admin.set_password("admin123")
        db.session.add(admin)
    if Meal.query.count() == 0:
        default_meals = [
            Meal(name="Bruschetta", description="Toasted bread with tomato and basil", price=5.99, category="appetizer", image_url="/static/images/meals/default.svg"),
            Meal(name="Caesar Salad", description="Romaine, parmesan, croutons", price=7.99, category="appetizer", image_url="/static/images/meals/default.svg"),
            Meal(name="Grilled Salmon", description="Fresh salmon with herbs", price=18.99, category="main", image_url="/static/images/meals/default.svg"),
            Meal(name="Beef Burger", description="Angus beef with fries", price=14.99, category="main", image_url="/static/images/meals/default.svg"),
            Meal(name="Tiramisu", description="Classic Italian dessert", price=8.99, category="dessert", image_url="/static/images/meals/default.svg"),
            Meal(name="Chocolate Cake", description="Rich chocolate layer cake", price=6.99, category="dessert", image_url="/static/images/meals/default.svg"),
        ]
        for m in default_meals:
            db.session.add(m)
    db.session.commit()


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Database initialized.")


if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True, port=5000)
