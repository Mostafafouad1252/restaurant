# Car Dealership (Full Stack)

Full-stack project that models a car dealership inventory using:
- **React** (HTML/CSS UI)
- **Node.js (Express)** API
- **Python** tools/CLI

Each car has:
- **price**
- **type** (e.g., Sedan, SUV, Truck)
- **color**

Inventory is stored in a shared local JSON file so it persists between runs:
- `data/inventory.json`

## Requirements
- Python 3.10+
- Node.js 18+

## Run (Python CLI)

```bash
python main.py --help
```

## Common commands

Add a car:

```bash
python main.py add --type SUV --color Black --price 32000
```

List all cars:

```bash
python main.py list
```

Search cars (any combination of filters):

```bash
python main.py search --type Sedan
python main.py search --color Red --max-price 20000
```

Reset inventory (clears all cars):

```bash
python main.py reset
```

## Run (Node.js API)

In one terminal:

```bash
cd server
npm install
npm run dev
```

API runs at `http://localhost:5174`

### Login (demo)
- **username**: `admin`
- **password**: `admin123`

You can change these with environment variables:
- `DEMO_USERNAME`
- `DEMO_PASSWORD`

Useful endpoints:
- `GET /api/cars`
- `POST /api/login` JSON body: `{ "username": "admin", "password": "admin123" }`
- `POST /api/logout` (requires `Authorization: Bearer <token>`)
- `POST /api/cars` (requires auth) JSON body: `{ "type": "SUV", "color": "Black", "price": 32000 }`
- `DELETE /api/cars/:id` (requires auth)
- `GET /api/cars/search?type=SUV&color=Black&minPrice=0&maxPrice=50000`

## Run (React UI: HTML/CSS)

In a second terminal (keep the API running):

```bash
cd client
npm install
npm run dev
```

Open the Vite URL (usually `http://localhost:5173`).

In the UI:
- Use the **Login** card first (default demo credentials are pre-filled).
- After login, you can **Add** and **Delete** cars.

## Run (Python tools)

Validate the JSON schema:

```bash
python python/inventory_tools.py validate
```

Print a summary:

```bash
python python/inventory_tools.py summary
```

