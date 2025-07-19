import requests
import re
import time

# CONFIGURACIÓN
FAST_LOG_PATH = "/var/log/suricata/fast.log"
FLOODLIGHT_API_URL = "http://192.168.201.200:8080/wm/staticflowpusher/json"

# Historial para evitar duplicados
ip_bloqueadas = set()

def extraer_ip_origen(linea):
    match = re.search(r"{[A-Z]+} (\d+\.\d+\.\d+\.\d+):\d+ ->", linea)
    if match:
        return match.group(1)
    return None

def get_dpid_and_port_from_ip(ip_objetivo):
    try:
        r = requests.get("http://192.168.201.200:8080/wm/device/")
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

def crear_flow_entry(ip, dpid, port):
    return {
        "switch": dpid,
        "name": f"block_{ip.replace('.', '_')}",
        "priority": "1000",
        "ipv4_src": ip,
        "eth_type": "0x0800",
        "in_port": str(port),
        "active": "true",
        "actions": ""  # sin acción = drop
    }

def enviar_flow(flow_entry):
    response = requests.post(FLOODLIGHT_API_URL, json=flow_entry)
    if response.status_code == 200:
        print(f"[+] IP bloqueada: {flow_entry['ipv4_src']} en switch {flow_entry['switch']} puerto {flow_entry['in_port']}")
    else:
        print(f"[!] Error al bloquear IP: {response.status_code} - {response.text}")

def monitorear_fastlog():
    print("[*] Monitoreando fast.log...")
    with open(FAST_LOG_PATH, "r") as f:
        f.seek(0, 2)  # Ir al final del archivo
        while True:
            linea = f.readline()
            if not linea:
                time.sleep(1)
                continue
            if "Posible DDoS interno" in linea:
                ip = extraer_ip_origen(linea)
                if ip and ip not in ip_bloqueadas:
                    mac, dpid, port = get_dpid_and_port_from_ip(ip)
                    if dpid and port:
                        flow = crear_flow_entry(ip, dpid, port)
                        enviar_flow(flow)
                        ip_bloqueadas.add(ip)
                    else:
                        print(f"[!] No se pudo determinar DPID/port para {ip}, no se bloquea.")

if __name__ == "__main__":
    monitorear_fastlog()

