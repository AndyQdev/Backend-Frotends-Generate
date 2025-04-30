import json
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.schemas.proyecto import ProyectoCreate, Proyecto
from app.models.models import Proyecto as ProyectoModel, Usuario, Page
from app.database import SessionLocal
from app.auth.dependencies import get_current_user
from datetime import datetime
from typing import List, Optional
from app.schemas.proyecto import ProyectoListResponse, ProyectoResponse, PageCreateIn, PageResponse
from app.models.models import ColaboradorProyecto
from sqlalchemy import desc
from app.schemas.proyecto import (
    ProyectoCreate, Proyecto, ProyectoListResponse, ProyectoResponse,
    ProyectoUpdate, PageUpdate        #  <-- importa los nuevos
)
import copy
import cv2, numpy as np, pytesseract, unicodedata, difflib, uuid, json
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
from xml.etree.ElementTree import fromstring
from faker import Faker
from fastapi import UploadFile, File, Form
from sqlalchemy import func
import unicodedata
import re
import os
import zipfile
import shutil
from jinja2 import Template
from fastapi.responses import FileResponse
from xml.etree.ElementTree import fromstring

router = APIRouter(prefix="/projects", tags=["Proyectos"])
ANGULAR_BASE = "angular_base"  # carpeta base con estructura angular vacía
TEMP_DIR = "/mnt/data/generated_projects"
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def extraer_clases(xml: bytes) -> list[dict]:
    """
    Extrae clases UML de un XMI 2.x (StarUML, EA, etc.)
    Devuelve: [{'nombre': 'User', 'atributos': ['id', 'nombre', ...]}, …]
    """
    root = fromstring(xml)

    ns = {
        "xmi": "http://schema.omg.org/spec/XMI/2.1",
        "uml": "http://schema.omg.org/spec/UML/2.0",
    }

    clases = []
    # 1)  Clases declaradas como <uml:Class …>
    for elem in root.findall(".//uml:Class", ns):
        nombre = elem.get("name", "Clase")
        atributos = [
            att.get("name")
            for att in elem.findall("./ownedAttribute", ns)
            if att.get("name")
        ]
        clases.append({"nombre": nombre, "atributos": atributos})

    # 2)  Clases declaradas con xmi:type="uml:Class" (por si la herramienta las suelta así)
    for elem in root.findall(".//*[@xmi:type='uml:Class']", ns):
        nombre = elem.get("name", "Clase")
        if nombre not in [c["nombre"] for c in clases]:    # evita duplicados
            atributos = [
                att.get("name")
                for att in elem.findall("./ownedAttribute", ns)
                if att.get("name")
            ]
            clases.append({"nombre": nombre, "atributos": atributos})

    return clases

ICONOS_SUGERIDOS = {
    "usuario": "user",
    "rol": "plus",
    "permiso": "cog",
    "producto": "folder",
    "sucursal": "home",
}
def icono_para(clase: str) -> str:
    return ICONOS_SUGERIDOS.get(clase.lower(), "folder")

faker = Faker("es_ES")

def fila_dummy(atributos):
    # Devuelve una lista del mismo largo con valores falsos
    vals = []
    for att in atributos:
        if 'id' in att.lower():
            vals.append(str(faker.random_int(1, 9999)))
        elif 'fecha' in att.lower():
            vals.append(faker.date())
        elif 'descripcion' in att.lower():
            vals.append(faker.sentence(nb_words=6))
        else:
            vals.append(faker.word())
    return vals
# -----------------------------------------------------
# Login estático tal cual tu JSON
TEMPLATE_LOGIN =  {
                        "id": "1745729450641",
                        "type": "login",
                        "x": 581.9572258528419,
                        "y": 139.3523736744362,
                        "width": 433,
                        "height": 388,
                        "styles": "",
                        "card": {
                            "id": "1745729450641-card",
                            "type": "card",
                            "x": 0,
                            "y": 0,
                            "width": 400,
                            "height": 600,
                            "styles": "p-6 flex flex-col items-center justify-center gap-4",
                            "backgroundColor": "#ffffff",
                            "borderRadius": "20px",
                            "padding": "1.5rem",
                            "shadow": True
                        },
                        "title": {
                            "id": "1745729450641-title",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 30,
                            "text": "Bienvenido a Te ayudo",
                            "styles": "text-2xl font-bold text-black"
                        },
                        "subtitle": {
                            "id": "1745729450641-subtitle",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 20,
                            "text": "Enter your email below to login to your account",
                            "styles": "text-gray-500 text-sm"
                        },
                        "emailInput": {
                            "id": "1745729450641-email",
                            "type": "input",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "border border-gray-300 bg-white rounded px-3 py-2 w-full",
                            "placeholder": "m@example.com",
                            "borderRadius": "0.375rem",
                            "value": ""
                        },
                        "passwordInput": {
                            "id": "1745729450641-password",
                            "type": "input",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "border border-gray-300 bg-white rounded px-3 py-2 w-full",
                            "placeholder": "",
                            "borderRadius": "0.375rem",
                            "value": ""
                        },
                        "loginButton": {
                            "id": "1745729450641-login-button",
                            "type": "button",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "bg-black text-white w-full py-2 rounded",
                            "label": "Login",
                            "backgroundColor": "#a855f7",
                            "borderRadius": "0.375rem",
                            "route": "31"
                        },
                        "googleButton": {
                            "id": "1745729450641-google-button",
                            "type": "button",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "bg-white text-black border border-gray-300 w-full py-2 rounded",
                            "label": "Login with Google",
                            "backgroundColor": "#ffffff",
                            "borderRadius": "0.375rem",
                            "route": "31"
                        },
                        "signupLink": {
                            "id": "1745729450641-signup",
                            "type": "label",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 20,
                            "text": "Don't have an account? Sign up",
                            "styles": "text-sm text-gray-600",
                            "route": "31"
                        }
                    }
  # ← pega aquí el bloque completo de la página Login
# Sidebar base (la estructura de “Usuarios”):
SIDEBAR_BASE = {
                        "id": "1745569520491",
                        "type": "sidebar",
                        "title": "Te Ayudo",
                        "x": -0.399993896484375,
                        "y": 0,
                        "width": 257,
                        "height": 729,
                        "styles": "bg-white shadow-lg p-4",
                        "asideBg": "#ffffff",
                        "mainColor": "#a855f7",
                        "sections": [
                            {
                                "icon": "user",
                                "label": "Usuarios",
                                "route": "31"
                            },
                            {
                                "icon": "plus",
                                "label": "Roles",
                                "route": "30"
                            },
                            {
                                "icon": "cog",
                                "label": "Permisos",
                                "route": "33"
                            },
                            {
                                "icon": "folder",
                                "label": "Productos",
                                "route": "34"
                            },
                            {
                                "icon": "home",
                                "label": "Sucursales",
                                "route": "35"
                            }
                        ],
                        "select": 0
            }
                    
# Header base (de “Usuarios”):
HEADER_BASE  =  {
                        "id": "1745701587012",
                        "type": "header",
                        "x": 254.69680712695413,
                        "y": 2.01019287110471e-05,
                        "width": 1282,
                        "height": 61,
                        "styles": "flex justify-between items-center p-4 border border-gray-300",
                        "backgroundColor": "#ffffff",
                        "sections": [
                            {
                                "label": "Te ayudo",
                                "route": "32"
                            },
                            {
                                "label": "Usuarios",
                                "route": "31"
                            }
                        ],
                        "buttons": [
                            {
                                "icon": "bell"
                            },
                            {
                                "icon": "user"
                            }
                        ],
                        "activeColor": "#a855f7"
            }

