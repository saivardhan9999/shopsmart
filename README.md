# ShopSmart

ShopSmart is a Python + HTML/CSS product-link price comparison app inspired by dense ecommerce storefront layouts.

## Features

- Flask backend with server-rendered HTML templates
- Demo login and registration
- Per-user JSON data store
- Paste a product URL and scan across major ecommerce stores
- Product title detection from the pasted link when the page is accessible
- Ranked offer cards with lowest price highlighted
- Smart cart for cheapest offers
- External buy/search links for each store
- Comparison history per user
- Ecommerce-style cards, sale badges, quick actions, and animated hero panels

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
