import requests
import yaml
from prettytable import PrettyTable

FLOODLIGHT_URL = "http://10.20.12.161:8080"

alumnos = []
cursos = []
servidores = []
conexiones = []

class Alumno:
    def __init__(self, nombre, codigo, mac):
        self.nombre = nombre
        self.codigo = codigo
        self.mac = mac

class Curso:
    def __init__(self, codigo, nombre, estado, alumnos=None, servidores=None):
        self.codigo = codigo
        self.nombre = nombre
        self.estado = estado
        self.alumnos = alumnos if alumnos else []
        self.servidores = servidores if servidores else []

    def agregar_alumno(self, alumno):
        self.alumnos.append(alumno)

    def remover_alumno(self, alumno):
        if alumno in self.alumnos:
            self.alumnos.remove(alumno)

    def agregar_servidor(self, servidor):
        self.servidores.append(servidor)

class Servidor:
    def __init__(self, nombre, ip, servicios=None):
        self.nombre = nombre
        self.ip = ip
        self.servicios = servicios if servicios else []

    def agregar_servicio(self, servicio):
        self.servicios.append(servicio)

class Servicio:
    def __init__(self, nombre, protocolo, puerto):
        self.nombre = nombre
        self.protocolo = protocolo
        self.puerto = puerto

class Conexion:
    def __init__(self, handler, alumno, servidor, servicio):
        self.handler = handler
        self.alumno = alumno
        self.servidor = servidor
        self.servicio = servicio

def menu_conexiones():
    while True:
        print("Bienvenido al submenú de conexiones owo ")
        print("1. Crear conexión")
        print("2. Listar conexiones")
        print("3. Borrar conexión")
        print("4. Volver al menú principal ")
        opcion = input("Seleccione una opción: ")

        if opcion == "1":
            crear_conexion()
        elif opcion == "2":
            listar_conexiones()
        elif opcion == "3":
            borrar_conexion()
        elif opcion == "4":
            break
        else:
            print("Opción no válida")

def listar_conexiones():
    global conexiones
    if not conexiones:
        print("No hay conexiones registradas.")
    else:
        table = PrettyTable()
        table.field_names = ["Handler", "Alumno", "Servidor", "Servicio"]
        for c in conexiones:
            table.add_row([c.handler, c.alumno.nombre, c.servidor.nombre, c.servicio.nombre])
        print(table)
        
def crear_conexion():
    global conexiones
    cod_alumno = input("Código del alumno: ")
    nombre_servicio = input("Servicio (ej: ssh): ").lower()
    nombre_servidor = input("Servidor (ej: Servidor 1): ")

    alumno = next((a for a in alumnos if a.codigo == cod_alumno), None)
    servidor = next((s for s in servidores if s.nombre == nombre_servidor), None)

    if not alumno or not servidor:
        print("Alumno o servidor no encontrado.")
        return

    autorizado = False
    for curso in cursos:
        if curso.estado == "DICTANDO" and cod_alumno in curso.alumnos:
            for srv in curso.servidores:
                if srv["nombre"] == nombre_servidor and nombre_servicio in srv["servicios_permitidos"]:
                    autorizado = True

    if not autorizado:
        print("Alumno NO autorizado para acceder al servicio.")
        return

    servicio_obj = next((x for x in servidor.servicios if x.nombre == nombre_servicio), None)

    if servicio_obj:
        mac_src = alumno.mac
        ip_dst = servidor.ip
        protocolo = servicio_obj.protocolo
        puerto = servicio_obj.puerto
        success = insertar_flows(mac_src, ip_dst, protocolo, puerto)

        if success:
            handler = f"{alumno.codigo}-{servidor.nombre}-{servicio_obj.nombre}"
            conexiones.append(Conexion(handler, alumno, servidor, servicio_obj))
            print(f"Conexión creada con handler: {handler}")
        else:
            print("Error al insertar flow.")
    else:
        print("Servicio no encontrado.")

def borrar_conexion():
    global conexiones
    handler = input("Ingrese el handler de la conexión a eliminar: ")
    conexion = next((c for c in conexiones if c.handler == handler), None)
    if conexion:
        requests.delete(f"{FLOODLIGHT_URL}/wm/staticflowpusher/json", json={"name": handler})
        conexiones.remove(conexion)
        print(f"Conexión con handler '{handler}' eliminada correctamente.")
    else:
        print("No se encontró una conexión con ese handler.")

