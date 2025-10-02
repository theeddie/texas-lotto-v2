# Texas Lottery Winners Dashboard

A comprehensive web application for viewing and analyzing Texas Lottery winners data and retailer sales information.

## Features

- **Dashboard**: Overview with top 10 winners and key statistics
- **All Winners**: Searchable table with filters for name, city, and amount
- **Statistics**: Detailed analytics including:
  - Total winners and winnings
  - Million dollar club
  - Anonymous winners
  - Luckiest cities
  - Biggest repeat winners
- **Retailer Sales**: Browse scratch ticket sales by retailer with interactive maps

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: PostgreSQL
- **Frontend**: Bootstrap admin template
- **Maps**: MapLibre GL with OpenStreetMap
- **Server**: Gunicorn with 4 workers
- **Deployment**: Docker

## Installation

1. Build and run with Docker Compose:
```bash
docker compose up -d --build
```

2. Access the application at `http://localhost:5051`

## API Endpoints

- `GET /api/winners` - Get lottery winners with search/filter/sort
- `GET /api/top10` - Get top 10 winners by amount
- `GET /api/stats` - Get comprehensive statistics
- `GET /api/sales` - Get retailer sales data
- `GET /api/sales/stats` - Get sales statistics
- `GET /api/winner_details/<player_id>` - Get all wins for a player

## Data Source

Data sourced from [Texas.gov Open Data Portal](https://data.texas.gov):
- Lottery Winners: https://data.texas.gov/resource/54pj-3dxy.json
- Retailer Sales: https://data.texas.gov/resource/beka-uwfq.json

## Configuration

Environment variables:
- `DB_PASSWORD` - Database password (default: paperless)

The application connects to a PostgreSQL database with the following configuration:
- Host: paperless-ng_db
- Database: texas_lotto
- User: paperless

## License

Data provided by Texas Lottery Commission
