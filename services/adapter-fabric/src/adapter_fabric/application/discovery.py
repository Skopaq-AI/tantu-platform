"""Real OPC-UA mDNS + Modbus 502 discovery — adapter-fabric side.

Mirrors gateway discovery but uses adapter-fabric infra conventions
(structlog logger). Provides same helpers: expand_subnet, mdns browse
for _opcua-tcp._tcp.local via zeroconf, asyncua find_servers, and
asyncio TCP SYN scan for 502/4840.

Used by GET /discover and GET /onboard/discover in api/main.py.
"""

from __future__ import annotations

import asyncio
import ipaddress
from typing import Any, Dict, List

from ..infra.logging import get_logger

log = get_logger("adapter_fabric.discovery")

_MDNS_SERVICE = "_opcua-tcp._tcp.local."
_DEFAULT_MDNS_TIMEOUT = 2.5
_DEFAULT_TCP_TIMEOUT = 0.55
_DEFAULT_OPCUA_TIMEOUT = 1.2
_DEFAULT_CONCURRENCY = 64
_DEFAULT_OPCUA_CONCURRENCY = 32
_MAX_HOSTS = 254


def expand_subnet(subnet: str, max_hosts: int = _MAX_HOSTS) -> List[str]:
    if not subnet or not subnet.strip():
        return []
    parts = [p.strip() for p in subnet.split(",") if p.strip()]
    hosts: List[str] = []
    seen: set[str] = set()
    for part in parts:
        try:
            net = ipaddress.ip_network(part, strict=False)
            if net.num_addresses == 1:
                ip_str = str(net.network_address)
                if ip_str not in seen:
                    seen.add(ip_str)
                    hosts.append(ip_str)
                continue
            count = 0
            for ip in net.hosts():
                ip_str = str(ip)
                if ip_str in seen:
                    continue
                seen.add(ip_str)
                hosts.append(ip_str)
                count += 1
                if len(hosts) >= max_hosts:
                    log.warning("subnet truncated", subnet=part, max_hosts=max_hosts, total=int(net.num_addresses))
                    break
                if count >= max_hosts:
                    break
        except ValueError as e:
            log.warning("invalid subnet", subnet=part, error=str(e))
            continue
        except Exception as e:  # pragma: no cover
            log.warning("subnet expand failed", subnet=part, error=str(e))
            continue
    return hosts


async def _probe_tcp(host: str, port: int, timeout: float) -> bool:
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

    await asyncio.gather(*(probe(h) for h in hosts), return_exceptions=True)
    return discovered


async def mdns_discover_opcua(timeout_s: float = _DEFAULT_MDNS_TIMEOUT) -> List[Dict[str, Any]]:
    try:
        try:
            from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf  # type: ignore

            return await _mdns_discover_async(timeout_s, AsyncZeroconf, AsyncServiceBrowser)
        except ImportError:
            pass
        from zeroconf import ServiceBrowser, Zeroconf  # type: ignore

        return await _mdns_discover_sync(timeout_s, Zeroconf, ServiceBrowser)
    except ImportError:
        log.warning("zeroconf not installed — skipping mDNS")
        return []
    except Exception as e:  # pragma: no cover
        log.warning("mdns browse failed", error=str(e))
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
                host: str | None = None
                if addrs:
                    host = addrs[0]
                else:
                    host = info.server.rstrip(".") if getattr(info, "server", None) else None
                if not host:
                    return
                port = int(getattr(info, "port", 0) or 0) or 4840
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
        log.warning("async mdns error", error=str(e))
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
                port = int(getattr(info, "port", 0) or 0) or 4840
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
        ServiceBrowser(zc, _MDNS_SERVICE, listener)  # noqa: F841
        await asyncio.sleep(timeout_s)
    except Exception as e:
        log.warning("sync mdns error", error=str(e))
    finally:
        try:
            if zc is not None:
                zc.close()
        except Exception:
            pass
    return discovered


