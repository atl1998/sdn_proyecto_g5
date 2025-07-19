import requests

# CONFIGURACIÓN
CONTROLADOR_URL = "http://192.168.201.200:8080"
IP_MALICIOSA = "10.0.0.1"
FLOW_NAME = f"block_{IP_MALICIOSA.replace('.', '_')}"


def get_dpid_and_port_from_ip(ip_objetivo): 
    try:
        r = requests.get(f"{CONTROLADOR_URL}/wm/device/")
        if r.status_code == 200:
            devices = r.json()
            for dev in devices:
                if ip_objetivo in dev.get("ipv4", []):
                    mac = dev.get("mac", [None])[0]
                    ap = dev.get("attachmentPoint", [])
                    if ap:
                        dpid = ap[0].get("switchDPID")
                        port = ap[0].get("port")
                        return mac, dpid, port
    except Exception as e:
        print(f"[!] Error al obtener DPID y puerto: {e}")
    return None, None, None


def eliminar_flow(dpid):
    data = {
        "name": FLOW_NAME,
        "switch": dpid
    }
    try:
        response = requests.delete(f"{CONTROLADOR_URL}/wm/staticflowpusher/json", json=data)
        if response.status_code == 200:
            print(f"[✓] Flow eliminado: {FLOW_NAME} del switch {dpid}")
        else:
            print(f"[!] Error al eliminar flow: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Error al conectar con el controlador: {e}")


if __name__ == "__main__":
    mac, dpid, port = get_dpid_and_port_from_ip(IP_MALICIOSA)
    if dpid:
        eliminar_flow(dpid)
    else:
        print(f"[!] No se encontró el DPID asociado a la IP {IP_MALICIOSA}. No se puede desbloquear.")

