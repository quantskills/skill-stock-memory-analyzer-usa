import ast
import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def functions(relative, names, **context):
    source=ast.parse((ROOT/relative).read_text(encoding="utf-8"))
    nodes=[ast.ImportFrom(module="__future__",names=[ast.alias(name="annotations")],level=0)]
    nodes.extend(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in names)
    namespace={"pd":pd,"datetime":datetime,"sys":sys,**context}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),relative,"exec"),namespace)
    return namespace

class MigrationTests(unittest.TestCase):
    def test_insider_request_is_bounded(self):
        sdk=Mock();sdk.get_stock_insider_transaction.return_value=pd.DataFrame([{"symbol":"AAPL"}])
        ns=functions("utils/fetcher.py",{"fetch_insider_trades"},datetime=datetime.datetime,timedelta=datetime.timedelta)
        with patch.dict(sys.modules,{"panda_data":sdk}):
            result=ns["fetch_insider_trades"]("AAPL")
        params=sdk.get_stock_insider_transaction.call_args.kwargs
        start=datetime.datetime.strptime(params["start_date"],"%Y%m%d")
        end=datetime.datetime.strptime(params["end_date"],"%Y%m%d")
        self.assertEqual((end-start).days,365)
        self.assertEqual(len(result["insider_transactions"]),1)

if __name__ == "__main__":
    unittest.main()
