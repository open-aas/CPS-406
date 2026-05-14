#!/usr/bin/env python3
"""
Carrega todos os arquivos AAS JSON do CP-L-406-1 no Eclipse BaSyx AAS Environment.

Uso:
    python3 upload_aas.py [--url http://localhost:8081]

Requer: requests  (pip install requests)
"""

import argparse
import base64
import glob
import json
import os
import sys
import time

import requests

DEFAULT_BASE_URL = "http://localhost:8081"

# Ordem de upload: sistema pai por último (garante que sub-assets já existem)
UPLOAD_ORDER = [
    # Esteiras (6)
    "cp_l_linear_v2_magfront.json",
    "cp_l_linear_v2_meas.json",
    "cp_l_linear_v2_idrill.json",
    "cp_l_linear_v2_magback.json",
    "cp_l_linear_v2_mpress.json",
    "cp_l_linear_v2_out.json",
    # Módulos de aplicação (7)
    "cp_am_mag_front.json",
    "cp_am_measure_v2.json",
    "cp_am_idrill.json",
    "cp_am_mag_back.json",
    "cp_am_press.json",
    "cp_am_out.json",
    "cp_am_mag.json",
    # Esteira genérica (tipo)
    "cp_l_linear_v2.json",
    # Sistema (pai)
    "cp_l_406_1_system.json",
]


def b64url(value: str) -> str:
    """Codifica um ID em Base64 URL-safe sem padding (padrão BaSyx v2)."""
    return base64.urlsafe_b64encode(value.encode()).rstrip(b"=").decode()


def upload_shell(base_url: str, shell: dict) -> bool:
    shell_id = shell["id"]
    url = f"{base_url}/shells"
    r = requests.post(url, json=shell, headers={"Content-Type": "application/json"})
    if r.status_code in (200, 201):
        print(f"  [OK] AAS: {shell_id}")
        return True
    if r.status_code == 409:
        # Já existe — atualizar
        enc = b64url(shell_id)
        r2 = requests.put(f"{url}/{enc}", json=shell, headers={"Content-Type": "application/json"})
        if r2.status_code in (200, 204):
            print(f"  [UP] AAS (atualizado): {shell_id}")
            return True
    print(f"  [ERR] AAS {shell_id}: HTTP {r.status_code} — {r.text[:120]}")
    return False


def upload_submodel(base_url: str, submodel: dict) -> bool:
    sm_id = submodel["id"]
    url = f"{base_url}/submodels"
    r = requests.post(url, json=submodel, headers={"Content-Type": "application/json"})
    if r.status_code in (200, 201):
        print(f"    [OK] SM: {sm_id}")
        return True
    if r.status_code == 409:
        enc = b64url(sm_id)
        r2 = requests.put(f"{url}/{enc}", json=submodel, headers={"Content-Type": "application/json"})
        if r2.status_code in (200, 204):
            print(f"    [UP] SM (atualizado): {sm_id}")
            return True
    print(f"    [ERR] SM {sm_id}: HTTP {r.status_code} — {r.text[:120]}")
    return False


def wait_for_basyx(base_url: str, timeout: int = 60) -> bool:
    print(f"Aguardando BaSyx em {base_url} ...", end="", flush=True)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(f"{base_url}/shells", timeout=3)
            if r.status_code < 500:
                print(" OK")
                return True
        except Exception:
            pass
        print(".", end="", flush=True)
        time.sleep(2)
    print(" TIMEOUT")
    return False


def main():
    parser = argparse.ArgumentParser(description="Carrega arquivos AAS no BaSyx")
    parser.add_argument("--url", default=DEFAULT_BASE_URL, help="URL base do AAS Environment")
    parser.add_argument("--dir", default=os.path.dirname(os.path.abspath(__file__)),
                        help="Diretório com os arquivos JSON")
    parser.add_argument("--no-wait", action="store_true", help="Não aguardar o BaSyx iniciar")
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    aas_dir  = args.dir

    if not args.no_wait:
        if not wait_for_basyx(base_url):
            print("BaSyx não respondeu. Execute: docker compose up -d")
            sys.exit(1)

    # Descobrir arquivos: usar a ordem definida; adicionar os não listados ao final
    ordered = [f for f in UPLOAD_ORDER if os.path.exists(os.path.join(aas_dir, f))]
    remaining = [os.path.basename(p) for p in sorted(glob.glob(f"{aas_dir}/*.json"))
                 if os.path.basename(p) not in ordered and not os.path.basename(p).startswith("update_")]
    files_to_process = ordered + remaining

    ok_shells = 0
    ok_sms    = 0
    errors    = 0

    for fname in files_to_process:
        path = os.path.join(aas_dir, fname)
        if not os.path.exists(path):
            continue
        print(f"\n{fname}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        for shell in data.get("assetAdministrationShells", []):
            if upload_shell(base_url, shell):
                ok_shells += 1
            else:
                errors += 1

        for sm in data.get("submodels", []):
            if upload_submodel(base_url, sm):
                ok_sms += 1
            else:
                errors += 1

    print(f"\n{'='*50}")
    print(f"AAS shells carregados : {ok_shells}")
    print(f"Submodels carregados  : {ok_sms}")
    print(f"Erros                 : {errors}")
    print(f"\nUI disponível em: http://localhost:3000")
    print(f"API disponível em: {base_url}")


if __name__ == "__main__":
    main()
