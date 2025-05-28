# requirements: pip install flask pyodbc

import pyodbc
from flask import Flask, request, jsonify

app = Flask(__name__)

# 1) connect via ODBC
conn = pyodbc.connect(
    'DRIVER={kdb+ ODBC Driver};'
    'SERVER=localhost;PORT=5000;'
    'UID=;PWD=;'
)

@app.route('/trade')
def get_trades():
    symbol = request.args.get('symbol')
    if not symbol:
        return jsonify(error="Missing symbol"), 400

    sql = "SELECT FROM Item_1ms WHERE symbol=`A"
    cur = conn.cursor()
    cur.execute(sql, symbol)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return jsonify(data=rows)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
