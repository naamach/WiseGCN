#!/usr/bin/env python
import gcn
from wisegcn.handler import process_gcn

# Listen for GCN notices (until interrupted or killed)
gcn.listen(handler=process_gcn)
