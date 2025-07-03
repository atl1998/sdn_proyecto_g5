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
    "administrativo": ["http", "dns", "ssh", "mysql"]
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
        print("\n--- MENÚ CONEXIONES ---")
        print("1) Crear conexión")
        print("2) Listar conexiones")
        print("3) Eliminar conexión")
        print("0) Finalizar")
        opcion = input("Seleccione una opción: ").strip()

        if opcion == '1':
            # Autenticación
            print("🔐 Inicie sesión para crear una conexión:")
            usuario = input("👤 Usuario: ").strip()
            clave = input("🔒 Contraseña: ").strip()

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
            dpid_cliente, port_cliente = get_attachment_point_by_ip(ip_alumno)

            for servicio in servicios_autorizados:
                handler = str(uuid.uuid4())[:8]
                conexiones.append({'handler': handler, 'servicio': servicio})
                print(f"📶 Conexión creada. Handler: {handler} para {servicio}")

                ip_servidor = "10.0.0.3"
                mac_servidor = "fa:16:3e:04:3f:65"  # debes asegurarte de que sea la correcta
                puerto_servicio = PUERTOS_POR_SERVICIO.get(servicio)

                if not puerto_servicio:
                    print(f"❌ Puerto no definido para el servicio: {servicio}")
                    continue

                dpid_servidor, port_servidor = get_attachment_point_by_ip(ip_servidor)
                if not dpid_servidor or not port_servidor:
                    print("❌ No se pudo obtener el DPID o puerto del servidor.")
                    continue

                # ➤ FLOW FW: Cliente → Servidor
                flow_fw = build_flow(handler, dpid_cliente, mac_alumno, ip_alumno, mac_servidor, ip_servidor, puerto_servicio, port_cliente, sentido="fw")
                push_flow(flow_fw)
                print(f"✅ Flow Forward: {flow_fw['name']}")

                # ➤ FLOW BW: Servidor → Cliente
                flow_bw = build_flow(handler, dpid_servidor, mac_servidor, ip_servidor, mac_alumno, ip_alumno, puerto_servicio, port_servidor, sentido="bw")
                push_flow(flow_bw)
                print(f"✅ Flow Reverse: {flow_bw['name']}")

                # ➤ ARP FW
                flow_arp_fw = build_arp_flow(handler, dpid_cliente, ip_alumno, ip_servidor, port_cliente, sentido="arp_fw")
                push_flow(flow_arp_fw)
                print(f"✅ Flow ARP FW: {flow_arp_fw['name']}")

                # ➤ ARP BW
                flow_arp_bw = build_arp_flow(handler, dpid_servidor, ip_servidor, ip_alumno, port_servidor, sentido="arp_bw")
                push_flow(flow_arp_bw)
                print(f"✅ Flow ARP BW: {flow_arp_bw['name']}")


        elif opcion == '2':
            if not conexiones:
                print("No hay conexiones creadas.")
            else:
                for c in conexiones:
                    print(f"Handler: {c['handler']}, Servicio: {c['servicio']}")

        elif opcion == '3':
            handler = input("Handler de la conexión a eliminar: ")
            for i, c in enumerate(conexiones):
                if c['handler'] == handler:
                    # Eliminar los flows correspondientes en Floodlight
                    delete_flow(f"{handler}_fw")
                    delete_flow(f"{handler}_bw")
                    delete_flow(f"{handler}_arp_fw")
                    delete_flow(f"{handler}_arp_bw")

                    # Eliminar la conexión de la lista
                    conexiones.pop(i)
                    print(" Conexión eliminada y flows removidos.")
                    break
            else:
                print(" No se encontró el handler.")

        elif opcion == '0':
            print("👋 Saliendo del sistema.")
            break
        else:
            print("⚠️ Opción no válida.")

def get_attachment_point_by_ip(ip):
    url = f"{BASE_URL}/wm/device/"
    try:
        r = requests.get(url)
        if r.status_code == 200:
            for dev in r.json():
                if ip in dev.get("ipv4", []):
                    ap = dev.get("attachmentPoint", [])
                    if ap:
                        return ap[0].get("switchDPID"), ap[0].get("port")
    except Exception as e:
        print(f"Error al consultar Floodlight: {e}")
    return None, None

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
def push_flow(flow):
    url = f"{BASE_URL}/wm/staticflowpusher/json"
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=flow, headers=headers)
        if response.status_code == 200:
            print(" Flow instalado en Floodlight.")
        else:
            print(f" Error al instalar flow: {response.text}")
    except Exception as e:
        print(f" No se pudo conectar a Floodlight: {e}")


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

