"""
RUN WITH:
    python example.py
"""

from __future__ import annotations

import asyncio

import cve_c
import exploitdb
import httpx_client
import zeroday
from exceptions import APIError, NotFoundError


async def main() -> None:
    async with httpx_client.lifespan():

        try:
            cve = await cve_c.get_cve("CVE-2024-12345")
            print("CVE encontrado:", cve is not None)
        except APIError as e:
            print(f"Erro ao buscar CVE: {e.status_code} - {e.detail}")

        afetados = await cve_c.search_cves_by_package("log4j", limit=10)
        print(f"{len(afetados)} CVEs afetando 'log4j'.")

        exploits = await exploitdb.search_exploits("apache", limit=10)
        print(f"{len(exploits)} exploits encontrados para 'apache'.")

        try:
            exploit = await exploitdb.get_exploit("00000")
        except NotFoundError:
            exploit = None
        print("Exploit '00000' encontrado?", exploit is not None)

        zerodays = await zeroday.search_zeroday_exploits("chrome", limit=10)
        print(f"{len(zerodays)} exploits zero-day encontrados para 'chrome'.")


if __name__ == "__main__":
    asyncio.run(main())