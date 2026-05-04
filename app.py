from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "store.json"

app = Flask(__name__)
app.secret_key = "shopsmart-demo-secret"


SEED_ITEMS = [
    {
        "id": "p1",
        "name": "Organic Oats",
        "brand": "Morning Mill",
        "category": "Pantry",
        "price": 249,
        "target": 220,
        "store": "FreshCart",
        "badge": "Best deal",
        "emoji": "🥣",
        "wishlist": True,
        "cart": 1,
    },
    {
        "id": "p2",
        "name": "Cold Brew Pack",
        "brand": "BeanLab",
        "category": "Beverages",
        "price": 399,
        "target": 350,
        "store": "DailyMart",
        "badge": "New",
        "emoji": "☕",
        "wishlist": False,
        "cart": 0,
    },
    {
        "id": "p3",
        "name": "Greek Yogurt",
        "brand": "CreamCo",
        "category": "Dairy",
        "price": 145,
        "target": 130,
        "store": "QuickBasket",
        "badge": "Save 12%",
        "emoji": "🥛",
        "wishlist": True,
        "cart": 2,
    },
    {
        "id": "p4",
        "name": "Avocado Bag",
        "brand": "GreenRoot",
        "category": "Produce",
        "price": 320,
        "target": 280,
        "store": "FreshCart",
        "badge": "Hot",
        "emoji": "🥑",
        "wishlist": False,
        "cart": 0,
    },
    {
        "id": "p5",
        "name": "Protein Granola",
        "brand": "FuelBite",
        "category": "Snacks",
        "price": 510,
        "target": 460,
        "store": "DailyMart",
        "badge": "Tracked",
        "emoji": "🍫",
        "wishlist": False,
        "cart": 1,
    },
    {
        "id": "p6",
        "name": "Kitchen Towels",
        "brand": "HomeNest",
        "category": "Home",
        "price": 189,
        "target": 160,
        "store": "QuickBasket",
        "badge": "Low price",
        "emoji": "🧻",
        "wishlist": True,
        "cart": 0,
    },
]


def default_store() -> dict:
    return {"users": {}, "items": {}}


def load_store() -> dict:
    if not DATA_FILE.exists():
        return default_store()

    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_store(store: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None

    return load_store()["users"].get(user_id)


def user_items(user_id: str) -> list[dict]:
    store = load_store()
    if user_id not in store["items"]:
        store["items"][user_id] = SEED_ITEMS
        save_store(store)

    return store["items"][user_id]


def save_user_items(user_id: str, items: list[dict]) -> None:
    store = load_store()
    store["items"][user_id] = items
    save_store(store)


@app.context_processor
def inject_year() -> dict:
    return {"year": date.today().year}


@app.route("/", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    message = ""
    mode = request.form.get("mode", "login")

    if request.method == "POST":
        store = load_store()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not email or not password:
            message = "Email and password are required."
        elif mode == "register":
            if not name:
                message = "Name is required."
            elif any(user["email"] == email for user in store["users"].values()):
                message = "That account already exists."
            else:
                user_id = uuid.uuid4().hex
                store["users"][user_id] = {
                    "id": user_id,
                    "name": name,
                    "email": email,
                    "password_hash": password_hash(password),
                }
                store["items"][user_id] = SEED_ITEMS
                save_store(store)
                session["user_id"] = user_id
                return redirect(url_for("dashboard"))
        else:
            user = next((candidate for candidate in store["users"].values() if candidate["email"] == email), None)
            if not user or user["password_hash"] != password_hash(password):
                message = "Account not found. Create one first."
            else:
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))

    return render_template("login.html", message=message, mode=mode)


@app.route("/dashboard", methods=["GET"])
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    items = user_items(user["id"])
    query = request.args.get("q", "").strip().lower()
    category = request.args.get("category", "All")

    filtered = [
        item
        for item in items
        if (category == "All" or item["category"] == category)
        and (not query or query in f"{item['name']} {item['brand']} {item['store']} {item['category']}".lower())
    ]
    categories = ["All", *sorted({item["category"] for item in items})]
    cart_total = sum(item["price"] * item["cart"] for item in items)
    target_savings = sum(max(0, item["price"] - item["target"]) for item in items)
    wishlist_count = sum(1 for item in items if item["wishlist"])
    cart_count = sum(item["cart"] for item in items)

    return render_template(
        "dashboard.html",
        user=user,
        items=filtered,
        categories=categories,
        active_category=category,
        query=query,
        cart_total=cart_total,
        target_savings=target_savings,
        wishlist_count=wishlist_count,
        cart_count=cart_count,
    )


@app.route("/item/add", methods=["POST"])
def add_item():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    items = user_items(user["id"])
    items.insert(
        0,
        {
            "id": uuid.uuid4().hex,
            "name": request.form.get("name", "New item").strip(),
            "brand": request.form.get("brand", "Custom").strip(),
            "category": request.form.get("category", "Custom").strip(),
            "price": int(request.form.get("price", 0)),
            "target": int(request.form.get("target", 0)),
            "store": request.form.get("store", "Local Store").strip(),
            "badge": "Custom",
            "emoji": request.form.get("emoji", "🛒").strip() or "🛒",
            "wishlist": False,
            "cart": 0,
        },
    )
    save_user_items(user["id"], items)
    return redirect(url_for("dashboard"))


@app.route("/item/<item_id>/<action>", methods=["POST"])
def item_action(item_id: str, action: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    items = user_items(user["id"])
    for item in items:
        if item["id"] != item_id:
            continue

        if action == "wishlist":
            item["wishlist"] = not item["wishlist"]
        elif action == "plus":
            item["cart"] += 1
        elif action == "minus":
            item["cart"] = max(0, item["cart"] - 1)
        elif action == "delete":
            items = [candidate for candidate in items if candidate["id"] != item_id]
        break

    save_user_items(user["id"], items)
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5180)