# Listar base (de “Usuarios”):
LISTAR_BASE  = {
                        "id": "1745649192323",
                        "type": "listar",
                        "x": 371.8843501003208,
                        "y": 162.06279010331542,
                        "width": 1050,
                        "height": 334,
                        "styles": "",
                        "button": {
                            "id": "1745649192323-btn",
                            "type": "button",
                            "label": "Agregar",
                            "x": 0,
                            "y": 0,
                            "width": 120,
                            "height": 40,
                            "styles": "bg-blue-600 text-white px-4 py-2 rounded",
                            "backgroundColor": "#a855f7"
                        },
                        "label": {
                            "id": "1745649192323-lbl",
                            "type": "label",
                            "text": "Todos los Usuarios",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 30,
                            "styles": "text-lg font-semibold text-black"
                        },
                        "search": {
                            "id": "1745649192323-search",
                            "type": "search",
                            "placeholder": "Buscar por nombre...",
                            "x": 0,
                            "y": 0,
                            "width": 250,
                            "height": 40,
                            "styles": "border-gray-300 rounded bg-white px-3 py-1"
                        },
                        "dataTable": {
                            "id": "1745649192323-table",
                            "type": "datatable",
                            "x": 0,
                            "y": 0,
                            "width": 1000,
                            "height": 200,
                            "styles": "",
                            "headers": [
                                "Id",
                                "Nombre",
                                "Descripción",
                                "Fecha de creación",
                                "Estado"
                            ],
                            "backgroundColor": "#ffffff",
                            "rows": [
                                [
                                    "1",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "2",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "3",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ],
                                [
                                    "4",
                                    "Proyecto Interfaces",
                                    "Este proyecto será para construir interfaces dinámicas...",
                                    "15 abr 2025",
                                    "En proceso"
                                ]
                            ]
                        },
                        "pagination": {
                            "id": "1745649192323-pg",
                            "type": "pagination",
                            "x": 0,
                            "y": 0,
                            "width": 300,
                            "height": 40,
                            "styles": "text-black",
                            "currentPage": 1,
                            "totalPages": 5
                        },
                        "dialog": {
                            "id": "1745649192323-dialog",
                            "type": "dialog",
                            "x": 0,
                            "y": 0,
                            "width": 400,
                            "height": 500,
                            "styles": "",
                            "title": "Agregar nuevo proyecto",
                            "fields": [
                                {
                                    "label": "Id",
                                    "type": {
                                        "id": "1745649192323-input-Id",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese id",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Nombre",
                                    "type": {
                                        "id": "1745649192323-input-Nombre",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese nombre",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Descripción",
                                    "type": {
                                        "id": "1745649192323-input-Descripción",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese descripción",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Fecha de creación",
                                    "type": {
                                        "id": "1745649192323-input-Fecha de creación",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese fecha de creación",
                                        "value": ""
                                    }
                                },
                                {
                                    "label": "Estado",
                                    "type": {
                                        "id": "1745649192323-input-Estado",
                                        "type": "input",
                                        "x": 0,
                                        "y": 0,
                                        "width": 300,
                                        "height": 40,
                                        "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                                        "placeholder": "Ingrese estado",
                                        "value": ""
                                    }
                                }
                            ]
                        },
                        "size": {
                            "width": None
                        }
                }

import copy, time

def page_para_clase(clase: dict, secciones_sidebar: list, idx_sel: int, order: int) -> dict:
    ts = int(time.time()*1000)
    nombre = clase['nombre'].capitalize()

    # --- Sidebar ---
    sidebar = copy.deepcopy(SIDEBAR_BASE)
    sidebar['id'] = f"{ts}-sb"
    sidebar['select'] = idx_sel
    sidebar['sections'] = secciones_sidebar   # mismas secciones para todas

    # --- Header --- 
    header = copy.deepcopy(HEADER_BASE)
    header['id'] = f"{ts}-hdr"
    header['sections'][1]['label'] = nombre   # migaja actual
    header['sections'][1]['route'] = str(order)  # id de página
    header['activeColor'] = "#a855f7"

    # --- Listar / DataTable ---
    listar = copy.deepcopy(LISTAR_BASE)
    listar['id'] = f"{ts}-lst"
    listar['label']['text'] = f"Todos los {nombre}"
    listar['button']['backgroundColor'] = "#a855f7"
    listar['dialog']['title'] = f"Agregar nuevo {nombre.lower()}"

    # headers = atributos
    listar['dataTable']['headers'] = clase['atributos']

    # filas dummy
    filas = [fila_dummy(clase['atributos']) for _ in range(4)]
    listar['dataTable']['rows'] = filas

    # también replica los fields del diálogo
    listar['dialog']['fields'] = [
        {
            "label": att,
            "type": {
                "id": f"{ts}-{att}",
                "type": "input",
                "x": 0, "y": 0, "width": 300, "height": 40,
                "styles": "border border-gray-300 bg-white rounded px-2 py-1",
                "placeholder": f"Ingrese {att.lower()}",
                "value": ""
            }
        } for att in clase['atributos']
    ]

    # --- Página completa ---
    return  {
        "id": order,              # o autogenerado en BD
        "name": nombre,
        "order": order,
        "background_color": "#ffffff",
        "grid_enabled": False,
        "device_mode": "desktop",
        "components": [sidebar, listar, header]
    }

def generar_pages_desde_xml(xml: bytes) -> list[dict]:
    clases = extraer_clases(xml)
    print("Clases extraídas del XML:", clases)
    # 1️⃣ Login siempre primero
    pages = [{
        "id": 1,  # id autogenerado ficticio
        "name": "Login",
        "order": 1,
        "background_color": "#ffffff",
        "grid_enabled": False,
        "device_mode": "desktop",
        "components": [copy.deepcopy(TEMPLATE_LOGIN)]  # Aquí lo corregimos
    }]

    # 2️⃣ Construir secciones únicas para TODO el sidebar
    secciones_sidebar = [
        {
            "icon": icono_para(cls['nombre']),
            "label": cls['nombre'].capitalize(),
            "route": str(i+2)   # +2 porque 1 es Login
        }
        for i, cls in enumerate(clases)
    ]

    # 3️⃣ Una página por clase
    for i, cls in enumerate(clases, start=2):
        pages.append(
            page_para_clase(cls, secciones_sidebar, idx_sel=i-2, order=i)
        )

    return pages

def set_routes_sidebar(pg, name_to_id):
    comps = copy.deepcopy(pg.components)          # ← copia
    changed = False
    for comp in comps:
        if comp.get('type') == 'sidebar':
            for sec in comp['sections']:
                dest = name_to_id.get(sec['label'].lower())
                if dest and sec['route'] != str(dest):
                    sec['route'] = str(dest)
                    changed = True
    if changed:
        pg.components = comps    # ← re-asignación marca sucio
    return changed

def set_login_buttons(login_pg, id_segunda):
    comps = copy.deepcopy(login_pg.components)
    for comp in comps:
        if comp.get('type') == 'login':
            for _, sub in comp.items():
                if isinstance(sub, dict) and sub.get('type') == 'button':
                    sub['route'] = str(id_segunda)
    login_pg.components = comps   # ← re-asignación
COMPONENTES = ["button","input","sidebar","label","datatable","header"]

def normaliza(txt):
    t = unicodedata.normalize("NFKD", txt).encode("ascii","ignore").decode()
    return t.lower().strip()

def match_tipo(txt):
    txt = normaliza(txt)
    candidato = difflib.get_close_matches(txt, COMPONENTES, n=1, cutoff=0.6)
    return candidato[0] if candidato else "unknown"

def detectar_componentes_desde_imagen(b: bytes) -> list[dict]:
    nparr = np.frombuffer(b, np.uint8)
    img   = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    gray  = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur  = cv2.GaussianBlur(gray, (5,5), 0)
    edges = cv2.Canny(blur, 50, 150)

    conts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    componentes = []
    for cnt in conts:
        x,y,w,h = cv2.boundingRect(cnt)
        if w*h < 2000:                    # descarta ruido
            continue

        roi = gray[y:y+h, x:x+w]
        txt = pytesseract.image_to_string(roi, config="--psm 7").strip()
        tipo = match_tipo(txt)

        comp_id = str(uuid.uuid4().int>>100)     # id numérico corto
        base = {"id": comp_id, "x": x, "y": y, "width": w, "height": h}

        if   tipo == "button":
            componentes.append({**base, "type":"button", "label":"Botón", "styles":"flex items-center bg-blue justify-center w-full h-full text-white"})
        elif tipo == "input":
            componentes.append({**base, "type":"input", "placeholder":"..."})
        elif tipo == "label":
            componentes.append({**base, "type":"label", "text":"Texto"})
        elif tipo == "sidebar":
            componentes.append({**base, "type":"sidebar", "title":"Sidebar", "sections":[]})
        elif tipo == "datatable":
            componentes.append({**base, "type":"datatable", "headers":["Id","Nombre"], "rows":[]})
        elif tipo == "header":
            componentes.append({**base, "type":"header", "sections":[], "buttons":[]})
        else:
            # opcional: ignorar u ordenar como 'label'
            pass

    # opcional: ordenar por y para una mejor topología
    componentes.sort(key=lambda c: (c["y"], c["x"]))
    return componentes
@router.post("/", response_model=Proyecto)
def crear_proyecto(
    name: str = Form(...),
    descripcion: str = Form(...),
    colaboradorId: Optional[str] = Form(None),  # Opción: lo recibimos como string tipo '12,13'
    archivo_xml: UploadFile = File(None),
    imagen_boceto: UploadFile = File(None), 
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    nuevo_proyecto = ProyectoModel(
        name=name,
        descripcion=descripcion,
        status="En proceso",
        owner_id=current_user.id,
        create_date=datetime.utcnow(),
        pages=[]  # inicialmente vacío
    )
    db.add(nuevo_proyecto)
    db.commit()
    db.refresh(nuevo_proyecto)
    
    if archivo_xml:
        xml_bytes = archivo_xml.file.read()
        listado_pages = generar_pages_desde_xml(xml_bytes)

        pages_temp: list[Page] = []

        # 1️⃣ Insertamos todas las páginas y llenamos pages_temp
        for p_dict in listado_pages:
            page_obj = Page(
                name=p_dict['name'],
                order=p_dict['order'],
                proyecto_id=nuevo_proyecto.id,
                components=p_dict['components']
            )
            db.add(page_obj)
            pages_temp.append(page_obj)

        db.flush()          

        # 2️⃣ Creamos mapa nombre → id
        name_to_id = {p.name.lower(): p.id for p in pages_temp}

        # 3️⃣ Botones del Login  → id segunda página
        if len(pages_temp) >= 2:
            set_login_buttons(pages_temp[0], pages_temp[1].id)

        # 4️⃣ Sidebars → id real de la página correspondiente
        for pg in pages_temp:
            set_routes_sidebar(pg, name_to_id)

        db.commit() 
    elif imagen_boceto:
        bytes_img = imagen_boceto.file.read()
        componentes = detectar_componentes_desde_imagen(bytes_img)  # 👈 tu función OCR + CV

        pagina_diseñada = Page(
            name="Página generada",
            order=1,
            proyecto_id=nuevo_proyecto.id,
            components=componentes
        )
        db.add(pagina_diseñada)
        db.commit()
        db.refresh(pagina_diseñada)
    else:
        pagina_inicial = Page(
            name="Página 1",
            order=1,
            proyecto_id=nuevo_proyecto.id,
            components=[]  # JSON vacío
        )
        db.add(pagina_inicial)
        db.commit()
        db.refresh(pagina_inicial)

    if colaboradorId:
        for colaborador_id in colaboradorId:
            relacion = ColaboradorProyecto(
                usuario_id=colaborador_id,
                proyecto_id=nuevo_proyecto.id,
                permisos="ver"  # por defecto, luego puedes asignar permisos específicos
            )
            db.add(relacion)
        db.commit()

    return nuevo_proyecto

@router.get("/", response_model=ProyectoListResponse)
def listar_proyectos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.is_main:
        # Usuario es administrador: proyectos que creó
        proyectos = db.query(ProyectoModel).filter_by(owner_id=current_user.id).all()
    else:
        # Usuario es colaborador: proyectos donde fue asignado
        proyectos = (
            db.query(ProyectoModel)
            .join(ColaboradorProyecto, ColaboradorProyecto.proyecto_id == ProyectoModel.id)
            .filter(ColaboradorProyecto.usuario_id == current_user.id)
            .all()
        )

    return {
        "data": proyectos,
        "countData": len(proyectos)
    }

@router.get("/last-worked", response_model=ProyectoResponse)
def obtener_ultimo_proyecto(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. proyectos donde es owner
    owner_q = db.query(ProyectoModel).filter(
        ProyectoModel.owner_id == current_user.id
    )
    print("Owner Query:", owner_q)
    # 2. proyectos donde es colaborador
    colaborador_q = (
        db.query(ProyectoModel)
        .join(ColaboradorProyecto,
              ColaboradorProyecto.proyecto_id == ProyectoModel.id)
        .filter(ColaboradorProyecto.usuario_id == current_user.id)
    )

    print("Colaborador Query:", colaborador_q)
    # 3. UNION ALL y ordenamos por last_modified
    ultimo = (
        owner_q.union_all(colaborador_q)
               .order_by(desc(ProyectoModel.last_modified))
               .limit(1)
               .first()
    )

    if not ultimo:
        raise HTTPException(404, "No tienes proyectos todavía")

    return {
        "data": ultimo,
    }

@router.get("/{proyecto_id}", response_model=ProyectoResponse)
def obtener_proyecto_por_id(
    proyecto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Buscar el proyecto donde sea owner
    proyecto = db.query(ProyectoModel).filter_by(id=proyecto_id, owner_id=current_user.id).first()

    if not proyecto:
        # Si no es owner, buscamos si es colaborador
        proyecto = (
            db.query(ProyectoModel)
            .join(ColaboradorProyecto, ColaboradorProyecto.proyecto_id == ProyectoModel.id)
            .filter(
                ColaboradorProyecto.usuario_id == current_user.id,
                ProyectoModel.id == proyecto_id
            )
            .first()
        )

    if not proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado o no tienes acceso")

    return {
        "data": proyecto
    }

@router.put("/", response_model=ProyectoResponse)
def actualizar_proyecto(
    data: ProyectoUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. ─────────── obtener proyecto y validar propietario
    proyecto = (
        db.query(ProyectoModel)
          .filter(ProyectoModel.id == data.id)
          .first()
    )
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")
    if proyecto.owner_id != current_user.id:
        raise HTTPException(403, "No autorizado")

    # 2. ─────────── actualizar campos simples del proyecto
    for campo in ("name", "descripcion", "status", "last_modified"):
        nuevo_valor = getattr(data, campo, None)
        if nuevo_valor is not None:
            setattr(proyecto, campo, nuevo_valor)

    # 3. ─────────── procesar cada página recibida
    #    usamos un dicc para saber cuáles páginas ya estaban
    existentes = {p.id: p for p in proyecto.pages}

    for pagina_in in data.pages:
        # 3.a ── UPDATE de página existente
        if pagina_in.id:
            page_obj = existentes.get(pagina_in.id)
            if not page_obj:
                raise HTTPException(
                    400,
                    f"Página con id {pagina_in.id} no pertenece al proyecto",
                )
        # 3.b ── INSERT de una nueva página
        else:
            page_obj = Page(proyecto_id=proyecto.id)
            db.add(page_obj)

        # Actualizamos campos de la página
        for campo in (
            "name",
            "order",
            "background_color",
            "grid_enabled",
            "device_mode",
            "components",
        ):
            nuevo_valor = getattr(pagina_in, campo, None)
            if nuevo_valor is not None:
                setattr(page_obj, campo, nuevo_valor)

    # 4. ─────────── commit (esto disparará el `onupdate` y refrescará last_modified)
    db.commit()
    db.refresh(proyecto)

    return {"data": proyecto}

@router.post(
    "/{project_id}/pages",
    response_model=PageResponse,   # ahora sí coincide con lo que devolvemos
    status_code=201
)
def crear_pagina_en_proyecto(
    project_id: int,
    page_in: PageCreateIn,         # ⬅ sin Depends()
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # 1. Verificar proyecto
    proyecto = (
        db.query(ProyectoModel)
          .filter(ProyectoModel.id == project_id)
          .first()
    )
    if not proyecto:
        raise HTTPException(404, "Proyecto no encontrado")

    # (opcional) validar permisos…

    # 2. Calcular order y nombre por defecto
    total_pages  = db.query(func.count(Page.id))\
                     .filter(Page.proyecto_id == project_id).scalar()
    nuevo_order  = (total_pages or 0) + 1
    nombre_def   = f"Página {nuevo_order}"

    nueva_pagina = Page(
        name             = page_in.name  or nombre_def,
        order            = page_in.order if page_in.order is not None else nuevo_order,
        background_color = page_in.background_color,
        grid_enabled     = page_in.grid_enabled,
        device_mode      = page_in.device_mode,
        components       = page_in.components,
        proyecto_id      = project_id
    )

    db.add(nueva_pagina)

    # 3. Actualizar timestamp del proyecto
    proyecto.last_modified = datetime.utcnow()

    db.commit()
    db.refresh(nueva_pagina)

    # 4. Devolver SOLO la página creada en el envoltorio `data`
    return {"data": nueva_pagina}

def slugify(text: str) -> str:
    """‘Página X’ → 'pagina-x'  (ASCII, minúsculas, guiones)"""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_]+", "-", text)

def pascal_from_slug(slug: str) -> str:
    """'pagina-x' → 'PaginaXComponent'"""
    return "".join(word.capitalize() for word in slug.split("-")) + "Component"

@router.get("/{project_id}/download")
def descargar_proyecto_angular(
    project_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    # Obtener el proyecto
    proyecto = db.query(ProyectoModel).filter_by(id=project_id).first()
    if not proyecto:
        raise HTTPException(404, detail="Proyecto no encontrado")

    # Crear carpeta temporal del proyecto
    carpeta_proyecto = os.path.join(TEMP_DIR, f"frontend_{proyecto.name}_{int(datetime.utcnow().timestamp())}")
    os.makedirs(carpeta_proyecto, exist_ok=True)

    # Crear estructura de carpetas
    src_dir = os.path.join(carpeta_proyecto, "src")
    app_dir = os.path.join(src_dir, "app")
    os.makedirs(app_dir, exist_ok=True)
    # ARCHIVOS DE BASE============================
    angular_json = {
        "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
        "version": 1,
        "newProjectRoot": "projects",
        "projects": {
            "frontend-generated": {
                "projectType": "application",
                "schematics": {},
                "root": "",
                "sourceRoot": "src",
                "prefix": "app",
                "architect": {
                    "build": {
                        "builder": "@angular-devkit/build-angular:browser",
                        "options": {
                            "outputPath": "dist/frontend-generated",
                            "index": "src/index.html",
                            "main": "src/main.ts",
                            "polyfills": [
                                "zone.js"
                            ],
                            "tsConfig": "tsconfig.app.json",
                            "assets": [
                                "src/assets"
                            ],
                            "styles": [
                                "src/styles.css",
                                "node_modules/@fortawesome/fontawesome-free/css/all.min.css"
                            ],
                            "scripts": []
                        },
                        "configurations": {
                            "production": {
                                "budgets": [
                                    {
                                        "type": "initial",
                                        "maximumWarning": "500kb",
                                        "maximumError": "1mb"
                                    },
                                    {
                                        "type": "anyComponentStyle",
                                        "maximumWarning": "2kb",
                                        "maximumError": "4kb"
                                    }
                                ],
                                "outputHashing": "all"
                            },
                            "development": {
                                "buildOptimizer": False,
                                "optimization": False,
                                "vendorChunk": True,
                                "extractLicenses": False,
                                "sourceMap": True,
                                "namedChunks": True
                            }
                        },
                        "defaultConfiguration": "production"
                    },
                    "serve": {
                        "builder": "@angular-devkit/build-angular:dev-server",
                        "configurations": {
                            "production": {
                                "browserTarget": "frontend-generated:build:production"
                            },
                            "development": {
                                "browserTarget": "frontend-generated:build:development"
                            }
                        },
                        "defaultConfiguration": "development"
                    },
                    "extract-i18n": {
                        "builder": "@angular-devkit/build-angular:extract-i18n",
                        "options": {
                            "browserTarget": "frontend-generated:build"
                        }
                    },
                    "test": {
                        "builder": "@angular-devkit/build-angular:karma",
                        "options": {
                            "polyfills": [
                                "zone.js",
                                "zone.js/testing"
                            ],
                            "tsConfig": "tsconfig.spec.json",
                            "assets": [
                                "src/assets"
                            ],
                            "styles": [
                                "src/styles.css"
                            ],
                            "scripts": []
                        }
                    }
                }
            }
        },
        "cli": {
            "analytics": "2a5fc0bd-8d8a-4d70-ac2b-eb35e5298fae"
        },  
    }
    with open(os.path.join(carpeta_proyecto, "angular.json"), "w",
            encoding="utf-8") as f:
        json.dump(angular_json, f, indent=2)

    # Crear package.json
    package_json = {
        "name": "frontend-generated",
        "version": "0.0.0",
        "scripts": {
            "ng": "ng",
            "start": "ng serve",
            "build": "ng build",
            "watch": "ng build --watch --configuration development",
            "test": "ng test"
        },
        "private": True,
        "dependencies": {
            "@angular/animations": "^16.2.0",
            "@angular/common": "^16.2.0",
            "@angular/compiler": "^16.2.0",
            "@angular/core": "^16.2.0",
            "@angular/forms": "^16.2.0",
            "@angular/platform-browser": "^16.2.0",
            "@angular/platform-browser-dynamic": "^16.2.0",
            "@angular/router": "^16.2.0",
            "@fortawesome/fontawesome-free": "^6.4.0",
            "angular-rutas-tailwind": "file:",
            "rxjs": "~7.8.0",
            "tslib": "^2.3.0",
            "zone.js": "~0.13.0"
        },
        "devDependencies": {
            "@angular-devkit/build-angular": "^16.2.16",
            "@angular/cli": "^16.2.16",
            "@angular/compiler-cli": "^16.2.0",
            "@types/jasmine": "~4.3.0",
            "autoprefixer": "^10.4.21",
            "jasmine-core": "~4.6.0",
            "karma": "~6.4.0",
            "karma-chrome-launcher": "~3.2.0",
            "karma-coverage": "~2.2.0",
            "karma-jasmine": "~5.1.0",
            "karma-jasmine-html-reporter": "~2.1.0",
            "postcss": "^8.5.3",
            "tailwindcss": "^3.4.17",
            "typescript": "~5.1.3"
        }
    }
    with open(os.path.join(carpeta_proyecto, "package.json"), "w", encoding="utf-8") as f:
        json.dump(package_json, f, indent=2)

    # Crear tailwind.config.js
    tailwind_config = """\
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
"""

    with open(os.path.join(carpeta_proyecto, "tailwind.config.js"), "w", encoding="utf-8") as f:
        f.write(tailwind_config)

    # Crear tsconfig.app.json
    tsconfig_app = """\
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": [
    "src/main.ts"
  ],
  "include": [
    "src/**/*.d.ts"
  ]
}
"""

    with open(os.path.join(carpeta_proyecto, "tsconfig.app.json"), "w", encoding="utf-8") as f:
        f.write(tsconfig_app)

    # Crear tsconfig.json
    tsconfig_json = """\
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "compileOnSave": false,
  "compilerOptions": {
    "baseUrl": "./",
    "outDir": "./dist/out-tsc",
    "forceConsistentCasingInFileNames": true,
    "strict": true,
    "noImplicitOverride": true,
    "noPropertyAccessFromIndexSignature": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "sourceMap": true,
    "declaration": false,
    "downlevelIteration": true,
    "experimentalDecorators": true,
    "moduleResolution": "node",
    "importHelpers": true,
    "target": "ES2022",
    "module": "ES2022",
    "useDefineForClassFields": false,
    "lib": [
      "ES2022",
      "dom"
    ]
  },
  "angularCompilerOptions": {
    "enableI18nLegacyMessageIdFormat": false,
    "strictInjectionParameters": true,
    "strictInputAccessModifiers": true,
    "strictTemplates": true
  }
}
"""

    with open(os.path.join(carpeta_proyecto, "tsconfig.json"), "w", encoding="utf-8") as f:
        f.write(tsconfig_json)

    # Crear tsconfig.spec.json
    tsconfig_spec = """\
/* To learn more about this file see: https://angular.io/config/tsconfig. */
{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/spec",
    "types": [
      "jasmine"
    ]
  },
  "include": [
    "src/**/*.spec.ts",
    "src/**/*.d.ts"
  ]
}
"""
    with open(os.path.join(carpeta_proyecto, "tsconfig.spec.json"), "w", encoding="utf-8") as f:
        f.write(tsconfig_spec)
    
    editorconfig = """\
# Editor configuration, see https://editorconfig.org
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 2
insert_final_newline = true
trim_trailing_whitespace = true

[*.ts]
quote_type = single

[*.md]
max_line_length = off
trim_trailing_whitespace = false
"""

    with open(os.path.join(carpeta_proyecto, ".editorconfig"), "w", encoding="utf-8") as f:
        f.write(editorconfig)
#====================================================
#CREACION DE ARCHIVOS DE SRC BASE====================
    # Crear index.html
    index_html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AngularRutasTailwind</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <app-root></app-root>
</body>
</html>
"""

    with open(os.path.join(src_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Crear main.ts
    main_ts = """import { platformBrowserDynamic } from '@angular/platform-browser-dynamic';

import { AppModule } from './app/app.module';

platformBrowserDynamic().bootstrapModule(AppModule)
  .catch(err => console.error(err));
"""

    with open(os.path.join(src_dir, "main.ts"), "w", encoding="utf-8") as f:
        f.write(main_ts)

    # Crear styles.css
    styles_css = """/* You can add global styles to this file, and also import other style files */
@tailwind base;
@tailwind components;
@tailwind utilities;
body{
    background-color: #d9d9d9;
}
"""

    with open(os.path.join(src_dir, "styles.css"), "w", encoding="utf-8") as f:
        f.write(styles_css)
# ==========================================

    # Crear run.bat
    run_bat = """
@echo off
echo Instalando dependencias...
REM Evita conflictos de peer‑deps
npm install --legacy-peer-deps

echo Iniciando servidor de desarrollo...
npm run start
"""
    with open(os.path.join(carpeta_proyecto, "run.bat"), "w", encoding="utf-8") as f:
        f.write(run_bat)

# Crear componentes en src/app ==========================
    component_info = []
    routes = []  # Para almacenar las rutas de las páginas
    for idx, page in enumerate(sorted(proyecto.pages, key=lambda p: p.order), start=1):
        slug = slugify(page.name)
        cls = pascal_from_slug(slug)

        # Evitar duplicados
        if any(s == slug for _, s in component_info):
            slug = f"{slug}-{idx}"
            cls = pascal_from_slug(slug)

        component_info.append((cls, slug))

        folder = os.path.join(app_dir, slug)
        os.makedirs(folder, exist_ok=True)

        # Crear archivos del componente
        needs_sidebar = False
        needs_listar = False
        listar_rows = []
        listar_title = ""
        listar_fields = []
        # Generar el contenido del archivo HTML
        html_content = ""
        for component in page.components:
            style = (
                f"position: absolute;"
                f"left: {component['x']}px;"
                f"top: {component['y']}px;"
                f"width: {component['width']}px;"
                f"height: {component['height']}px;"
            )

            if "backgroundColor" in component:
                style += f"background-color: {component['backgroundColor']};"
            if "borderRadius" in component:
                style += f"border-radius: {component['borderRadius']};"

            tailwind_classes = component.get("styles", "")

            if component["type"] == "button":
                dest = f"'/page-{component['route']}'" if "route" in component else "'/'"
                html_content += f'''
        <button
        class="{tailwind_classes}"
        style="{style}"
        [routerLink]="{dest}">
        {component.get('label', 'Button')}
        </button>
        '''
            elif component["type"] == "input":
                html_content += f'''
        <input
        class="{tailwind_classes}"
        style="{style}"
        placeholder="{component.get('placeholder', '')}">
        '''
            elif component["type"] == "sidebar":
                needs_sidebar = True
                title = component.get("title", "UI SKETCH")
                title_icon = component.get("titleIcon", "star")
                main_color = component.get("mainColor", "#a855f7")
                aside_bg = component.get("asideBg", "#ffffff")
                height = component.get("height", 600)
                sections = component.get("sections", [])
                select = component.get("select", 0)
                
                section_items = ""
                for idx, sec in enumerate(sections):
                    section_bg = f"background-color: {main_color}20;" if idx == select else ""
                    section_color = f"color: {main_color};" if idx == select else ""
                    dest = f"/page-{sec.get('route', '')}"
                    section_items += f'''
                    <button class="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-gray-100 transition w-full text-left"
                        [routerLink]="['{dest}']"
                        style="{section_bg} {section_color}">
                        <i class="fa fa-{sec.get('icon', 'star')} text-base"></i>
                        <span>{sec.get('label', '')}</span>
                    </button>
                    '''

                html_content += f'''
                <div style="position:absolute; left:{component['x']}px; top:{component['y']}px; width:{component['width']}px; height:{height}px;">
                <aside [ngClass]="isSidebarOpen ? 'w-64' : 'w-[3.14rem]'" style="background-color:{aside_bg}; height:100%;" class="h-full flex flex-col border-r transition-all duration-300 ease-in-out">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-4 py-3 border-b">
                    <div class="flex items-center gap-2">
                        <i class="fa fa-{title_icon} text-xl" style="color:{main_color};"></i>
                        <h1 class="text-lg font-bold text-black truncate">{title}</h1>
                    </div>
                    <button class="p-1 rounded hover:bg-gray-100 transition" title="Toggle" (click)="toggleSidebar()">
                        <i class="fa" [ngClass]="isSidebarOpen ? 'fa-angle-double-left' : 'fa-bars'" style="color:{main_color};"></i>
                    </button>
                    </div>

                    <!-- Secciones -->
                    <nav class="flex-1 overflow-y-auto p-4 text-black space-y-2 text-sm">
                    {section_items}
                    </nav>

                    <!-- Footer -->
                    <div class="p-4 border-t">
                    <button class="w-full flex items-center justify-center gap-2 py-2 rounded hover:opacity-90"
                            style="background-color:{main_color}; color:white;">
                        <i class="fa fa-gear"></i> Configuración
                    </button>
                    </div>
                </aside>
                </div>
                '''
            elif component["type"] == "datatable":
                headers = component.get("headers", [])
                rows = component.get("rows", [])
                bg_color = component.get("backgroundColor", "#ffffff")

                style = (
                    f"position: absolute;"
                    f"left: {component['x']}px;"
                    f"top: {component['y']}px;"
                    f"width: {component['width']}px;"
                    f"height: {component['height']}px;"
                    f"background-color: {bg_color};"
                )

                headers_html = "".join([f'<th class="px-4 py-3">{header}</th>' for header in headers])

                rows_html = ""
                for row in rows:
                    cells = "".join([f'<td class="px-4 py-3">{cell}</td>' for cell in row])
                    row_html = f"""
                    <tr class="hover:bg-gray-50 border-b-gray-200 border-2 transition">
                        {cells}
                        <td class="relative px-4 py-3 text-right">
                            <button class="text-gray-500 hover:text-gray-700">
                                <i class="fa fa-ellipsis-v"></i>
                            </button>
                        </td>
                    </tr>
                    """
                    rows_html += row_html

                html_content += f"""
                <div style="{style}" class="overflow-x-auto rounded-lg border border-gray-200 h-full shadow-sm">
                <table class="min-w-full divide-y divide-gray-200 text-sm text-left text-gray-800">
                    <thead class="bg-gray-100 text-xs font-semibold uppercase text-gray-600">
                    <tr>
                        {headers_html}
                        <th class="px-4 py-3 text-right">...</th>
                    </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-200">
                    {rows_html}
                    </tbody>
                </table>
                </div>
                """
            elif component["type"] == "header":
                # Extraer propiedades principales
                x = component["x"]
                y = component["y"]
                width = component["width"]
                height = component["height"]
                styles = component.get("styles", "flex justify-between items-center p-4 border border-gray-300")
                background_color = component.get("backgroundColor", "#ffffff")
                active_color = component.get("activeColor", "#3b82f6")
                sections = component.get("sections", [])
                buttons = component.get("buttons", [])

                # Generar HTML para las secciones (breadcrumb)
                sections_html = ""
                for idx, section in enumerate(sections):
                    section_color = active_color if idx == len(sections) - 1 else "#6b7280"
                    font_weight = "font-bold" if idx == len(sections) - 1 else "font-normal"
                    separator = '<span class="mx-2 text-gray-500">&gt;</span>' if idx < len(sections) - 1 else ""
                    sections_html += f'''
                    <div class="flex items-center">
                        <a
                            [routerLink]="['/page-{section.get('route', '')}']"
                            class="hover:underline {font_weight}"
                            style="color: {section_color};"
                        >
                            {section.get('label', '')}
                        </a>
                        {separator}
                    </div>
                    '''

                # Generar HTML para los botones (iconos a la derecha)
                buttons_html = ""
                for button in buttons:
                    icon = button.get("icon", "star")
                    buttons_html += f'''
                    <button class="relative w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center hover:bg-slate-100">
                        <i class="fa fa-{icon} text-black"></i>
                    </button>
                    '''

                # Armar el componente completo
                html_content += f'''
                <div style="position:absolute; left:{x}px; top:{y}px; width:{width}px; height:{height}px;">
                    <div class="{styles}" style="background-color:{background_color}; width:100%; height:100%; padding:1rem;">
                        <div class="flex items-center space-x-2 text-sm">
                            {sections_html}
                        </div>
                        <div class="flex items-center space-x-4 ml-auto">
                            {buttons_html}
                        </div>
                    </div>
                </div>
                '''
            elif component["type"] == "login":
                # Extraer datos principales
                x = component["x"]
                y = component["y"]
                width = component["width"]
                height = component["height"]
                styles = component.get("styles", "")
                
                # Extraer componentes internos
                card = component.get("card", {})
                title = component.get("title", {})
                subtitle = component.get("subtitle", {})
                email_input = component.get("emailInput", {})
                password_input = component.get("passwordInput", {})
                login_button = component.get("loginButton", {})
                google_button = component.get("googleButton", {})
                signup_link = component.get("signupLink", {})

                card_background = card.get("backgroundColor", "#ffffff")
                card_border_radius = card.get("borderRadius", "0.5rem")
                card_padding = card.get("padding", "1.5rem")
                card_shadow = "shadow-lg" if card.get("shadow", False) else ""

                # Armamos el HTML
                html_content += f'''
                <div style="position:absolute; left:{x}px; top:{y}px; width:{width}px; height:{height}px;" class="{styles}">
                <div class="{card.get('styles', '')} {card_shadow}" 
                    style="background-color:{card_background}; border-radius:{card_border_radius}; width:100%; height:100%; padding:{card_padding}; display:flex; flex-direction:column; align-items:center; justify-content:center;">
                    
                    <!-- Title -->
                    <h1 class="{title.get('styles', '')}">
                    {title.get('text', 'Bienvenido')}
                    </h1>

                    <!-- Subtitle -->
                    <p class="{subtitle.get('styles', '')}">
                    {subtitle.get('text', '')}
                    </p>

                    <!-- Email Input -->
                    <input
                    class="{email_input.get('styles', '')}"
                    style="width:100%;"
                    type="email"
                    placeholder="{email_input.get('placeholder', 'Email')}"
                    value="{email_input.get('value', '')}"
                    readonly
                    />

                    <!-- Password Input -->
                    <input
                    class="{password_input.get('styles', '')}"
                    style="width:100%;"
                    type="password"
                    placeholder="Password"
                    value="{password_input.get('value', '')}"
                    readonly
                    />

                    <!-- Botón de Login -->
                    <button
                    class="{login_button.get('styles', '')}"
                    style="background-color:{login_button.get('backgroundColor', '#000000')}; border-radius:{login_button.get('borderRadius', '0.375rem')};"
                    >
                    {login_button.get('label', 'Login')}
                    </button>

                    <!-- Botón de Google -->
                    <button
                    class="{google_button.get('styles', '')}"
                    style="background-color:{google_button.get('backgroundColor', '#ffffff')}; border-radius:{google_button.get('borderRadius', '0.375rem')}; border:1px solid #e5e7eb;"
                    [routerLink]="['/page-{google_button.get('route', '')}']"
                    >
                    {google_button.get('label', 'Login with Google')}
                    </button>

                    <!-- Link de Sign up -->
                    <p class="{signup_link.get('styles', '')}">
                    {signup_link.get('text', '')}
                    </p>

                </div>
                </div>
                '''
            elif component["type"] == "select":
                style = (
                    f"position: absolute;"
                    f"left: {component['x']}px;"
                    f"top: {component['y']}px;"
                    f"width: {component['width']}px;"
                    f"height: {component['height']}px;"
                    f"background-color: {component.get('backgroundColor', '#ffffff')};"
                )
                options = component.get("options", [])
                value = component.get("value", "")

                options_html = "\n".join([
                    f'<option value="{opt}" {"selected" if opt == value else ""}>{opt}</option>'
                    for opt in options
                ])

                html_content += f"""
                <select
                    class="{tailwind_classes}"
                    style="{style}">
                    {options_html}
                </select>
                """
            elif component["type"] == "radiobutton":
                style = (
                    f"position: absolute;"
                    f"left: {component['x']}px;"
                    f"top: {component['y']}px;"
                    f"width: {component['width']}px;"
                    f"height: {component['height']}px;"
                )
                options = component.get("options", [])
                selected = component.get("selected", "")
                name = component.get("name", f"radio-{component['id']}")

                radio_items = "\n".join([
                    f'''
                    <label class="flex items-center gap-2">
                        <input type="radio" name="{name}" value="{opt}" {"checked" if opt == selected else ""} />
                        <span>{opt}</span>
                    </label>
                    ''' for opt in options
                ])

                html_content += f"""
                <div class="{tailwind_classes}" style="{style}">
                    {radio_items}
                </div>
                """
            elif component["type"] == "checklist":
                style = (
                    f"position: absolute;"
                    f"left: {component['x']}px;"
                    f"top: {component['y']}px;"
                    f"width: {component['width']}px;"
                    f"height: {component['height']}px;"
                )
                title = component.get("title", "")
                items = component.get("items", [])

                checklist_items = "\n".join([
                    f'''
                    <li class="flex items-center gap-2">
                        <input type="checkbox" {"checked" if item['checked'] else ""} />
                        <span class="{ 'line-through text-gray-500' if item['checked'] else '' }">{item['label']}</span>
                    </li>
                    ''' for item in items
                ])

                html_content += f"""
                <div class="{tailwind_classes}" style="{style}">
                    <h3 class="font-semibold text-lg mb-2">{title}</h3>
                    <ul class="space-y-1">
                        {checklist_items}
                    </ul>
                </div>
                """
            elif component["type"] == "listar":
                needs_listar = True
                listar_rows = component["dataTable"]["rows"]
                listar_title = component["dialog"]["title"]
                listar_fields = component["dialog"]["fields"]
                bg_data = component["dataTable"]["backgroundColor"]
                style_listar = (
                    f"background-color: {bg_data};"
                )
                html_content += f"""
            <div style="position:absolute; left:{component['x']}px; top:{component['y']}px; width:{component['width']}px; height:{component['height']}px;">
            <div class="flex flex-col w-full gap-4 overflow-hidden">
            <!-- Encabezado -->
            <div class="flex justify-between items-center">
                <span class="{component['label'].get('styles', '')}">{component['label'].get('text', '')}</span>
                <div class="flex gap-2 items-center">
                <input placeholder="{component['search'].get('placeholder', '')}" class="{component['search'].get('styles', '')}" />
                <button
                    class="{component['button'].get('styles', '')}"
                    style="background-color:{component['button'].get('backgroundColor', '#2563eb')}; border-radius:{component['button'].get('borderRadius', '0.375rem')}; height:40px;"
                    (click)="openDialog()">
                    {component['button'].get('label', 'Agregar')}
                </button>
                </div>
            </div>

            <!-- Tabla -->
            <div class="overflow-x-auto rounded-lg h-full shadow-sm" style="{style_listar}">
                <table class="min-w-full divide-y divide-gray-200 text-sm text-left text-gray-800">
                <thead class="bg-gray-100 text-xs font-semibold uppercase text-gray-600">
                    <tr>
            """
                for header in component["dataTable"]["headers"]:
                    html_content += f"          <th class='px-4 py-3'>{header}</th>\n"

                html_content += """
                    <th class="px-4 py-3 text-right">...</th>
                    </tr>
                </thead>
                <tbody>
                    <tr *ngFor="let row of dataTableRows; let i = index" class="hover:bg-gray-50 transition">
                    <td class="px-4 py-3" *ngFor="let cell of row">{{cell}}</td>
                    <td class="relative px-4 py-3 text-right">
                        <button class="text-gray-500 hover:text-gray-700" (click)="toggleRowMenu(i)">
                            <i class="fa fa-ellipsis-v"></i>
                        </button>

                        <div *ngIf="openRowMenuIndex === i" class="absolute right-0 mt-2 w-32 bg-white border border-gray-200 rounded-md shadow-lg z-50">
                            <button class="w-full text-left px-4 py-2 text-sm hover:bg-gray-100" (click)="editRow(i)">
                                Editar
                            </button>
                            <button class="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-100" (click)="confirmDeleteRow(i)">
                                Eliminar
                            </button>
                        </div>
                    </td>
                    </tr>
                </tbody>
                </table>
            </div>

            <!-- Pagination -->
            <div class="flex justify-end items-center space-x-2 text-sm text-black">
                <button class="px-3 py-1 rounded hover:bg-gray-100 transition" [ngStyle]="styleListar">&lt; Previous</button>
                <button class="px-3 py-1 rounded bg-white ring-2 ring-gray-300" [ngStyle]="styleListar">1</button>
                <button class="px-3 py-1 rounded hover:bg-gray-100">2</button>
                <button class="px-3 py-1 rounded hover:bg-gray-100">3</button>
                <span class="px-2">…</span>
                <button class="px-3 py-1 rounded hover:bg-gray-100" [ngStyle]="styleListar">Next &gt;</button>
            </div>

            <!-- Dialog -->
            <div *ngIf="isDialogOpen" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40">
                <div class="bg-white rounded-lg shadow-lg w-[500px] max-w-full p-6 space-y-4">
                <h2 class="text-xl font-semibold text-black mb-2">{{ dialogTitle }}</h2>
            """
                for field in component["dialog"]["fields"]:
                    if field["type"]["type"] == "input":
                        html_content += f"""
                <div class="flex flex-col space-y-1">
                    <label class="text-sm font-medium text-gray-700">{field['label']}</label>
                    <input
                    class="{field['type'].get('styles', 'border border-gray-300 rounded px-3 py-1 text-sm')}"
                    placeholder="{field['type'].get('placeholder', '')}"
                    [(ngModel)]="formValues['{field['label']}']" />
                </div>
            """
                    elif field["type"]["type"] == "select":
                        html_content += f"""
                <div class="flex flex-col space-y-1">
                    <label class="text-sm font-medium text-gray-700">{field['label']}</label>
                    <select
                    class="border border-gray-300 rounded px-3 py-1 text-sm"
                    [(ngModel)]="formValues['{field['label']}']">
            """
                        for option in field["type"]["options"]:
                            html_content += f"""          <option value="{option}">{option}</option>\n"""
                        html_content += """        </select>
                </div>
            """
                html_content += """
                <div class="flex justify-end gap-2 pt-4">
                    <button (click)="closeDialog()" class="px-4 py-2 rounded border border-gray-300 text-gray-600 hover:bg-gray-100">Cancelar</button>
                    <button (click)="saveDialog()" class="px-4 py-2 rounded bg-blue-600 text-white hover:bg-blue-700">Guardar</button>
                </div>
                </div>
            </div>
            <!-- Confirmar Eliminación -->
            <div *ngIf="confirmDeleteRowIndex !== null" class="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40">
                <div class="bg-white p-6 rounded-lg shadow-lg w-[400px] space-y-4">
                <h2 class="text-xl font-semibold text-black mb-4">¿Estás seguro de eliminar esta fila?</h2>
                <div class="flex justify-end gap-2">
                    <button
                    (click)="confirmDeleteRowIndex = null"
                    class="px-4 py-2 rounded border border-gray-300 text-gray-600 hover:bg-gray-100">
                    Cancelar
                    </button>
                    <button
                    (click)="deleteRow()"
                    class="px-4 py-2 rounded bg-red-600 text-white hover:bg-red-700">
                    Eliminar
                    </button>
                </div>
                </div>
            </div>
            </div>
            </div>
            """
        
        with open(os.path.join(folder, f"{slug}.component.ts"), "w", encoding="utf-8") as f:
            f.write(f"""import {{ Component }} from '@angular/core';

        @Component({{
        selector: 'app-{slug}',
        templateUrl: './{slug}.component.html',
        styleUrls: ['./{slug}.component.css']
        }})
        export class {cls} {{
        """)

            # Si necesita sidebar
            if needs_sidebar:
                f.write("""  isSidebarOpen = true;

        toggleSidebar() {
            this.isSidebarOpen = !this.isSidebarOpen;
        }

        """)

            # Si necesita listar
            if needs_listar:
                headers_list = [json.dumps(field['label']) for field in listar_fields]  # ejemplo: ["Id", "Nombre", "Descripción", "Fecha", "Estado"]

                f.write(f"""  
            isDialogOpen = false;
            formValues: Record<string, any> = {{}};
            openRowMenuIndex: number | null = null;
            editRowIndex: number | null = null;
            confirmDeleteRowIndex: number | null = null;

            dataTableRows = {listar_rows};
            dialogTitle = {json.dumps(listar_title)};
            styleListar = {{ 'background-color': '{bg_data}' }};
            openDialog() {{
                this.isDialogOpen = true;
            }}

            closeDialog() {{
                this.isDialogOpen = false;
                this.editRowIndex = null;
            }}

            toggleRowMenu(index: number) {{
                this.openRowMenuIndex = this.openRowMenuIndex === index ? null : index;
            }}

            editRow(index: number) {{
                this.editRowIndex = index;
                const row = this.dataTableRows[index];
                this.formValues = {{}};
                const headers = [{', '.join(headers_list)}];
                headers.forEach((header, idx) => {{
                this.formValues[header] = row[idx];
                }});
                this.isDialogOpen = true;
                this.openRowMenuIndex = null;
            }}

            confirmDeleteRow(index: number) {{
                this.confirmDeleteRowIndex = index;
                this.openRowMenuIndex = null;
            }}

            deleteRow() {{
                if (this.confirmDeleteRowIndex !== null) {{
                this.dataTableRows.splice(this.confirmDeleteRowIndex, 1);
                this.confirmDeleteRowIndex = null;
                }}
            }}

            saveDialog() {{
                const newRow = [
            """)

                # Aquí cada campo como antes:
                for field in listar_fields:
                    f.write(f"      this.formValues['{field['label']}'] ?? '' ,\n")

                # Ahora cerramos la función saveDialog
                f.write("""    ];
                if (this.editRowIndex !== null) {
                this.dataTableRows[this.editRowIndex] = newRow;
                } else {
                this.dataTableRows.push(newRow);
                }
                this.formValues = {};
                this.isDialogOpen = false;
                this.editRowIndex = null;
            }
            """)

            # Cerrar class
            f.write("""}
        """)
            
        with open(os.path.join(folder, f"{slug}.component.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
        with open(os.path.join(folder, f"{slug}.component.css"), "w", encoding="utf-8") as f:
            f.write("")  # CSS vacío por ahora
        # Agregar la ruta de la página
        routes.append(f"{{ path: 'page-{page.id}', component: {cls} }}")
    
    routes.insert(0, "{ path: '', redirectTo: 'page-%s', pathMatch: 'full' }" % proyecto.pages[0].id)
    # Crear app-routing.module.ts
    routing_module_path = os.path.join(app_dir, "app-routing.module.ts")
    with open(routing_module_path, "w", encoding="utf-8") as f:
        f.write(f"""import {{ NgModule }} from '@angular/core';
    import {{ RouterModule, Routes }} from '@angular/router';

    {''.join(f'import {{ {cls} }} from \'./{slug}/{slug}.component\';\n' for cls, slug in component_info)}

    const routes: Routes = [
    {',\n'.join(routes)}
    ];

    @NgModule({{
    imports: [RouterModule.forRoot(routes)],
    exports: [RouterModule]
    }})
    export class AppRoutingModule {{}}
    """)
    
    # Crear app.component.html
    with open(os.path.join(app_dir, f"app.component.html"), "w", encoding="utf-8") as f:
        f.write("<router-outlet></router-outlet>")

    # Crear app-root.component.spec.ts
    with open(os.path.join(app_dir, "app-root.component.spec.ts"), "w", encoding="utf-8") as f:
        f.write("""import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [RouterTestingModule],
    declarations: [AppComponent]
  }));

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have as title 'angular-rutas-tailwind'`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('angular-rutas-tailwind');
  });

  it('should render title', () => {
    const fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('.content span')?.textContent).toContain('angular-rutas-tailwind app is running!');
  });
});
""")
    # Crear app.component.css
    with open(os.path.join(app_dir, "app.component.css"), "w", encoding="utf-8") as f:
        f.write("")  # CSS vacío
        
    # Crear app.component.ts
    with open(os.path.join(app_dir, "app.component.ts"), "w", encoding="utf-8") as f:
        f.write("""import { Component } from '@angular/core';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'angular-rutas-tailwind';
}
""")
    # Crear app.module.ts
    module_path = os.path.join(app_dir, "app.module.ts")
    imports = "".join(f"import {{ {cls} }} from './{slug}/{slug}.component';\n" for cls, slug in component_info)
    declarations = "".join(f"  {cls},\n" for cls, _ in component_info)
    bootstrap_cls = "AppComponent"

    with open(module_path, "w", encoding="utf-8") as f:
        f.write(f"""import {{ NgModule }} from '@angular/core';
import {{ BrowserModule }} from '@angular/platform-browser';
import {{ AppRoutingModule }} from './app-routing.module';
import {{ AppComponent }} from './app.component';
import {{ FormsModule }} from '@angular/forms'; 
                
{imports}
@NgModule({{
  declarations: [
  AppComponent,
{declarations}  ],
  imports: [BrowserModule, AppRoutingModule, FormsModule],
  providers: [],
  bootstrap: [{bootstrap_cls}]
}})
export class AppModule {{}}
""")

    # Comprimir el proyecto
    zip_filename = f"{carpeta_proyecto}.zip"
    shutil.make_archive(carpeta_proyecto, 'zip', carpeta_proyecto)

    return FileResponse(path=zip_filename, filename="frontend-angular.zip", media_type='application/zip')