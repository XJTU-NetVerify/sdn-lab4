#!/usr/bin/env python3
from utils.flowmod import send_flow_mod


send_flow_mod(3, None, None, None, '10.10.0.0/16', None, 4, 10)
send_flow_mod(4, None, None, None, '10.10.0.0/16', None, 3, 10)
send_flow_mod(7, None, None, None, '10.10.0.0/16', None, 2, 10)
send_flow_mod(2, None, None, None, '10.10.0.0/16', None, 2, 10)
send_flow_mod(1, None, None, None, '10.10.0.0/16', None, 3, 10)
send_flow_mod(6, None, None, None, '10.10.0.0/16', None, 3, 10)