import ssl
ssl.SSLContext.minimum_version = ssl.TLSVersion.TLSv1_2
import requests
import json

from ryu.ofproto import ofproto_v1_0

def send_flow_mod(dpid, src_mac = None, dst_mac = None, src_ip = None, dst_ip = None, in_port = None, out_port=ofproto_v1_0.OFPP_FLOOD, priority=1):
    match = { "dl_type": 2048 }
    if in_port is not None:
        match["in_port"] = in_port
    if src_mac is not None:
        match["dl_src"] = src_mac
    if dst_mac is not None:
        match["dl_dst"] = dst_mac
    if src_ip is not None:
        match["nw_src"] = src_ip
    if dst_ip is not None:
        match["nw_dst"] = dst_ip
    flow = {
        "dpid": dpid,
        "idle_timeout": 0,
        "hard_timeout": 0,
        "priority": priority,
        "match": match,
        "actions":[
            {
                "type":"OUTPUT",
                "port": out_port
            }
        ]
    }

    url = 'http://localhost:8080/stats/flowentry/add'
    requests.post(
        url, headers={'Accept': 'application/json', 'Accept': 'application/json'}, data=json.dumps(flow))