#Punto de conexión de un host
def get_attachment_points(mac_address):
    url = f"{FLOODLIGHT_URL}/wm/device/"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        for host in data:
            if mac_address.lower() in [m.lower() for m in host.get("mac", [])]:
                aps = host.get("attachmentPoint", [])
                if aps:
                    punto = aps[0]
                    return punto["switchDPID"], punto["port"]
                else:
                    print(f"La MAC {mac_address} no tiene attachmentPoint.")
        print(f"La MAC {mac_address} no fue encontrada.")
    else:
        print(f"[{response.status_code}]")
        print(f"Respuesta: {response.text}")
    
    return None, None

def menu_alumnos():
    while True:
        print("Bienvenido al submenú de alumnos owo ")
        print("1. Listar")
        print("2. Mostrar detalle")
        print("3. Volver al menú principal")
        opcion_alumnos = input("Seleccione una opción: ")
        if opcion_alumnos == "1":
            listar_alumnos()
        elif opcion_alumnos == "2":
            detalle_alumno()
        elif opcion_alumnos == "3": 
            break
        else:
            print("Opción no válida")

def listar_alumnos():
    global alumnos
    while True:
        print("1. Mostrar todos los alumnos")
        print("2. Filtrar por curso")
        print("3. Volver")
        opc_lista_alumnos = input("Seleccione una opción: ")
        if opc_lista_alumnos == "1":
            table = PrettyTable()
            table.field_names = ["Código", "Nombre", "MAC"]
            for a in alumnos:
                table.add_row([a.codigo, a.nombre, a.mac])
            print(table)
            break
        elif opc_lista_alumnos == "2":
            cod_curso = input("Ingrese el código del curso: ")
            curso = next((c for c in cursos if c.codigo == cod_curso), None)
            if not curso:
                print("Curso no encontrado.")
            else:
                table = PrettyTable()
                table.field_names = ["Código", "Nombre", "MAC"]
                for cod in curso.alumnos:
                    alumno = next((a for a in alumnos if a.codigo == cod), None)
                    if alumno:
                        table.add_row([alumno.codigo, alumno.nombre, alumno.mac])
                print(table)
        elif opc_lista_alumnos == "3":
            break
        else:
            print("Ingrese una opción válida")

def detalle_alumno():
    global alumnos
    codigo = input("Ingrese el código del alumno: ")
    alumno = next((a for a in alumnos if a.codigo == codigo), None)
    if alumno:
        print(f"Nombre: {alumno.nombre}\nCódigo: {alumno.codigo}\nMAC: {alumno.mac}")
    else:
        print("Alumno no encontrado.")

def menu_cursos():
    while True:
        print("Bienvenido al submenú de cursos owo ")
        print("1. Listar ")
        print("2. Mostrar detalle ")
        print("3. Actualizar ")
        print("4. Volver al menú principal")
        opcion_cursos = input("Seleccione una opción: ")
        if (opcion_cursos=="1"):
            listar_cursos()
        elif (opcion_cursos=="2"):
            detalle_curso()
        elif (opcion_cursos=="3"): 
            actualizar_curso()
        elif (opcion_cursos=="4"): 
            break
        else:
            print("Opción no válida")

def listar_cursos():
    global cursos
    if not cursos:
        print("No hay cursos registrados.")
    else:
        table = PrettyTable()
        table.field_names = ["Código", "Nombre", "Estado"]
        for c in cursos:
            table.add_row([c.codigo, c.nombre, c.estado])
        print(table)

def detalle_curso():
    global cursos
    codigo = input("Ingrese el código del curso: ")
    curso = next((c for c in cursos if c.codigo == codigo), None)
    if curso:
        print(f"Nombre: {curso.nombre}\nEstado: {curso.estado}")
        print("Alumnos:")
        for cod in curso.alumnos:
            print(f" - {cod}")
        print("Servidores:")
        for s in curso.servidores:
            print(f" - {s['nombre']}")
            print(f"   Servicios permitidos: {', '.join(s['servicios_permitidos'])}")
    else:
        print("Curso no encontrado.")

def actualizar_curso():
    global cursos, alumnos
    codigo = input("Ingrese el código del curso a actualizar: ")
    curso = next((c for c in cursos if c.codigo == codigo), None)

    if not curso:
        print("Curso no encontrado.")
        return

    while True:
        print(f"\nCurso: {curso.codigo} - {curso.nombre}")
        print("1. Agregar alumno")
        print("2. Eliminar alumno")
        print("3. Volver")
        op = input("Seleccione una opción: ")

        if op == "1":
            cod_alumno = input("Código del alumno a agregar: ")
            if cod_alumno in curso.alumnos:
                print("El alumno ya está inscrito en el curso.")
            else:
                curso.agregar_alumno(cod_alumno)
                print("Alumno agregado correctamente.")
        elif op == "2":
            cod_alumno = input("Código del alumno a eliminar: ")
            if cod_alumno in curso.alumnos:
                curso.remover_alumno(cod_alumno)
                print("Alumno eliminado del curso.")
            else:
                print("El alumno no pertenece al curso.")
        elif op == "3":
            break
        else:
            print("Opción inválida.")

