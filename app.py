from __future__ import annotations

import hashlib
import html
import json
import re
import uuid
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus, urlparse
from urllib.request import Request, urlopen

from flask import Flask, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "store.json"

app = Flask(__name__)
app.secret_key = "shopsmart-demo-secret"


ECOMMERCE_STORES = [
    {"name": "Amazon", "domain": "amazon.in", "search": "https://www.amazon.in/s?k={query}", "bias": 1.02},
    {"name": "Flipkart", "domain": "flipkart.com", "search": "https://www.flipkart.com/search?q={query}", "bias": 0.96},
    {"name": "Meesho", "domain": "meesho.com", "search": "https://www.meesho.com/search?q={query}", "bias": 0.91},
    {"name": "Myntra", "domain": "myntra.com", "search": "https://www.myntra.com/{query}", "bias": 1.08},
    {"name": "Croma", "domain": "croma.com", "search": "https://www.croma.com/searchB?q={query}", "bias": 1.04},
    {"name": "Reliance Digital", "domain": "reliancedigital.in", "search": "https://www.reliancedigital.in/search?q={query}", "bias": 0.99},
    {"name": "Tata CLiQ", "domain": "tatacliq.com", "search": "https://www.tatacliq.com/search/?searchCategory=all&text={query}", "bias": 1.01},
    {"name": "JioMart", "domain": "jiomart.com", "search": "https://www.jiomart.com/search/{query}", "bias": 0.94},
    {"name": "BigBasket", "domain": "bigbasket.com", "search": "https://www.bigbasket.com/ps/?q={query}", "bias": 0.98},
]


def default_store() -> dict:
    return {"users": {}, "comparisons": {}, "cart": {}}


def normalize_store(store: dict) -> dict:
    store.setdefault("users", {})
    store.setdefault("comparisons", {})
    store.setdefault("cart", {})
    return store


def load_store() -> dict:
    if not DATA_FILE.exists():
        return default_store()

    return normalize_store(json.loads(DATA_FILE.read_text(encoding="utf-8")))


def save_store(store: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(normalize_store(store), indent=2), encoding="utf-8")


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None

    return load_store()["users"].get(user_id)


def user_comparisons(user_id: str) -> list[dict]:
    store = load_store()
    store["comparisons"].setdefault(user_id, [])
    save_store(store)
    return store["comparisons"][user_id]


def user_cart(user_id: str) -> list[dict]:
    store = load_store()
    store["cart"].setdefault(user_id, [])
    save_store(store)
    return store["cart"][user_id]


def save_user_comparisons(user_id: str, comparisons: list[dict]) -> None:
    store = load_store()
    store["comparisons"][user_id] = comparisons
    save_store(store)


def save_user_cart(user_id: str, cart: list[dict]) -> None:
    store = load_store()
    store["cart"][user_id] = cart
    save_store(store)


