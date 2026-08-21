"""Real OPC-UA mDNS + Modbus 502 discovery.

Implements:
 - Zeroconf browse for ``_opcua-tcp._tcp.local`` (asyncua companion)
 - asyncua ``find_servers`` / ``get_endpoints`` validation (opcua-asyncio)
 - asyncio TCP SYN scan (open_connection with timeout) for Modbus 502 and OPC-UA 4840
 - Subnet expansion (ipaddress) with graceful limits

All discovery is bounded by timeouts, handles missing deps gracefully,
never raises — returns [] on failure so callers can return empty discovered
list instead of 500.

Response shape per discovered endpoint:
  {
    "protocol": "opcua" | "modbus",
    "host": "10.10.0.5",
    "port": 502,
    "endpoint": "opc.tcp://10.10.0.5:4840" | "modbus://10.10.0.5:502",
    "endpoint_url": "...",  # alias for endpoint
    "hint": "...",          # legacy hint for onboarding UI
    "discovery_method": "mdns" | "tcp_syn" | "opcua_find_servers",
    "service_name": "...",  # mdns only
  }
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import socket
from typing import Any, Dict, List

log = logging.getLogger("gateway.discovery")

_MDNS_SERVICE = "_opcua-tcp._tcp.local."
_DEFAULT_MDNS_TIMEOUT = 2.5
_DEFAULT_TCP_TIMEOUT = 0.55
_DEFAULT_OPCUA_TIMEOUT = 1.2
_DEFAULT_CONCURRENCY = 64
_DEFAULT_OPCUA_CONCURRENCY = 32
_MAX_HOSTS = 254


def expand_subnet(subnet: str, max_hosts: int = _MAX_HOSTS) -> List[str]:
    """Expand CIDR to host IP strings, capped to *max_hosts*.

    Handles invalid input gracefully -> [].
    For /32 returns single IP. For huge /16 etc caps to max_hosts first entries.
    Supports comma-separated list of subnets (returns union).
    """
    if not subnet or not subnet.strip():
        return []
    parts = [p.strip() for p in subnet.split(",") if p.strip()]
    hosts: List[str] = []
    seen: set[str] = set()
    for part in parts:
        try:
            net = ipaddress.ip_network(part, strict=False)
            # single host /32 or /128
            if net.num_addresses == 1:
                ip_str = str(net.network_address)
                if ip_str not in seen:
                    seen.add(ip_str)
                    hosts.append(ip_str)
                continue
            # enumerate hosts(); for large nets we cap early to avoid O(N) explosion
            # iterate but break early at max_hosts
            count = 0
            for ip in net.hosts():
                ip_str = str(ip)
                if ip_str in seen:
                    continue
                seen.add(ip_str)
                hosts.append(ip_str)
                count += 1
                if len(hosts) >= max_hosts:
                    log.warning("subnet %s truncated to %d hosts (total %d)", part, max_hosts, net.num_addresses)
                    break
                # also guard gigantic iteration: stop after max_hosts per part
                if count >= max_hosts:
                    break
        except ValueError as e:
            log.warning("invalid subnet %r: %s", part, e)
            continue
        except Exception as e:  # pragma: no cover
            log.warning("subnet expand failed %r: %s", part, e)
            continue
    return hosts


async def _probe_tcp(host: str, port: int, timeout: float) -> bool:
    """Single TCP SYN probe via asyncio.open_connection. Returns True if port open."""
    try:
        coro = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(coro, timeout=timeout)
        try:
            writer.close()
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
            except Exception:
                pass
        except Exception:
            pass
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError, asyncio.CancelledError):
        return False
    except Exception:
        return False


async def scan_tcp_hosts(
    hosts: List[str],
    port: int,
    timeout: float = _DEFAULT_TCP_TIMEOUT,
    concurrency: int = _DEFAULT_CONCURRENCY,
    protocol: str = "modbus",
) -> List[Dict[str, Any]]:
    """Concurrent TCP scan for given port. Returns discovered endpoint dicts."""
    if not hosts:
        return []
    sem = asyncio.Semaphore(concurrency)
    discovered: List[Dict[str, Any]] = []

    async def probe(host: str) -> None:
        async with sem:
            ok = await _probe_tcp(host, port, timeout)
            if ok:
                if protocol == "opcua":
                    endpoint = f"opc.tcp://{host}:{port}"
                elif protocol == "modbus":
                    endpoint = f"modbus://{host}:{port}"
                else:
                    endpoint = f"{protocol}://{host}:{port}"
                discovered.append(
                    {
                        "protocol": protocol,
                        "host": host,
                        "port": port,
                        "endpoint": endpoint,
                        "endpoint_url": endpoint,
                        "hint": endpoint,
                        "discovery_method": "tcp_syn",
                    }
                )

    # gather with return_exceptions to avoid one failure killing all
    await asyncio.gather(*(probe(h) for h in hosts), return_exceptions=True)
    return discovered


# ---------------------------------------------------------------------------
# mDNS browse via zeroconf
# ---------------------------------------------------------------------------

async def mdns_discover_opcua(timeout_s: float = _DEFAULT_MDNS_TIMEOUT) -> List[Dict[str, Any]]:
    """Browse _opcua-tcp._tcp.local via zeroconf. Returns OPC-UA endpoints.

    Handles both AsyncZeroconf and sync Zeroconf. Never raises.
    """
    try:
        # Prefer async variant if available (zeroconf >= 0.47)
        try:
            from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf  # type: ignore

            return await _mdns_discover_async(timeout_s, AsyncZeroconf, AsyncServiceBrowser)
        except ImportError:
            pass
        # Fallback to sync Zeroconf
        from zeroconf import ServiceBrowser, Zeroconf  # type: ignore

        return await _mdns_discover_sync(timeout_s, Zeroconf, ServiceBrowser)
    except ImportError:
        log.warning("zeroconf not installed — skipping mDNS browse")
        return []
    except Exception as e:  # pragma: no cover
        log.warning("mdns browse failed: %s", e)
        return []


async def _mdns_discover_async(timeout_s: float, AsyncZeroconf, AsyncServiceBrowser) -> List[Dict[str, Any]]:  # type: ignore
    discovered: List[Dict[str, Any]] = []
    seen: set[str] = set()

    class _Listener:
        def __init__(self, zc):
            self._zc = zc

        def add_service(self, zc, type_, name):  # type: ignore
            try:
                info = zc.get_service_info(type_, name, timeout=2000)
                if info is None:
                    return
                addrs = info.parsed_addresses() if hasattr(info, "parsed_addresses") else []
                # also try parsed_scoped_addresses for IPv6? ignore
                host: str | None = None
                if addrs:
                    host = addrs[0]
                else:
                    # fallback to server name stripped trailing dot
                    try:
                        host = info.server.rstrip(".") if getattr(info, "server", None) else None
                    except Exception:
                        host = None
                if not host:
                    return
                port = int(getattr(info, "port", 0) or 0)
                if not port:
                    port = 4840
                key = f"{host}:{port}"
                if key in seen:
                    return
                seen.add(key)
                endpoint = f"opc.tcp://{host}:{port}"
                discovered.append(
                    {
                        "protocol": "opcua",
                        "host": host,
                        "port": port,
                        "endpoint": endpoint,
                        "endpoint_url": endpoint,
                        "hint": endpoint,
                        "discovery_method": "mdns",
                        "service_name": name,
                        "server": getattr(info, "server", ""),
                        "mdns_type": type_,
                    }
                )
            except Exception:
                pass

        def update_service(self, *args, **kwargs):  # type: ignore
            try:
                self.add_service(*args, **kwargs)
            except Exception:
                pass

        def remove_service(self, *args, **kwargs):  # type: ignore
            pass

    zc = None
    browser = None
    try:
        zc = AsyncZeroconf()
        listener = _Listener(zc.zeroconf)
        browser = AsyncServiceBrowser(zc.zeroconf, _MDNS_SERVICE, listener)
        await asyncio.sleep(timeout_s)
    except Exception as e:
        log.warning("async mdns browse error: %s", e)
    finally:
        try:
            if browser is not None:
                await browser.async_cancel()
        except Exception:
            pass
        try:
            if zc is not None:
                await zc.async_close()
        except Exception:
            pass
    return discovered


async def _mdns_discover_sync(timeout_s: float, Zeroconf, ServiceBrowser) -> List[Dict[str, Any]]:  # type: ignore
    discovered: List[Dict[str, Any]] = []
    seen: set[str] = set()

    class _Listener:
        def __init__(self, zc):
            self._zc = zc

        def add_service(self, zc, type_, name):  # type: ignore
            try:
                info = zc.get_service_info(type_, name, timeout=2000)
                if info is None:
                    return
                addrs = info.parsed_addresses() if hasattr(info, "parsed_addresses") else []
                host: str | None = None
                if addrs:
                    host = addrs[0]
                else:
                    host = info.server.rstrip(".") if getattr(info, "server", None) else None
                if not host:
                    return
                port = int(getattr(info, "port", 0) or 0)
                if not port:
                    port = 4840
                key = f"{host}:{port}"
                if key in seen:
                    return
                seen.add(key)
                endpoint = f"opc.tcp://{host}:{port}"
                discovered.append(
                    {
                        "protocol": "opcua",
                        "host": host,
                        "port": port,
                        "endpoint": endpoint,
                        "endpoint_url": endpoint,
                        "hint": endpoint,
                        "discovery_method": "mdns",
                        "service_name": name,
                        "server": getattr(info, "server", ""),
                        "mdns_type": type_,
                    }
                )
            except Exception:
                pass

        def update_service(self, *args, **kwargs):  # type: ignore
            try:
                self.add_service(*args, **kwargs)
            except Exception:
                pass

        def remove_service(self, *args, **kwargs):  # type: ignore
            pass

    zc = None
    try:
        zc = Zeroconf()
        listener = _Listener(zc)
        browser = ServiceBrowser(zc, _MDNS_SERVICE, listener)
        await asyncio.sleep(timeout_s)
        # browser auto-cancels on zc close
    except Exception as e:
        log.warning("sync mdns browse error: %s", e)
    finally:
        try:
            if zc is not None:
                zc.close()
        except Exception:
            pass
    return discovered


# ---------------------------------------------------------------------------
# OPC-UA find_servers enrichment via asyncua
# ---------------------------------------------------------------------------

async def _opcua_find_servers_single(host: str, port: int = 4840, timeout: float = _DEFAULT_OPCUA_TIMEOUT) -> Dict[str, Any] | None:
    """Try asyncua Client find_servers/get_endpoints for one host. Returns discovered dict or None."""
    try:
        from asyncua import Client  # type: ignore
    except ImportError:
        return None
    endpoint = f"opc.tcp://{host}:{port}"
    client = None
    try:
        client = Client(url=endpoint, timeout=timeout)  # type: ignore
        # connect with timeout
        await asyncio.wait_for(client.connect(), timeout=timeout)  # type: ignore
        # attempt to enumerate servers/endpoints — success proves OPC-UA server
        discovered_via = "opcua_find_servers"
        try:
            # prefer find_servers if available
            if hasattr(client, "find_servers"):
                try:
                    await asyncio.wait_for(client.find_servers(), timeout=1.0)  # type: ignore
                except Exception:
                    # fallback to get_endpoints
                    if hasattr(client, "get_endpoints"):
                        await asyncio.wait_for(client.get_endpoints(), timeout=1.0)  # type: ignore
            elif hasattr(client, "get_endpoints"):
                await asyncio.wait_for(client.get_endpoints(), timeout=1.0)  # type: ignore
        except Exception:
            # enumeration failure still counts as discovery if connect succeeded
            pass
        return {
            "protocol": "opcua",
            "host": host,
            "port": port,
            "endpoint": endpoint,
            "endpoint_url": endpoint,
            "hint": endpoint,
            "discovery_method": discovered_via,
        }
    except (asyncio.TimeoutError, asyncio.CancelledError, ConnectionRefusedError, OSError):
        return None
    except Exception:
        return None
    finally:
        if client is not None:
            try:
                await asyncio.wait_for(client.disconnect(), timeout=0.8)  # type: ignore
            except Exception:
                pass


async def opcua_find_servers_scan(
    hosts: List[str],
    port: int = 4840,
    timeout: float = _DEFAULT_OPCUA_TIMEOUT,
    concurrency: int = _DEFAULT_OPCUA_CONCURRENCY,
) -> List[Dict[str, Any]]:
    """Concurrent asyncua find_servers scan. Only for hosts where import available."""
    if not hosts:
        return []
    try:
        import asyncua  # noqa: F401  # type: ignore
    except ImportError:
        log.warning("asyncua not installed — skipping find_servers scan")
        return []
    sem = asyncio.Semaphore(concurrency)
    discovered: List[Dict[str, Any]] = []

    async def probe(host: str) -> None:
        async with sem:
            res = await _opcua_find_servers_single(host, port, timeout)
            if res is not None:
                discovered.append(res)

    await asyncio.gather(*(probe(h) for h in hosts), return_exceptions=True)
    return discovered


# ---------------------------------------------------------------------------
# Composite discovery
# ---------------------------------------------------------------------------

async def discover_all(
    subnet: str,
    mdns_timeout: float = _DEFAULT_MDNS_TIMEOUT,
    tcp_timeout: float = _DEFAULT_TCP_TIMEOUT,
    opcua_timeout: float = _DEFAULT_OPCUA_TIMEOUT,
    overall_timeout: float = 5.0,
    max_hosts: int = _MAX_HOSTS,
) -> List[Dict[str, Any]]:
    """Run mDNS + TCP SYN (502 + 4840) + asyncua find_servers concurrently.

    Bounded by *overall_timeout* seconds total; never raises.
    Deduplicates by (protocol, host, port).
    """
    hosts = expand_subnet(subnet, max_hosts=max_hosts)
    # if subnet empty or invalid, still try mdns alone
    mdns_coro = mdns_discover_opcua(timeout_s=mdns_timeout)

    if hosts:
        modbus_coro = scan_tcp_hosts(hosts, 502, timeout=tcp_timeout, concurrency=_DEFAULT_CONCURRENCY, protocol="modbus")
        opcua_tcp_coro = scan_tcp_hosts(hosts, 4840, timeout=tcp_timeout, concurrency=_DEFAULT_CONCURRENCY, protocol="opcua")
        # find_servers as enrichment — run only if asyncua available; limit to hosts that responded to tcp for efficiency
        # but we run it independently; deduplication will handle overlap
        # To avoid double scan, we run find_servers only for up to 16 hosts with highest likelihood
        # For now run for all hosts but with lower concurrency
        find_servers_coro = opcua_find_servers_scan(hosts, 4840, timeout=opcua_timeout, concurrency=_DEFAULT_OPCUA_CONCURRENCY)
    else:
        modbus_coro = asyncio.sleep(0, result=[])  # type: ignore
        opcua_tcp_coro = asyncio.sleep(0, result=[])  # type: ignore
        find_servers_coro = asyncio.sleep(0, result=[])  # type: ignore

    try:
        # overall bound
        results = await asyncio.wait_for(
            asyncio.gather(mdns_coro, modbus_coro, opcua_tcp_coro, find_servers_coro, return_exceptions=True),
            timeout=overall_timeout,
        )
    except asyncio.TimeoutError:
        log.warning("discovery overall timeout %.1fs exceeded (subnet=%s)", overall_timeout, subnet)
        # try to collect whatever finished — gather already cancelled; return empty or partial
        return []
    except Exception as e:  # pragma: no cover
        log.warning("discovery gather failed: %s", e)
        return []

    # unpack with exception handling
    mdns_res, modbus_res, opcua_tcp_res, find_servers_res = results  # type: ignore
    if isinstance(mdns_res, Exception):
        log.warning("mdns discover error: %s", mdns_res)
        mdns_res = []
    if isinstance(modbus_res, Exception):
        log.warning("modbus scan error: %s", modbus_res)
        modbus_res = []
    if isinstance(opcua_tcp_res, Exception):
        log.warning("opcua tcp scan error: %s", opcua_tcp_res)
        opcua_tcp_res = []
    if isinstance(find_servers_res, Exception):
        log.warning("find_servers scan error: %s", find_servers_res)
        find_servers_res = []

    # deduplicate: prefer mdns > find_servers > tcp_syn
    seen: set[tuple[str, str, int]] = set()
    merged: List[Dict[str, Any]] = []

    # priority ordering
    for bucket in (mdns_res, find_servers_res, opcua_tcp_res, modbus_res):  # type: ignore
        for entry in bucket:  # type: ignore
            try:
                proto = str(entry.get("protocol", "")).lower()
                host = str(entry.get("host", "")).strip()
                port = int(entry.get("port", 0))
                if not host or not port:
                    continue
                key = (proto, host, port)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(entry)  # type: ignore
            except Exception:
                continue
    return merged
