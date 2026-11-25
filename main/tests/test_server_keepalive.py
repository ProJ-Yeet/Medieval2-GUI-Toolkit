"""The server keeps a connection open for the next request (HTTP/1.1).

Answering each request on a fresh connection and closing it left one TCP
port pair in TIME_WAIT per request, about two minutes each. A gallery of
icons, a page of scripts and fast switching between models make thousands,
the 16,384 ports Windows hands out ran short or wrapped onto a pair still
held, and Windows refused the browser's next connect with WSAEACCES (10013):
"net::ERR_NETWORK_ACCESS_DENIED", "Failed to fetch", now and then the page
not opening at all. Measured 2026-11-25: 731 of 3,000 quick connections
refused. Kept open, a browser asks hundreds of things over a handful.

    python -m tests.test_server_keepalive
"""
import http.client
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tests import _tmp  # noqa: E402
from unittransfer.server import Handler, Registry, _Server  # noqa: E402

ok = []


def check(label, cond):
    ok.append(bool(cond))
    print(f"  [{'OK ' if cond else 'FAIL'}] {label}")


print("\n-- one connection, many requests --")
tmp = Path(_tmp.mkdtemp(prefix="ut_keepalive_"))
Handler.registry = Registry(tmp / "icons")
accepted = []


class Counting(_Server):
    def get_request(self):
        got = super().get_request()
        accepted.append(got[1])
        return got


httpd = Counting(("127.0.0.1", 0), Handler)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
c = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=20)

c.request("GET", "/api/ping")
r = c.getresponse(); body = r.read()
check(f"answered as HTTP/1.1 ({r.version}), connection kept ({r.getheader('Connection')})",
      r.version == 11 and (r.getheader("Connection") or "").lower() != "close" and r.status == 200)

c.request("POST", "/api/heartbeat", body=json.dumps({"x": 1}), headers={"Content-Type": "application/json"})
r = c.getresponse(); r.read()
check(f"a POST on the same connection ({r.status})", r.status == 200)

c.request("POST", "/api/bye", body="x" * 5000, headers={"Content-Type": "text/plain"})
r = c.getresponse(); r.read()
c.request("GET", "/api/ping")
r = c.getresponse(); r.read()
check(f"a body the handler ignores is drained, the next request still reads ({r.status})", r.status == 200)

fails = 0
for i in range(300):
    c.request("GET", "/api/ping")
    r = c.getresponse(); r.read()
    fails += r.status != 200
check(f"300 more requests, all answered ({300 - fails})", fails == 0)
check(f"all of it over one connection (server accepted {len(accepted)})", len(accepted) == 1)

c.close()
httpd.shutdown()
print()
print(f"{sum(ok)}/{len(ok)} checks - " + ("ALL PASSED" if all(ok) else f"{len(ok) - sum(ok)} FAILED"))
sys.exit(0 if all(ok) else 1)