def clean_product_name(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s*[-|:]\s*(Amazon|Flipkart|Myntra|Croma|Meesho|JioMart|BigBasket).*$", "", value, flags=re.I)
    return value.strip()[:90] or "Tracked product"


def title_from_url(product_url: str) -> tuple[str, str]:
    parsed = urlparse(product_url)
    host = parsed.netloc.replace("www.", "") or "unknown store"
    fallback = clean_product_name(parsed.path.replace("-", " ").replace("/", " "))

    if parsed.scheme not in {"http", "https"}:
        return fallback, host

    try:
        page_request = Request(product_url, headers={"User-Agent": "Mozilla/5.0 ShopSmart comparison bot"})
        with urlopen(page_request, timeout=5) as response:
            page = response.read(300000).decode("utf-8", errors="ignore")
    except (URLError, TimeoutError, ValueError):
        return fallback, host

    title_match = re.search(r"<title[^>]*>(.*?)</title>", page, re.I | re.S)
    title = clean_product_name(title_match.group(1)) if title_match else fallback
    return title, host


def deterministic_price(product_name: str, store: dict, index: int) -> int:
    seed = int(hashlib.sha256(f"{product_name}-{store['name']}".encode("utf-8")).hexdigest()[:8], 16)
    base = 399 + seed % 3400
    return int((base * store["bias"]) + index * 13)


def compare_product(product_url: str) -> dict:
    product_name, source_host = title_from_url(product_url)
    encoded = quote_plus(product_name)
    offers = []

    for index, store in enumerate(ECOMMERCE_STORES):
        price = deterministic_price(product_name, store, index)
        delivery = "Today" if index % 3 == 0 else "Tomorrow" if index % 3 == 1 else "2 days"
        rating = round(4.1 + (index % 6) * 0.13, 1)
        offers.append(
            {
                "id": uuid.uuid4().hex,
                "store": store["name"],
                "domain": store["domain"],
                "price": price,
                "delivery": delivery,
                "rating": rating,
                "link": store["search"].format(query=encoded),
                "badge": "Source match" if store["domain"] in source_host else "Live search",
            }
        )

    offers.sort(key=lambda offer: offer["price"])
    for rank, offer in enumerate(offers, start=1):
        offer["rank"] = rank
        offer["saving"] = offers[-1]["price"] - offer["price"]
        offer["best"] = rank == 1

    return {
        "id": uuid.uuid4().hex,
        "url": product_url,
        "source": source_host,
        "name": product_name,
        "created": date.today().isoformat(),
        "offers": offers,
    }


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
                store["comparisons"][user_id] = []
                store["cart"][user_id] = []
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

    comparisons = user_comparisons(user["id"])
    cart = user_cart(user["id"])
    active_id = request.args.get("comparison")
    active_comparison = next((comparison for comparison in comparisons if comparison["id"] == active_id), None)
    if not active_comparison and comparisons:
        active_comparison = comparisons[0]

    all_offers = [offer for comparison in comparisons for offer in comparison["offers"]]
    best_price = min((offer["price"] for offer in all_offers), default=0)
    total_savings = sum(comparison["offers"][-1]["price"] - comparison["offers"][0]["price"] for comparison in comparisons)
    cart_total = sum(item["price"] for item in cart)

    return render_template(
        "dashboard.html",
        user=user,
        comparisons=comparisons,
        active_comparison=active_comparison,
        cart=cart,
        cart_total=cart_total,
        best_price=best_price,
        total_savings=total_savings,
        store_count=len(ECOMMERCE_STORES),
    )


@app.route("/compare", methods=["POST"])
def compare():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    product_url = request.form.get("product_url", "").strip()
    if not product_url:
        return redirect(url_for("dashboard"))

    if not product_url.startswith(("http://", "https://")):
        product_url = f"https://{product_url}"

    comparison = compare_product(product_url)
    comparisons = user_comparisons(user["id"])
    comparisons.insert(0, comparison)
    save_user_comparisons(user["id"], comparisons[:12])
    return redirect(url_for("dashboard", comparison=comparison["id"]))


@app.route("/cart/add/<comparison_id>/<offer_id>", methods=["POST"])
def add_to_cart(comparison_id: str, offer_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    comparisons = user_comparisons(user["id"])
    comparison = next((candidate for candidate in comparisons if candidate["id"] == comparison_id), None)
    if not comparison:
        return redirect(url_for("dashboard"))

    offer = next((candidate for candidate in comparison["offers"] if candidate["id"] == offer_id), None)
    if not offer:
        return redirect(url_for("dashboard", comparison=comparison_id))

    cart = user_cart(user["id"])
    cart.append(
        {
            "id": uuid.uuid4().hex,
            "product": comparison["name"],
            "store": offer["store"],
            "price": offer["price"],
            "link": offer["link"],
        }
    )
    save_user_cart(user["id"], cart)
    return redirect(url_for("dashboard", comparison=comparison_id))


@app.route("/cart/remove/<item_id>", methods=["POST"])
def remove_from_cart(item_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    cart = [item for item in user_cart(user["id"]) if item["id"] != item_id]
    save_user_cart(user["id"], cart)
    return redirect(url_for("dashboard"))


@app.route("/comparison/delete/<comparison_id>", methods=["POST"])
def delete_comparison(comparison_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    comparisons = [comparison for comparison in user_comparisons(user["id"]) if comparison["id"] != comparison_id]
    save_user_comparisons(user["id"], comparisons)
    return redirect(url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5180)
