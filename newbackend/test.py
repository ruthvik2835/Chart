
import pykx as kx




# ——— 1. OPEN CONNECTION ——————————————————————————————————————————————————————————————
# adjust host/port as needed
q = kx.QConnection(host='localhost', port=5000)
# ——— 2. FRAME ⇄ TABLE MAPPING ————————————————————
conn=q('select from Item_1ms')
conn.pd(raw="True")
print(conn)
