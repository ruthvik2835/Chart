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
KDB_EPOCH = datetime(2000, 1, 1)
def table_to_dict(result):
    def convert_value(v):
        # If pykx object with .py() method, extract Python type
        try:
            py = v.py()
        except Exception:
            py = v
        # If datetime, return ISO format
        if isinstance(py, datetime):
            return py.isoformat()
        # Else return raw value
        return py

    if hasattr(result, '_cols'):
        out = {}
        for col, arr in result._cols.items():
            # arr is iterable of kdb+ values
            out[col] = [convert_value(val) for val in arr]
        return out
    # handle scalar or list
    try:
        return {'values': [convert_value(v) for v in result]}
    except Exception:
        val = result.py() if hasattr(result, 'py') else result
        return {'value': convert_value(val)}
# Helper: convert ISO 'YYYY.MM.DDThh:mm:ss.sss' to q timestamp literal

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
    symbol     = request.query_params.get('symbol')
    start_date = request.query_params.get('start_date')
    end_date   = request.query_params.get('end_date')
    N_str      = request.query_params.get('N')
    missing = [p for p in ('symbol','start_date','end_date','N') if not request.query_params.get(p)]
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
    frame_ms = compute_best_frame_ms(to_q_timestamp(start_date), to_q_timestamp(end_date), N, symbol)
    print(frame_ms)
    tbl = FRAME_TABLE_MAP[frame_ms]

    # Final query
    qcmd = (
        f"0! select from {tbl} "
        f"where symbol=`{symbol}, time within({to_q_timestamp(start_date)};{to_q_timestamp(end_date)})"
    )
    try:
        with kx.QConnection(host='localhost', port=5000) as q:
            res = q(qcmd)
            df = res.pd(raw=True)
            # print(df)
            records=df.to_dict(orient='records')
            for rec in records:
                for col in ('time', 'min_time', 'max_time'):
                    if col in rec and isinstance(rec[col], (int, float)):
                        iso = (KDB_EPOCH + timedelta(days=rec[col])).isoformat()
                        rec[col] = iso

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    duration=time.time()-start_time
    stats={
        'time taken': duration,
        'total length': len(records)
    }

    print(stats)
    return Response({'data': records, 'framems': frame_ms, 'count': len(records)})
