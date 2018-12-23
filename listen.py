import gcn
from wisegcn.handler import process_gcn

# Listen for VOEvents until killed with Control-C
gcn.listen(handler=process_gcn)
