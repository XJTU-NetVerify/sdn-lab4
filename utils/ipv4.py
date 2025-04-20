import re

IPV4_IP_RE = re.compile(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}$")
IPV4_NET_RE = re.compile(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)\.?\b){4}/(3[012]|[12]?[0-9])$")


def format_ip(i: int) -> str:
    if i > 0xffffffff:
        raise Exception("not a valid ip bit")
        
    octs = [i >> 24, i >> 16 & 0xff, i >> 8 & 0xff, i & 0xff]
    return f"{octs[0]}.{octs[1]}.{octs[2]}.{octs[3]}"
    
def get_nth_host(network: str, i: int) -> str:
    if not IPV4_NET_RE.match(network):
        raise Exception("not a network")
    
    [ip, prefixlen] = network.split("/")
    prefixlen = int(prefixlen)
    octs = [int(i) for i in ip.split(".")]
    bit_represent = octs[0] << 24 | octs[1] << 16 | octs[2] << 8 | octs[3]
    
    if (bit_represent << prefixlen) & 0xffffffff != 0:
        print("Warning: device bits not cleared.")
    network = bit_represent & (0xffffffff) << (32 - prefixlen)
    first = network + 1
    broadcast = bit_represent | ((1 << (32 - prefixlen)) - 1)
    
    if i + first >= broadcast:
        raise Exception("exceed network limit")
    
    return format_ip(first + i)

"""
Return whether ip is in the network.
"""
def in_net(network: str, ip: str) -> bool:
    
    if not IPV4_NET_RE.match(network):
        raise Exception("not a network")
    if not IPV4_IP_RE.match(ip):
        raise Exception("not an ip")
    
    
    [net_ip, prefixlen] = network.split("/")
    prefixlen = int(prefixlen)
    net_octs = [int(i) for i in net_ip.split(".")]
    net_bit_represent = net_octs[0] << 24 | net_octs[1] << 16 | net_octs[2] << 8 | net_octs[3]
    
    if (net_bit_represent << prefixlen) & 0xffffffff != 0:
        print("Warning: device bits not cleared.")
    
    network = net_bit_represent & (0xffffffff) << (32 - prefixlen)
    first = network + 1
    broadcast = net_bit_represent | ((1 << (32 - prefixlen)) - 1)
    
    ip_octs = [int(i) for i in ip.split(".")]
    ip_bit_represent = ip_octs[0] << 24 | ip_octs[1] << 16 | ip_octs[2] << 8 | ip_octs[3]
    
    
    if ip_bit_represent == network or ip_bit_represent == broadcast:
        print("Warning: not a device ip")
    return ip_bit_represent >> (32 - prefixlen) == net_bit_represent >> (32 - prefixlen)

"""
Return whether `child` is a subnet of parent.
"""
def is_subnet(parent: str, child: str):
    
    if not IPV4_NET_RE.match(parent):
        raise Exception("parent not a network")
    if not IPV4_NET_RE.match(child):
        raise Exception("child not a network")
    
    
    [parent_ip, parent_prefixlen] = parent.split("/")
    parent_prefixlen = int(parent_prefixlen)
    parent_octs = [int(i) for i in parent_ip.split(".")]
    parent_bit_represent = parent_octs[0] << 24 | parent_octs[1] << 16 | parent_octs[2] << 8 | parent_octs[3]
    
    if (parent_bit_represent << parent_prefixlen) & 0xffffffff != 0:
        print("Warning: device bits not cleared.")
    
    parent = parent_bit_represent & (0xffffffff) << (32 - parent_prefixlen)
    
    [child_ip, child_prefixlen] = child.split("/")
    child_prefixlen = int(child_prefixlen)
    child_octs = [int(i) for i in child_ip.split(".")]
    child_bit_represent = child_octs[0] << 24 | child_octs[1] << 16 | child_octs[2] << 8 | child_octs[3]
    
    if (child_bit_represent << child_bit_represent) & 0xffffffff != 0:
        print("Warning: device bits not cleared.")
        
    return child_bit_represent >> (32 - parent_prefixlen) == parent_bit_represent >> (32 - parent_prefixlen) and child_prefixlen >= parent_prefixlen
    
if __name__ == "__main__":
    assert(get_nth_host("0.0.0.0/24", 253) == "0.0.0.254")
    assert(in_net("0.0.0.0/24", "0.0.0.254"))
    
    assert(is_subnet("0.0.0.0/24", "0.0.0.128/25"))
    assert(not is_subnet("0.0.0.0/24", "0.0.1.0/25"))
