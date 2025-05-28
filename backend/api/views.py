from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import pykx as kx
from datetime import datetime,timedelta
import time

# Mapping of resolution to kdb+ table name
FRAME_TABLE_MAP = {
    1:    'Item_1ms',
    10:   'Item_10ms',
    100:  'Item_100ms',
    1000: 'Item_1s',
    10000:'Item_10s',
    60000:'Item_1min',
}
def list_to_q_symbols(symbol_list):
    """
    Convert a Python list of symbols to q/kdb+ symbol list format.
    
    Args:
        symbol_list (list): List of symbol strings
        
    Returns:
        str: Formatted string in q/kdb+ symbol format (`A`B`C)
    """
    return '`' + '`'.join(symbol_list)

KDB_EPOCH = datetime(2000, 1, 1)
def serialize(q_result):
    col_dict = q_result.py(raw=True)
    col_dict = {
        k.decode() if isinstance(k, bytes) else k:
        v for k, v in col_dict.items()
    }
    rows = []
    for i in range(len(next(iter(col_dict.values())))):
        row = {}
        for col, values in col_dict.items():
            val = values[i]
            col1=col
            if col in ("min_date","max_date","time"):
                val = (KDB_EPOCH + timedelta(days=val)).isoformat()+'Z'
            if col=="max_price":
                col1="max"
            elif col=="min_price":
                col1="min"
            elif col=="min_date":
                col1="min_time"
            elif col=="max_date":
                col1="max_time"
            else:
                col1=col
            if isinstance(val, bytes):
                val = val.decode()
            row[col1] = val
        rows.append(row)
    return rows
def to_q_timestamp(iso_str: str) -> str:
    """
    Convert an ISO8601 UTC string with 'Z' suffix into
    'YYYY.MM.DDThh:mm:ss.SSS' (3-digit ms) format.
    
    Examples:
      '2025-05-18T00:00:00.408Z' -> '2025.05.18T00:00:00.408'
      '2025-05-18T00:00:01.207Z' -> '2025.05.18T00:00:01.207'
    """
    # 1) Strip the Z and parse
    s = iso_str.rstrip('Z')
    # fromisoformat handles the fractional part automatically
    dt = datetime.fromisoformat(s)
    # 2) Format with dots for date, keep microseconds then truncate to ms
    #    '%f' gives 6-digit microseconds; we cut off last 3 digits.
    return dt.strftime('%Y.%m.%dT%H:%M:%S.%f')[:-3]
# Utility: choose finest table that returns <=N rows

def compute_best_frame_ms(start_iso: str, end_iso: str, N: int, symbol: str) -> int:
    print(start_iso,end_iso)
    with kx.QConnection(host='localhost', port=5000) as q:
        for frame_ms in sorted(FRAME_TABLE_MAP):
            tbl = FRAME_TABLE_MAP[frame_ms]
            qcmd = (
                f"count select from {tbl} "
                f"where symbol=`{symbol}, time within({start_iso};{end_iso})"
            )
            cnt = int(q(qcmd))
            print(cnt)
            if cnt <= N:
                return frame_ms
    return max(FRAME_TABLE_MAP)

@api_view(['GET'])
def get_items_equidistant(request):
    # Validate params
    start_time=time.time()
    symbols_str     = request.query_params.get('symbol')
    start_date = request.query_params.get('start_date')
    end_date   = request.query_params.get('end_date')
    N_str      = request.query_params.get('N')
    missing = [p for p in ('symbol','start_date','end_date','N') if not request.query_params.get(p)]
    symbols = [s.strip() for s in symbols_str.split(",") if s.strip()]
    print("symbols: ",symbols)
    if not symbols:
        return Response({"error": "Invalid or empty symbols list"}, status=400)
    if missing:
        return Response({'error': f"Missing parameters: {', '.join(missing)}"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        N = int(N_str)
        if N <= 0:
            raise ValueError
    except ValueError:
        return Response({'error': '"N" must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

    # Convert ISO8601 to q timestamp literal
    print(start_date,end_date)

    if start_date >= end_date:
        return Response({'error': 'start_date must be before end_date.'}, status=status.HTTP_400_BAD_REQUEST)

    # Pick best frame
    frame_ms = compute_best_frame_ms(to_q_timestamp(start_date), to_q_timestamp(end_date), N, symbols[0])
    print(frame_ms)
    tbl = FRAME_TABLE_MAP[frame_ms]



    # Final query
    qcmd = (
        f"0! select from {tbl} "
        f"where symbol in ({list_to_q_symbols(symbols)}), time within({to_q_timestamp(start_date)};{to_q_timestamp(end_date)})"
    )
    try:
        with kx.QConnection(host='localhost', port=5000) as q:
            res = q(qcmd)
            records=serialize(res)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    duration=time.time()-start_time
    stats={
        'time taken': duration,
        'total length': len(records)
    }

    print(stats)
    return Response({'data': records, 'framems': frame_ms, 'count': len(records)})