def listar_servidores():
    global servidores
    if not servidores:
        print("No hay servidores registrados.")
    else:
        table = PrettyTable()
        table.field_names = ["Nombre", "IP", "Servicios"]
        for s in servidores:
            servicios_str = ", ".join([f"{srv.nombre}({srv.protocolo}:{srv.puerto})" for srv in s.servicios])
            table.add_row([s.nombre, s.ip, servicios_str])
        print(table)

def detalle_servidor():
    global servidores
    nombre = input("Ingrese el nombre del servidor: ")
    servidor = next((s for s in servidores if s.nombre == nombre), None)
    if servidor:
        print(f"IP: {servidor.ip}\nServicios:")
        for srv in servidor.servicios:
            print(f" - {srv.nombre} ({srv.protocolo}:{srv.puerto})")
    else:
        print("Servidor no encontrado.")

def menu_servidores():
    while True:
        print("Bienvenido al submenú de servidores owo ")
        print("1. Listar")
        print("2. Mostrar detalle")
        print("3. Volver al menú principal")
        opcion_servidores = input("Seleccione una opción: ")
        if opcion_servidores == "1":
            listar_servidores()
        elif opcion_servidores == "2":
            detalle_servidor()
        elif opcion_servidores == "3":
            break
        else:
            print("Opción no válida")

def importar_datos(name_archivo):
    with open(name_archivo, 'r') as file:
        data = yaml.safe_load(file)

    alumnos = [Alumno(a['nombre'], str(a['codigo']), a['mac']) for a in data.get('alumnos', [])]

    cursos = []
    for c in data.get('cursos', []):
        cursos.append(Curso(
            nombre=c['nombre'],
            estado=c['estado'],
            alumnos=[str(cod) for cod in c['alumnos']],  
            servidores=c['servidores'],
            codigo=c['codigo']
        ))

    servidores = []
    for s in data.get('servidores', []):
        servicios = [Servicio(**serv) for serv in s['servicios']]
        servidores.append(Servidor(s['nombre'], s['ip'], servicios))

    return alumnos, cursos, servidores

def insertar_flows(mac_src, ip_dst, protocolo, puerto):
    dpid, port = get_attachment_points(mac_src)
    if not dpid:
        print("No se pudo determinar el punto de conexión.")
        return False

    flow = {
        "switch": dpid,
        "name": f"flow_{mac_src}_{ip_dst}_{puerto}",
        "priority": "32768",
        "eth_type": "0x0800",
        "ipv4_dst": ip_dst,
        "eth_src": mac_src,
        "ip_proto": "0x06" if protocolo.lower() == "tcp" else "0x11",
        "tp_dst": str(puerto),
        "active": "true",
        "actions": f"output={port}"  
    }
    response = requests.post(f"{FLOODLIGHT_URL}/wm/staticflowpusher/json", json=flow)
    return response.status_code == 200



def get_route(src_dpid, src_port, dst_dpid, dst_port):

    url = f"{FLOODLIGHT_URL}/wm/topology/route/{src_dpid}/{src_port}/{dst_dpid}/{dst_port}/json"
    response = requests.get(url)

    if response.status_code == 200:
        ruta = response.json()
        
        return [(hop["switch"], hop["port"]["portNumber"]) for hop in ruta]
    return []




def menu():
    while True:
        print("####################################################")
        print("Network Policy manager de la UPSM")
        print("####################################################")
        print("\n--- MENÚ ---")
        print("1. Importar ")
        print("2. Exportar")
        print("3. Cursos")
        print("4. Alumnos")
        print("5. Servidores")
        print("6. Políticas")
        print("7. Conexiones")
        print("0. Salir")
        opc = input("Seleccione una opción: ")

        if opc == "1":
            name = input("Ingresa el nombre  del archivo YAML: ")
            global alumnos, cursos, servidores
            if not name.endswith(".yaml"):
                name += ".yaml"
            alumnos, cursos, servidores = importar_datos(name)
            print("Datos importados exitosamente :D")
            print("Presione m para volver al menú: ")
            while True:
                tecla = input()
                if tecla=="m":
                    break
                else:
                    continue
        elif opc == "3":
            menu_cursos()
        elif opc == "4":
            menu_alumnos()
        elif opc == "5":
            menu_servidores()
        elif opc == "7":
            menu_conexiones()
        elif opc == "0":
            break

if __name__ == "__main__":
    menu()