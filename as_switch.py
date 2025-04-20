from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_0
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet, arp, ipv4
import utils.flowmod
import utils.ipv4
from utils.flowmod import send_flow_mod
from network_awareness import NetworkAwareness
import json
import os
import math



class RoutingSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION]

    _CONTEXTS = {
        'network_awareness': NetworkAwareness
    }

    def __init__(self, *args, **kwargs):
        super(RoutingSwitch, self).__init__(*args, **kwargs)
        self.network_awareness = kwargs['network_awareness']
        self.dpid_mac_port = {}
        with open(os.environ["CONFIG"], "r") as f:
            self.routing_cfg = json.load(f)
        


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        dpid = dp.id
        in_port = msg.in_port

        pkt = packet.Packet(msg.data)
        eth_pkt = pkt.get_protocol(ethernet.ethernet)
        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)

        pkt_type = eth_pkt.ethertype

        # layer 2 self-learning
        dst_mac = eth_pkt.dst
        src_mac = eth_pkt.src

        self.dpid_mac_port.setdefault(dpid, {})
        self.dpid_mac_port[dpid][src_mac] = in_port

        if isinstance(arp_pkt, arp.arp):
            self.handle_arp(msg, in_port, dst_mac, pkt_type)

        if isinstance(ipv4_pkt, ipv4.ipv4):
            self.handle_ipv4(msg, dpid, in_port, src_mac, dst_mac, ipv4_pkt.src, ipv4_pkt.dst, pkt_type)

    def handle_arp(self, msg, in_port, dst_mac, pkt_type):
        dp = msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        dpid = dp.id

        if dst_mac in self.dpid_mac_port[dpid]:
            out_port = self.dpid_mac_port[dpid][dst_mac]
            actions = [parser.OFPActionOutput(out_port)]
            out = parser.OFPPacketOut(
                datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data)
            dp.send_msg(out)
        else:
            # send to the switch port which linked hosts
            for d, ports in self.network_awareness.port_info.items():
                for p in ports:
                    # except the source host
                    if d == dpid and p == in_port:
                        continue
                    dp = self.network_awareness.switch_info[d]
                    actions = [parser.OFPActionOutput(p)]
                    out = parser.OFPPacketOut(
                        datapath=dp, buffer_id=msg.buffer_id, in_port=ofp.OFPP_CONTROLLER, actions=actions, data=msg.data)
                    dp.send_msg(out)

    def handle_ipv4(self, msg, dpid, in_port, src_mac, dst_mac, src_ip, dst_ip, pkt_type):
        print(f"Packet to {dpid}")
        parser = msg.datapath.ofproto_parser

        switch_net = self.routing_cfg["switch_nets"][dpid]
        srcnet = None
        dstnet = None
        
        for net in self.routing_cfg["gateways"]:
            if utils.ipv4.in_net(net, src_ip):
                srcnet = net
                break
    
        if utils.ipv4.in_net(switch_net, dst_ip):
            # Local switching. Install shortest paths.
            dstnet = switch_net
            gateways = None
        else:
            # Routing. Go to the closest gateway
            for dst_candidate in self.routing_cfg["gateways"][switch_net]:
                if utils.ipv4.in_net(dst_candidate, dst_ip):
                    dstnet = dst_candidate
                    gateways = self.routing_cfg["gateways"][switch_net][dstnet]
            
        if not srcnet or not dstnet:
            print("src / dst not recognized, unable to forward.")
            return
        # add_path should be called only from switch to switch / host.
        def add_path(route, dl_src, dl_dst, nw_src, nw_dst, priority=5):
            port_path = []
            for i in range(len(route) - 1):
                out_port = self.network_awareness.link_info[(route[i], route[i + 1])]
                port_path.append((route[i], out_port))
            self.show_path(route[0], route[-1], port_path)
            
            for node in port_path:
                waypoint_dpid, out_port = node
                send_flow_mod(waypoint_dpid, dl_src, dl_dst, nw_src, nw_dst, None, out_port, priority)
            
            # return the output port of current switch.
            return port_path[0][1]
        if gateways is None:
            # Handle packet switching within AS.
            dpid_path = self.network_awareness.shortest_path(dpid, dst_ip)
            if not dpid_path:
                return
            # get port path:  h1 -> in_port, s1, out_port -> h2
            out_port = add_path(dpid_path, None, None, src_ip, dst_ip)
        else:
            # Handle inter-AS packet switching.
            if dpid in gateways:
                # first, if self is a gateway, send to the peer
                peer = self.routing_cfg["peers"][str(dpid)][dstnet]
                route = [dpid, peer]
                # To make matching more efficient, use source net and dst net as matching condition.
                # This might match some IPs which does not exist in the network.
                out_port = add_path(route, None, None, srcnet, dstnet)
                
            else:
                # otherwise, send to the closest gateway
                min_delay = math.inf
                min_gw = None
                for gw in gateways:
                    delay = self.network_awareness.shortest_path_length(dpid, gw)
                    if delay < 0:
                        continue

                    if delay < min_delay:
                        min_delay = delay
                        min_gw = gw
                
                if min_gw is None:
                    #no way to gateway
                    return
                
                dpid_path = self.network_awareness.shortest_path(dpid, min_gw)
                if not dpid_path:
                    return
                
                # To make matching more efficient, use source net and dst net as matching condition.
                # This might match some IPs which does not exist in the network.
                out_port = add_path(dpid_path, None, None, srcnet, dstnet)
        
        # after installing the path, send the packet   
        dp = self.network_awareness.switch_info[dpid]
        actions = [parser.OFPActionOutput(out_port)]
        out = parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=msg.data)
        dp.send_msg(out)
            
    def show_path(self, src, dst, port_path):
        self.logger.info('path: {} -> {}'.format(src, dst))
        path = str(src) + ' -> '
        for node in port_path:
            path += 's{}:{}'.format(*node) + ' -> '
        path += str(dst)
        self.logger.info(path)
        self.logger.info('\n')