async def _opcua_find_servers_single(host: str, port: int = 4840, timeout: float = _DEFAULT_OPCUA_TIMEOUT) -> Dict[str, Any] | None:
    try:
        from asyncua import Client  # type: ignore
    except ImportError:
        return None
    endpoint = f"opc.tcp://{host}:{port}"
    client = None
    try:
        client = Client(url=endpoint, timeout=timeout)  # type: ignore
        await asyncio.wait_for(client.connect(), timeout=timeout)  # type: ignore
        try:
            if hasattr(client, "find_servers"):
                try:
                    await asyncio.wait_for(client.find_servers(), timeout=1.0)  # type: ignore
                except Exception:
                    if hasattr(client, "get_endpoints"):
                        await asyncio.wait_for(client.get_endpoints(), timeout=1.0)  # type: ignore
            elif hasattr(client, "get_endpoints"):
                await asyncio.wait_for(client.get_endpoints(), timeout=1.0)  # type: ignore
        except Exception:
            pass
        return {
            "protocol": "opcua",
            "host": host,
            "port": port,
            "endpoint": endpoint,
            "endpoint_url": endpoint,
            "hint": endpoint,
            "discovery_method": "opcua_find_servers",
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
    if not hosts:
        return []
    try:
        import asyncua  # noqa: F401  # type: ignore
    except ImportError:
        log.warning("asyncua not installed — skipping find_servers")
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


async def discover_all(
    subnet: str,
    mdns_timeout: float = _DEFAULT_MDNS_TIMEOUT,
    tcp_timeout: float = _DEFAULT_TCP_TIMEOUT,
    opcua_timeout: float = _DEFAULT_OPCUA_TIMEOUT,
    overall_timeout: float = 5.0,
    max_hosts: int = _MAX_HOSTS,
) -> List[Dict[str, Any]]:
    hosts = expand_subnet(subnet, max_hosts=max_hosts)
    mdns_coro = mdns_discover_opcua(timeout_s=mdns_timeout)
    if hosts:
        modbus_coro = scan_tcp_hosts(hosts, 502, timeout=tcp_timeout, concurrency=_DEFAULT_CONCURRENCY, protocol="modbus")
        opcua_tcp_coro = scan_tcp_hosts(hosts, 4840, timeout=tcp_timeout, concurrency=_DEFAULT_CONCURRENCY, protocol="opcua")
        find_servers_coro = opcua_find_servers_scan(hosts, 4840, timeout=opcua_timeout, concurrency=_DEFAULT_OPCUA_CONCURRENCY)
    else:
        modbus_coro = asyncio.sleep(0, result=[])  # type: ignore
        opcua_tcp_coro = asyncio.sleep(0, result=[])  # type: ignore
        find_servers_coro = asyncio.sleep(0, result=[])  # type: ignore

    try:
        results = await asyncio.wait_for(
            asyncio.gather(mdns_coro, modbus_coro, opcua_tcp_coro, find_servers_coro, return_exceptions=True),
            timeout=overall_timeout,
        )
    except asyncio.TimeoutError:
        log.warning("discovery overall timeout", subnet=subnet, timeout=overall_timeout)
        return []
    except Exception as e:  # pragma: no cover
        log.warning("discovery gather failed", error=str(e))
        return []

    mdns_res, modbus_res, opcua_tcp_res, find_servers_res = results  # type: ignore
    if isinstance(mdns_res, Exception):
        log.warning("mdns error", error=str(mdns_res))
        mdns_res = []
    if isinstance(modbus_res, Exception):
        log.warning("modbus scan error", error=str(modbus_res))
        modbus_res = []
    if isinstance(opcua_tcp_res, Exception):
        log.warning("opcua tcp scan error", error=str(opcua_tcp_res))
        opcua_tcp_res = []
    if isinstance(find_servers_res, Exception):
        log.warning("find_servers error", error=str(find_servers_res))
        find_servers_res = []

    seen: set[tuple[str, str, int]] = set()
    merged: List[Dict[str, Any]] = []
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
