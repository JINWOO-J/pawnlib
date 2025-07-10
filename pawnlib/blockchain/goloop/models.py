from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class PeerEndpoint:
    """
    Additional information about a single IP address.
    """
    count: int = 0
    """The number of times this IP address has been encountered."""
    peer_type: str = ""
    """The type of peer, e.g., 'friends', 'children'."""
    rtt: Optional[float] = None
    """Round Trip Time (RTT) to this endpoint."""


@dataclass
class PeerInfo:
    """
    Information corresponding to a single HX address.
    """
    hx: str
    """The HX address of the node."""
    name: str = ""
    """The P-Rep name (or alias), typically fetched from `preps_info[hx]`."""
    ip_addresses: Dict[str, PeerEndpoint] = field(default_factory=dict)
    """A dictionary mapping IP address strings to :class:`PeerEndpoint` objects,
    managing information for multiple IP addresses associated with this HX address.
    """
    ip_count: int = 0
    """The total number of unique IP addresses associated with this HX address."""

    def add_ip(self, ip: str, peer_type: str = "", rtt: Optional[float] = None):
        """
        Adds a new IP address or increments the count if the IP already exists.

        If the IP address is new, it is added to `ip_addresses` with a count of 1,
        and `ip_count` is incremented. If the IP address already exists, its `count`
        is incremented. Optionally updates `peer_type` and `rtt` if provided.

        :param ip: The IP address string to add or update.
        :type ip: str
        :param peer_type: The type of peer for this IP (e.g., 'friends', 'children'). If provided, updates the existing `peer_type`. Defaults to "".
        :type peer_type: str, optional
        :param rtt: The Round Trip Time (RTT) for this IP. If provided, updates the existing `rtt`. Defaults to None.
        :type rtt: Optional[float], optional

        Example:

            .. code-block:: python

                peer = PeerInfo(hx="hx123...", name="my_prep")

                # Add a new IP
                peer.add_ip("192.168.1.1", peer_type="friends", rtt=0.05)
                # peer.ip_addresses will contain "192.168.1.1": PeerEndpoint(count=1, peer_type="friends", rtt=0.05)
                # peer.ip_count will be 1

                # Add the same IP again (increments count)
                peer.add_ip("192.168.1.1")
                # peer.ip_addresses["192.168.1.1"].count will be 2
                # peer.ip_count will still be 1

                # Add another new IP
                peer.add_ip("192.168.1.2", peer_type="children")
                # peer.ip_addresses will also contain "192.168.1.2": PeerEndpoint(count=1, peer_type="children", rtt=None)
                # peer.ip_count will be 2

                # Update existing IP's rtt
                peer.add_ip("192.168.1.1", rtt=0.06)
                # peer.ip_addresses["192.168.1.1"].rtt will be 0.06
        """
        if ip not in self.ip_addresses:
            self.ip_count += 1
            self.ip_addresses[ip] = PeerEndpoint(count=1, peer_type=peer_type, rtt=rtt)
        else:
            self.ip_addresses[ip].count += 1
            if peer_type:
                self.ip_addresses[ip].peer_type = peer_type
            if rtt is not None:
                self.ip_addresses[ip].rtt = rtt
