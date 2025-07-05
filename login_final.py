from pyrad.client import Client
from pyrad.dictionary import Dictionary
from pyrad.packet import AccessRequest, AccessAccept, AccessReject
import getpass
import pymysql
import subprocess
from datetime import datetime

import json
import yaml
import requests
import uuid
from typing import List, Dict, Optional, Any

BASE_URL = f"http://192.168.201.200:8080"
FLOW_PUSHER_URL = f"{BASE_URL}/wm/staticflowpusher/json"

# === CONFIGURACIONES ===

client = Client(server="192.168.201.200", secret=b"testing123", dict=Dictionary("dictionary"))
client.AuthPort = 1812

DB_CONFIG = {
    "host": "192.168.201.200",
    "user": "radius",
    "password": "radiuspass",
    "database": "radius"
}

MYDB_CONFIG = {
    "host": "192.168.201.200",
    "user": "mydb_user",
    "password": "mydb_pass",
    "database": "mydb"
}

SERVICIOS_POR_ROL = {
    "soporte": ["http", "dns", "ssh"],
    "administracion": ["http", "dns", "ssh", "mysql"]
}

PUERTOS_POR_SERVICIO = {
    "http": 80,
    "https": 443,
    "dns": 53,
    "ssh": 22,
    "mysql": 3306,
    "ftp":21
}

conexiones = []

# === FUNCIONES AUXILIARES ===

