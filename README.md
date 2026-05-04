# ShopSmart

ShopSmart is a Python + HTML/CSS shopping list and price tracker inspired by dense ecommerce storefront layouts, adapted into a grocery and household savings dashboard.

## Features

- Flask backend with server-rendered HTML templates
- Demo login and registration
- Per-user JSON data store
- Search and category filtering
- Wishlist and cart quantity controls
- Add custom tracked products
- Savings, wishlist, cart, and total dashboard stats
- Ecommerce-style product cards, sale badges, quick actions, and animated hero panels

## Tech Stack

- Python
- Flask
- HTML templates
- CSS
- Small vanilla JavaScript enhancement

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open `http://127.0.0.1:5180`.

Authentication is demo-only and uses local JSON storage.
