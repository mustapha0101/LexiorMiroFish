import os
import kuzu
import sys

base_dir = os.path.dirname(os.path.abspath(__file__))
graph_dir = os.path.join(base_dir, 'uploads', 'kuzu', 'test_graph')
os.makedirs(graph_dir, exist_ok=True)

db = kuzu.Database(graph_dir)
conn = kuzu.Connection(db)

try:
    conn.execute("CREATE NODE TABLE Node_Person (uuid STRING, name STRING, PRIMARY KEY (uuid))")
except:
    pass

res = conn.execute("CALL show_tables() RETURN *")
while res.has_next():
    row = res.get_next()
    print("ROW:", row)

try:
    import shutil
    shutil.rmtree(graph_dir)
except:
    pass
