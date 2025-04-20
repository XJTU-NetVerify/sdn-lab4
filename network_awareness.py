from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_0
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp
from ryu.lib import hub
from ryu.topology import event
from ryu.topology.api import get_host, get_link, get_switch
from ryu.topology.switches import LLDPPacket
import os
import networkx as nx


GET_TOPOLOGY_INTERVAL = 2
SEND_ECHO_REQUEST_INTERVAL = .05
GET_DELAY_INTERVAL = 2


class NetworkAwareness(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]
    

    def __init__(self, *args, **kwargs):
        super(NetworkAwareness, self).__init__(*args, **kwargs)
        self.name = 'network_awareness'
        self.switch_info = {}  # dpid: datapath
        self.link_info = {}  # (s1, s2): s1.port
        self.port_info = {}  # dpid: (ports linked hosts)
        self.topo_map = nx.Graph()
        
        # Immediately get topology by topo file
        with open(os.environ["TOPO"], "r") as f:
            for line in f:
                line = line.strip()
                if line == "" or line.startswith("#"):
                    continue
                if " # delay(ms): " in line:
                    [device_link, device_delay] = line.split(" # delay(ms): ")
                    device_delay = device_delay.split(" ")
                else:
                    device_link = line
                    device_delay = None
                
                device_info = device_link.split(" ")
                [dpid, ip, is_host] = device_info[:3]
                dpid = int(dpid)
                links = device_info[3:]
                is_host = (is_host == "1")
                
                
                if not is_host:
                    self.port_info[dpid] = set()
                for i in range(0, len(links), 2):
                    port_id = int(links[i])
                    peer = links[i + 1]
                    
                    if len(peer.split(".")) == 5:
                        # is a switch. Use dpid as key instead of ip
                        peer = int(peer.split(".")[-1])
                    
                    if device_delay:
                        delay = int(device_delay[i >> 1][:-1])
                        is_external = device_delay[i >> 1][-1] == 'e'
                    else:
                        delay = 0
                        is_external = False
                    
                    if not is_host:
                        # only add host-switch connection to port info
                        if type(peer) != int: # peer is a host
                            self.port_info[dpid].add(port_id)
                        self.link_info[(dpid, peer)] = port_id
                        if not is_external:
                            self.topo_map.add_edge(dpid, peer, hop=1, delay=delay)   
            
            
    def add_flow(self, datapath, priority, match, actions):
        dp = datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        # inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=priority, match=match, actions=actions)
        dp.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER)]
        self.add_flow(dp, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, ev):
        dp = ev.datapath
        dpid = dp.id

        if ev.state == MAIN_DISPATCHER:
            self.switch_info[dpid] = dp

        if ev.state == DEAD_DISPATCHER and dpid in self.switch_info:
            del self.switch_info[dpid]

    def shortest_path(self, src, dst, weight='delay'):
        try:
            paths = list(nx.shortest_simple_paths(self.topo_map, src, dst, weight=weight))
            return paths[0]
        except:
            return None

    def shortest_path_length(self, src, dst, weight='delay'):
        try:
            return nx.shortest_path_length(self.topo_map, src, dst, weight=weight)
        except:
            return -1
    def show_topo_map(self):
        self.logger.info('topo map:')
        self.logger.info('{:^10s}  ->  {:^10s}'.format('node', 'node'))
        for src, dst in self.topo_map.edges:
            self.logger.info('{:^10s}      {:^10s}'.format(str(src), str(dst)))
        self.logger.info('\n')
