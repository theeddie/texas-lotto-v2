from flask import Flask, render_template, send_from_directory, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import os

app = Flask(__name__, static_folder='.', template_folder='.')

# Database connection settings
DB_CONFIG = {
    'host': 'paperless-ng_db',
    'database': 'texas_lotto',
    'user': 'paperless',
    'password': os.environ.get('DB_PASSWORD', 'paperless')
}

def get_db_connection():
    """Create database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/winners')
def get_winners():
    # Get query parameters
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    search_name = request.args.get('name', '')
    search_city = request.args.get('city', '')
    min_amount = request.args.get('min_amount', '')
    sort_by = request.args.get('sort_by', 'date')  # date, amount, name
    sort_order = request.args.get('sort_order', 'desc')  # asc, desc

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if search_name:
            # Split name into parts and search for all parts
            name_parts = search_name.strip().split()
            if len(name_parts) > 1:
                # Multiple words - search for each part
                name_conditions = []
                for part in name_parts:
                    name_conditions.append("UPPER(player_name_w_id) LIKE UPPER(%s)")
                    params.append(f'%{part}%')
                where_clauses.append("(" + " AND ".join(name_conditions) + ")")
            else:
                # Single word search
                where_clauses.append("UPPER(player_name_w_id) LIKE UPPER(%s)")
                params.append(f'%{search_name}%')
        if search_city:
            where_clauses.append("UPPER(claimant_city) LIKE UPPER(%s)")
            params.append(f'%{search_city}%')
        if min_amount:
            where_clauses.append("won_amount >= %s")
            params.append(float(min_amount))

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM winners {where_sql}"
        cur.execute(count_query, params)
        total_count = cur.fetchone()['count']

        # Determine sort column
        sort_column = 'claim_paid_date'
        if sort_by == 'amount':
            sort_column = 'won_amount'
        elif sort_by == 'name':
            sort_column = 'player_name_w_id'
        elif sort_by == 'date':
            sort_column = 'claim_paid_date'

        # Determine sort direction
        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        # Get paginated results with win count per player
        query = f"""
            SELECT
                w.player_name_w_id,
                w.player_id,
                w.won_amount,
                w.claim_paid_date,
                w.claimant_city,
                w.claimant_state,
                w.claimant_county,
                w.game_category,
                w.location_name,
                w.location_city,
                w.instant_price_point,
                w.anonymity_indicator,
                (SELECT COUNT(*) FROM winners WHERE player_id = w.player_id) as win_count
            FROM winners w
            {where_sql}
            ORDER BY {sort_column} {sort_direction}
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [limit, offset])
        results = cur.fetchall()

        # Format results
        winners = []
        for row in results:
            winner = {
                'name': row['player_name_w_id'] or 'N/A',
                'player_id': row['player_id'] or 'N/A',
                'amount': f"${float(row['won_amount'] or 0):,.2f}",
                'raw_amount': float(row['won_amount'] or 0),
                'date': str(row['claim_paid_date']) if row['claim_paid_date'] else 'N/A',
                'city': row['claimant_city'] or 'N/A',
                'state': row['claimant_state'] or 'N/A',
                'county': row['claimant_county'] or 'N/A',
                'game_category': row['game_category'] or 'N/A',
                'location': row['location_name'] or 'N/A',
                'location_city': row['location_city'] or 'N/A',
                'instant_price_point': row['instant_price_point'] or 'N/A',
                'anonymity': row['anonymity_indicator'] or 'No',
                'win_count': row['win_count']
            }
            winners.append(winner)

        cur.close()
        conn.close()

        return jsonify({'winners': winners, 'count': total_count, 'showing': len(winners)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top10')
def get_top10():
    """Get top 10 winners by amount"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        query = """
            SELECT
                player_name_w_id,
                won_amount,
                claim_paid_date,
                claimant_city,
                claimant_state,
                game_category,
                location_name
            FROM winners
            ORDER BY won_amount DESC
            LIMIT 10
        """
        cur.execute(query)
        results = cur.fetchall()

        winners = []
        for i, row in enumerate(results):
            winner = {
                'rank': i + 1,
                'name': row['player_name_w_id'] or 'N/A',
                'amount': f"${float(row['won_amount'] or 0):,.2f}",
                'raw_amount': float(row['won_amount'] or 0),
                'date': str(row['claim_paid_date']) if row['claim_paid_date'] else 'N/A',
                'city': row['claimant_city'] or 'N/A',
                'state': row['claimant_state'] or 'N/A',
                'game_category': row['game_category'] or 'N/A',
                'location': row['location_name'] or 'N/A'
            }
            winners.append(winner)

        cur.close()
        conn.close()

        return jsonify({'winners': winners})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """Get comprehensive statistics about lottery winners"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get basic statistics
        stats_query = """
            SELECT
                COUNT(*) as total_winners,
                SUM(won_amount) as total_amount,
                AVG(won_amount) as avg_amount,
                MAX(won_amount) as max_win,
                MIN(won_amount) as min_win
            FROM winners
        """
        cur.execute(stats_query)
        stats_row = cur.fetchone()

        # Get game category breakdown
        category_query = """
            SELECT game_category, COUNT(*) as count, SUM(won_amount) as total
            FROM winners
            GROUP BY game_category
            ORDER BY total DESC
        """
        cur.execute(category_query)
        category_results = cur.fetchall()

        game_categories = {}
        for row in category_results:
            game_categories[row['game_category']] = {
                'count': row['count'],
                'total': f"${float(row['total']):,.2f}"
            }

        # Luckiest cities (most winners)
        lucky_cities_query = """
            SELECT claimant_city, claimant_state, COUNT(*) as winner_count, SUM(won_amount) as total_winnings
            FROM winners
            WHERE claimant_city IS NOT NULL
            GROUP BY claimant_city, claimant_state
            ORDER BY winner_count DESC
            LIMIT 10
        """
        cur.execute(lucky_cities_query)
        lucky_cities = []
        for row in cur.fetchall():
            lucky_cities.append({
                'city': f"{row['claimant_city']}, {row['claimant_state']}",
                'winners': row['winner_count'],
                'total': f"${float(row['total_winnings']):,.2f}"
            })

        # Biggest repeat winners
        repeat_winners_query = """
            SELECT
                player_name_w_id,
                player_id,
                COUNT(*) as win_count,
                SUM(won_amount) as total_winnings,
                MAX(won_amount) as biggest_win
            FROM winners
            GROUP BY player_name_w_id, player_id
            HAVING COUNT(*) > 1
            ORDER BY win_count DESC, total_winnings DESC
            LIMIT 10
        """
        cur.execute(repeat_winners_query)
        repeat_winners = []
        for row in cur.fetchall():
            repeat_winners.append({
                'name': row['player_name_w_id'],
                'times_won': row['win_count'],
                'total': f"${float(row['total_winnings']):,.2f}",
                'biggest': f"${float(row['biggest_win']):,.2f}"
            })

        # Winners by month (recent activity)
        monthly_query = """
            SELECT
                TO_CHAR(claim_paid_date, 'YYYY-MM') as month,
                COUNT(*) as winners,
                SUM(won_amount) as total
            FROM winners
            WHERE claim_paid_date >= CURRENT_DATE - INTERVAL '12 months'
            GROUP BY TO_CHAR(claim_paid_date, 'YYYY-MM')
            ORDER BY month DESC
            LIMIT 12
        """
        cur.execute(monthly_query)
        monthly_winners = []
        for row in cur.fetchall():
            monthly_winners.append({
                'month': row['month'],
                'winners': row['winners'],
                'total': f"${float(row['total']):,.2f}"
            })

        # Million dollar club
        million_club_query = """
            SELECT COUNT(*) as count
            FROM winners
            WHERE won_amount >= 1000000
        """
        cur.execute(million_club_query)
        million_club = cur.fetchone()['count']

        # Anonymous winners stats
        anon_query = """
            SELECT
                COUNT(*) as anon_count,
                SUM(won_amount) as anon_total
            FROM winners
            WHERE anonymity_indicator = 'Yes'
        """
        cur.execute(anon_query)
        anon_stats = cur.fetchone()

        stats = {
            'total_winners': stats_row['total_winners'],
            'total_amount': f"${float(stats_row['total_amount'] or 0):,.2f}",
            'average_amount': f"${float(stats_row['avg_amount'] or 0):,.2f}",
            'max_win': f"${float(stats_row['max_win'] or 0):,.2f}",
            'min_win': f"${float(stats_row['min_win'] or 0):,.2f}",
            'million_club': million_club,
            'anonymous_winners': anon_stats['anon_count'],
            'anonymous_total': f"${float(anon_stats['anon_total'] or 0):,.2f}",
            'game_categories': game_categories,
            'lucky_cities': lucky_cities,
            'biggest_repeat_winners': repeat_winners,
            'monthly_activity': monthly_winners
        }

        cur.close()
        conn.close()

        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales')
def get_sales():
    """Get retailer scratch ticket sales data"""
    # Get query parameters
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    search_retailer = request.args.get('retailer', '')
    search_city = request.args.get('city', '')
    fiscal_year = request.args.get('fiscal_year', '')
    sort_by = request.args.get('sort_by', 'sales')  # sales, retailer, date
    sort_order = request.args.get('sort_order', 'desc')

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Build WHERE clause
        where_clauses = []
        params = []

        if search_retailer:
            where_clauses.append("UPPER(location_name) LIKE UPPER(%s)")
            params.append(f'%{search_retailer}%')
        if search_city:
            where_clauses.append("UPPER(location_city) LIKE UPPER(%s)")
            params.append(f'%{search_city}%')
        if fiscal_year:
            where_clauses.append("fiscal_year = %s")
            params.append(fiscal_year)

        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        # Determine sort column
        sort_column = 'net_sales_amount'
        if sort_by == 'retailer':
            sort_column = 'location_name'
        elif sort_by == 'date':
            sort_column = 'month_end_date'

        sort_direction = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM retailer_sales {where_sql}"
        cur.execute(count_query, params)
        total_count = cur.fetchone()['count']

        # Get aggregated sales by retailer
        query = f"""
            SELECT
                retailer_number,
                location_name,
                location_address,
                location_city,
                location_state,
                location_zip,
                location_county_desc,
                COUNT(*) as transaction_count,
                SUM(net_sales_amount) as total_sales,
                AVG(net_sales_amount) as avg_sales,
                MAX(month_end_date) as latest_month
            FROM retailer_sales
            {where_sql}
            GROUP BY retailer_number, location_name, location_address, location_city, location_state, location_zip, location_county_desc
            ORDER BY total_sales {sort_direction}
            LIMIT %s OFFSET %s
        """
        cur.execute(query, params + [limit, offset])
        results = cur.fetchall()

        sales = []
        for row in results:
            sale = {
                'retailer_number': row['retailer_number'] or 'N/A',
                'location': row['location_name'] or 'N/A',
                'address': row['location_address'] or 'N/A',
                'city': row['location_city'] or 'N/A',
                'state': row['location_state'] or 'N/A',
                'zip': row['location_zip'] or 'N/A',
                'county': row['location_county_desc'] or 'N/A',
                'transaction_count': row['transaction_count'],
                'total_sales': f"${float(row['total_sales'] or 0):,.2f}",
                'avg_sales': f"${float(row['avg_sales'] or 0):,.2f}",
                'latest_month': str(row['latest_month']) if row['latest_month'] else 'N/A'
            }
            sales.append(sale)

        cur.close()
        conn.close()

        return jsonify({'sales': sales, 'count': total_count, 'showing': len(sales)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/stats')
def get_sales_stats():
    """Get sales statistics by fiscal year and category"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get total sales by fiscal year
        year_query = """
            SELECT
                fiscal_year,
                SUM(net_sales_amount) as total_sales,
                COUNT(*) as transaction_count,
                COUNT(DISTINCT retailer_number) as retailer_count
            FROM retailer_sales
            GROUP BY fiscal_year
            ORDER BY fiscal_year DESC
        """
        cur.execute(year_query)
        year_results = cur.fetchall()

        years = {}
        for row in year_results:
            years[row['fiscal_year']] = {
                'total_sales': f"${float(row['total_sales']):,.2f}",
                'transaction_count': row['transaction_count'],
                'retailer_count': row['retailer_count']
            }

        # Get overall stats
        stats_query = """
            SELECT
                SUM(net_sales_amount) as total_sales,
                COUNT(DISTINCT retailer_number) as total_retailers,
                COUNT(DISTINCT location_city) as total_cities
            FROM retailer_sales
        """
        cur.execute(stats_query)
        stats = cur.fetchone()

        result = {
            'total_sales': f"${float(stats['total_sales'] or 0):,.2f}",
            'total_retailers': stats['total_retailers'],
            'total_cities': stats['total_cities'],
            'by_fiscal_year': years
        }

        cur.close()
        conn.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/winner_details/<player_id>')
def get_winner_details(player_id):
    """Get all wins for a specific player"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get all wins for this player
        query = """
            SELECT
                player_name_w_id,
                won_amount,
                claim_paid_date,
                claimant_city,
                claimant_state,
                game_category,
                location_name
            FROM winners
            WHERE player_id = %s
            ORDER BY claim_paid_date DESC
        """
        cur.execute(query, [player_id])
        results = cur.fetchall()

        wins = []
        total_winnings = 0
        for row in results:
            win = {
                'name': row['player_name_w_id'] or 'N/A',
                'amount': f"${float(row['won_amount'] or 0):,.2f}",
                'raw_amount': float(row['won_amount'] or 0),
                'date': str(row['claim_paid_date']) if row['claim_paid_date'] else 'N/A',
                'city': row['claimant_city'] or 'N/A',
                'state': row['claimant_state'] or 'N/A',
                'game_category': row['game_category'] or 'N/A',
                'location': row['location_name'] or 'N/A'
            }
            wins.append(win)
            total_winnings += float(row['won_amount'] or 0)

        cur.close()
        conn.close()

        return jsonify({
            'player_id': player_id,
            'wins': wins,
            'total_wins': len(wins),
            'total_winnings': f"${total_winnings:,.2f}"
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5051, debug=True)