def obtener_mac_y_ip(interfaz):
    comando = f"ip addr show {interfaz}"
    resultado = subprocess.run(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    mac = ip = None
    for linea in resultado.stdout.splitlines():
        if "link/ether" in linea:
            mac = linea.split()[1]
        elif "inet " in linea:
            ip = linea.split()[1].split('/')[0]
    return mac, ip

def registrar_log(usuario, resultado, rol="N/A", ip="N/A", mac="N/A"):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("logs_acceso.txt", "a") as f:
        f.write(f"{now} | Usuario: {usuario} | Resultado: {resultado} | Rol: {rol} | IP: {ip} | MAC: {mac}\n")

def autenticar_usuario(usuario, contrasena):
    req = client.CreateAuthPacket(code=AccessRequest, User_Name=usuario)
    req["User-Password"] = req.PwCrypt(contrasena)

    try:
        reply = client.SendPacket(req)

        if reply.code == AccessAccept:
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cursor:
                    cursor.execute("SELECT groupname FROM radusergroup WHERE username = %s", (usuario,))
                    resultado = cursor.fetchone()
                    rol = resultado[0] if resultado else "No asignado"
                    return True, rol
            except Exception as e:
                print(f"❌ Error al consultar MySQL: {e}")
                return True, "Error en DB"
            finally:
                try:
                    conn.close()
                except:
                    pass

        elif reply.code == AccessReject:
            return False, "Denegado"
        else:
            print(f"⚠️ Respuesta inesperada del servidor: {reply.code}")
            return False, "Error"

    except Exception as e:
        print(f"❌ Error al conectar con FreeRADIUS: {e}")
        return False, "Error"


def obtener_servicios_por_usuario(codigo_usuario):
    try:
        conn = pymysql.connect(**MYDB_CONFIG)
        with conn.cursor() as cursor:
            consulta = """
                SELECT DISTINCT s.nombreservicio
                FROM usuarios u
                JOIN cursos_has_usuarios chu ON u.idusuarios = chu.usuarios_idusuarios
                JOIN cursos c ON chu.cursos_idcursos = c.idcursos
                JOIN servicios s ON s.cursos_idcursos = c.idcursos
                WHERE u.codigousuario = %s;
            """
            cursor.execute(consulta, (codigo_usuario,))
            resultados = cursor.fetchall()
            return [r[0] for r in resultados] if resultados else []
    except Exception as e:
        print(f"❌ Error al consultar cursos y servicios en mydb: {e}")
        return []
    finally:
        try:
            conn.close()
        except:
            pass


# === MENÚ PRINCIPAL ===

def menu_conexiones():
    while True:
        print("\n--- BIENVENIDO A LA RED PUCP ---")
        print("1) Iniciar conexion")
        print("2) Lista de servicios disponibles")
        print("3) Eliminar conexión de servicios")
        print("0) Finalizar")
        opcion = input("Seleccione una opción: ").strip()

        if opcion == '1':
            # Autenticación
            print("🔐 Inicie sesión para crear una conexión:")
            usuario = input("👤 Usuario: ").strip()
            clave = getpass.getpass("🔒 Contraseña: ").strip()


            # Autenticar con FreeRADIUS y obtener rol
            autenticado, rol = autenticar_usuario(usuario, clave)
            mac_alumno, ip_alumno = obtener_mac_y_ip('ens4')

            if not autenticado:
                print("❌ Acceso denegado.")
                registrar_log(usuario, "Denegado", "N/A", ip_alumno, mac_alumno)
                continue

            print(f"\n✅ Bienvenido {usuario} ({rol})")
            print(f"📡 IP: {ip_alumno} | MAC: {mac_alumno}")
            registrar_log(usuario, "Autenticado", rol, ip_alumno, mac_alumno)

            # Mostrar servicios disponibles para su rol
            if rol.lower() in ['alumno', 'docente']:
                servicios_autorizados = obtener_servicios_por_usuario(usuario)
            else:
                servicios_autorizados = SERVICIOS_POR_ROL.get(rol.lower(), [])

            if not servicios_autorizados:
                print("⚠️ No hay servicios disponibles para su rol.")
                continue

            # Punto de red del cliente (dinámico)
            dpid_cliente, port_cliente = get_attachment_point(mac_alumno)
            ip_servidor = "10.0.0.3"
            mac_servidor = "fa:16:3e:04:3f:65" 
            dpid_servidor, port_servidor = get_attachment_point(mac_servidor)

            if None in (dpid_cliente, port_cliente, dpid_servidor, port_servidor):
                print("❌ No se pudo obtener la ubicación de uno o ambos hosts.")
                continue

            ruta = get_route(dpid_cliente, port_cliente, dpid_servidor, port_servidor)
            if not ruta:
                print("❌ No se encontró una ruta entre los hosts.")
                exit()

            print(f"\n📍 Ruta detectada entre {mac_alumno} y {mac_servidor}:")
            for sw, port in ruta:
                print(f"  Switch: {sw}, Puerto: {port}")


            for servicio in servicios_autorizados:
                handler = str(uuid.uuid4())[:8]
                conexiones.append({'handler': handler, 'servicio': servicio})
                print(f"📶 Conexión creada. Handler: {handler} para {servicio}")

                puerto_servicio = PUERTOS_POR_SERVICIO.get(servicio)
                if not puerto_servicio:
                    print(f"❌ Puerto no definido para el servicio: {servicio}")
                    continue                

                # Flujos TCP
                flows_ida = generar_flows(ruta, ip_alumno, ip_servidor, puerto_servicio, mac_alumno, mac_servidor, handler, direccion="ida")
                flows_vuelta = generar_flows(ruta, ip_alumno, ip_servidor, puerto_servicio, mac_alumno, mac_servidor, handler, direccion="vuelta")

                # Flujos ARP
                flow_arp_fw = build_arp_flow(handler, dpid_cliente, ip_alumno, ip_servidor, port_cliente, "arp_fw")
                flow_arp_bw = build_arp_flow(handler, dpid_servidor, ip_servidor, ip_alumno, port_servidor, "arp_bw")

                # Enviar todo
                enviar_flows(flows_ida + flows_vuelta + [flow_arp_fw, flow_arp_bw])


        elif opcion == '2':
            if not conexiones:
                print("No hay conexiones de servicios disponibles.")
            else:
                for c in conexiones:
                    print(f"Handler: {c['handler']}, Servicio: {c['servicio']}")

        elif opcion == '3':
            handler = input("Ingrese el handler de la conexión que desea eliminar: ")
            encontrado = False
            for i, c in enumerate(conexiones):
                if c['handler'] == handler:
                    # Eliminar los flows correspondientes en Floodlight
                    for j in range(len(ruta) - 1):
                        delete_flow(f"{handler}_ida_{j}")
                        delete_flow(f"{handler}_vuelta_{j}")
                    delete_flow(f"{handler}_arp_fw")
                    delete_flow(f"{handler}_arp_bw")

                    conexiones.pop(i)
                    print("✅ Conexión eliminada y flows removidos.")
                    encontrado = True
                    break  # salimos del bucle
            if not encontrado:
                print("❌ No se encontró el handler.")


        elif opcion == '0':
            print("👋 Saliendo del sistema.")
            break
        else:
            print("⚠️ Opción no válida.")

#obtenemos el dpid del switch asi como el puerto
def get_attachment_point(mac):
    url = f"{BASE_URL}/wm/device/"
    r = requests.get(url)
    if r.status_code == 200:
        for dev in r.json():
            if mac.lower() in [m.lower() for m in dev.get("mac", [])]:
                point = dev.get("attachmentPoint", [{}])[0]
                return point.get("spwitchDPID"), point.get("port")
    return None, None

#obtenemos la ruta de switches para ir del cliente al servidor
def get_route(src_dpid, src_port, dst_dpid, dst_port):
    url = f"{BASE_URL}/wm/topology/route/{src_dpid}/{src_port}/{dst_dpid}/{dst_port}/json"
    r = requests.get(url)
    if r.status_code == 200:
        return [(step["switch"], step["port"]) for step in r.json()]
    return []

def generar_flows(ruta, ip_src, ip_dst, tcp_port, mac_src, mac_dst, handler, direccion="ida"):
    flows = []
    for i in range(len(ruta) - 1):
        sw_actual, in_port_obj = ruta[i]
        in_port = in_port_obj["portNumber"] if isinstance(in_port_obj, dict) else in_port_obj

        _, out_port_obj = ruta[i + 1]
        out_port = out_port_obj["portNumber"] if isinstance(out_port_obj, dict) else out_port_obj


        flow = {
            "switch": sw_actual,
            "name": f"{handler}_{direccion}_{i}",
            "priority": "32768",
            "eth_type": "0x0800",
            "eth_src": mac_src,
            "eth_dst": mac_dst,
            "ipv4_src": ip_src if direccion == "ida" else ip_dst,
            "ipv4_dst": ip_dst if direccion == "ida" else ip_src,
            "ip_proto": "0x06",
            "tcp_dst": str(tcp_port) if direccion == "ida" else None,
            "tcp_src": str(tcp_port) if direccion == "vuelta" else None,
            "in_port": str(in_port),
            "active": "true",
            "actions": f"output={out_port}"
        }

        # Eliminar campos None
        flows.append({k: v for k, v in flow.items() if v is not None})
    return flows



def build_flow(handler, dpid, mac_src, ip_src, mac_dst, ip_dst, tcp_port, out_port, sentido="fw"):
    """
    Construye un flow para tráfico de L3 (IP) y L4 (TCP/UDP).
    """
    flow = {
        "switch": dpid,
        "name": f"{handler}_{sentido}",
        "priority": "32768",
        "eth_type": "0x0800",       # IPv4
        "ipv4_src": ip_src,
        "ipv4_dst": ip_dst,
        "ip_proto": "0x06",         # TCP
        "tcp_dst": tcp_port,
        "eth_src": mac_src,
        "eth_dst": mac_dst,
        "active": "true",
        "actions": f"output={out_port}"
    }

    return flow

def build_arp_flow(handler, dpid, ip_src, ip_dst, out_port, sentido="arp"):
    """
    Flow para permitir ARP entre hosts.
    """
    flow = {
        "switch": dpid,
        "name": f"{handler}_{sentido}",
        "priority": "32769",  # Priorizamos ARP
        "eth_type": "0x0806",  # ARP
        "arp_spa": ip_src,  # IP de origen
        "arp_tpa": ip_dst,  # IP de destino
        "active": "true",
        "actions": f"output={out_port}"  # Acción de salida
    }
    return flow

# ===== insertar y eliminar flows =====
def enviar_flows(flows):
    for flow in flows:
        print(f"\n📤 Enviando flow: {flow['name']}")
        print(json.dumps(flow, indent=2))
        response = requests.post(FLOW_PUSHER_URL, json=flow)
        if response.status_code == 200:
            print(f"✅ Flow '{flow['name']}' instalado.")
        else:
            print(f"❌ Error al instalar '{flow['name']}': {response.status_code} - {response.text}")


def delete_flow(flow_name):
    url = f"{BASE_URL}/wm/staticflowpusher/json"
    data = {"name": flow_name}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.delete(url, json=data, headers=headers)
        if response.status_code == 200:
            print(" Flow eliminado de Floodlight.")
        else:
            print(f" Error al eliminar flow: {response.text}")
    except Exception as e:
        print(f" No se pudo conectar a Floodlight: {e}")

# === INICIO ===

if __name__ == "__main__":
    menu_conexiones()

