from flask import Flask, request, render_template, session, redirect, url_for, send_file 
from functools import wraps
import os
import re
import reportlab
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import mariadb
import pymongo
from datetime import datetime
from pymongo import MongoClient
from urllib.parse import quote, unquote
import base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = "clau_hiper_ultra_mega_secreta_bro_123"

# Configuració de MariaDB
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "sergi",
    "database": "gestor_projectes"
}

# Configuració de MongoDB
mongo_client = pymongo.MongoClient("mongodb://localhost:27017/")
mongo_db = mongo_client["gestor_projectes"]
comentaris_collection = mongo_db["comentaris"]
revisions_alumnes_collection = mongo_db["revisions_alumnes"]  # Nova col·lecció per a revisions d'alumnes
mongo_perfils = mongo_db["perfils"]  # Col·lecció per a les dades del perfil
# Funció per connectar a MariaDB

def connect_to_mariadb():
    try:
        conn = mariadb.connect(
            user="root",
            password="sergi",
            host="localhost",
            port=3306,
            database="gestor_projectes"
        )
        return conn
    except mariadb.Error as e:
        print(f"Error connectant a MariaDB: {e}")
        return None

class Usuari:
    def __init__(self, usuario, nom, edat, telefon):
        self.usuario = usuario
        self.nom = nom
        self.edat = edat
        self.telefon = telefon

    def to_dict(self):
        return {
            "usuario": self.usuario,
            "nom": self.nom,
            "edat": self.edat,
            "telefon": self.telefon,
            "rol": self.__class__.__name__.lower()
        }

class Professor(Usuari):
    def __init__(self, usuario, nom, edat, telefon, placa_fixa):
        super().__init__(usuario, nom, edat, telefon)
        self.placa_fixa = placa_fixa

    def to_dict(self):
        data = super().to_dict()
        data["placa_fixa"] = self.placa_fixa
        return data

class Alumne(Usuari):
    def __init__(self, usuario, nom, edat, telefon, identificador_alumne):
        super().__init__(usuario, nom, edat, telefon)
        self.identificador_alumne = identificador_alumne
    
    def to_dict(self):
        data = super().to_dict()
        data["identificador_alumne"] = self.identificador_alumne
        return data

# Verifica el usuari i contrasenya a MariaDB i torna el rol si és vàlid
def verificar_credenciales(user, password):
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuaris WHERE usuari = ? AND contrasenya = ?", (user, password))
            result = cursor.fetchone()
            if result:
                print(f"Rol retornat per a l'usuari {user}: {result[0]}")
                return result[0]
        finally:
            conn.close()
    return None

def es_professor():
    rol = session.get("rol")
    print(f"A es_professor, session['rol']: {rol}")
    return rol == "Professor"

def es_alumne():
    rol = session.get("rol")
    print(f"A es_alumne, session['rol']: {rol}")
    return rol == "Alumne"

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def professor_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("usuario"):
            return redirect(url_for("login"))
        if not es_professor():
            return redirect(url_for("error403"))
        return f(*args, **kwargs)
    return wrapped

def alumne_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("usuario"):
            return redirect(url_for("login"))
        if not es_alumne():
            return redirect(url_for("error403"))
        return f(*args, **kwargs)
    return wrapped

# Busca l'últim identificador d'alumne i suma 1 a un format de 3 dígits
def generar_identificador_alumne():
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(identificador_alumne) FROM usuaris WHERE rol = 'Alumne'")
            result = cursor.fetchone()
            max_id = int(result[0]) if result[0] else 0
            return str(max_id + 1).zfill(3)
        finally:
            conn.close()
    return '001'

# Carrega els usuaris des de MariaDB
def cargar_usuaris():
    usuaris = []
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT usuari, nom, email, rol FROM usuaris")
            for fila in cursor:
                usuari, nom, email, rol = fila
                usuaris.append({
                    "usuario": usuari,
                    "nom": nom,
                    "email": email,
                    "rol": rol
                })
        finally:
            conn.close()
    return usuaris

# Carrega els projectes des de MariaDB
def carregar_projectes(com_notes=False):
    projectes = []
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT p.id, p.titol AS nom_projecte, p.assignatura, p.estat, p.nota, u.usuari
                FROM projectes p
                JOIN usuaris u ON p.alumne_id = u.id
            """
            cursor.execute(query)
            for fila in cursor:
                projecte = {
                    "id": fila["id"],
                    "nom_projecte": fila["nom_projecte"],
                    "contingut": "",
                    "usuario": fila["usuari"],
                    "asignatura": fila["assignatura"],
                    "notes": fila["nota"] if com_notes and fila["nota"] is not None else fila["estat"]
                }
                projectes.append(projecte)
        finally:
            conn.close()
    return projectes

# Carrega els projectes filtrats per usuari i rol
def cargar_proyectos_home():
    proyectos = []
    usuario = session.get('usuario')
    rol = session.get('rol')
    print(f"A cargar_proyectos_home, session['rol'] és: {rol}")
    projectes_notes = carregar_projectes(com_notes=True)
    for projecte in projectes_notes:
        if isinstance(projecte, dict):
            if rol == 'Professor' or (rol == 'Alumne' and projecte["usuario"] == usuario):
                proyectos.append(projecte)
    return proyectos

@app.route("/home")
@login_required
def home():
    proyectos = cargar_proyectos_home()
    session['proyectos'] = proyectos
    print(f"Abans de renderitzar home.html, session['rol']: {session.get('rol')}")
    return render_template("home.html", proyectos=proyectos, usuario=session["usuario"])

@app.route("/guardar_y_redirigir", methods=["GET", "POST"])
@login_required
def guardar_y_redirigir():
    proyectos = cargar_proyectos_home()
    session['proyectos'] = proyectos
    return redirect(url_for('home'))

@app.route("/indexprojectes", methods=["GET", "POST"])
@login_required
def indexprojectes():
    usuario_actual = session["usuario"]
    
    # Carreguem només els projectes de l'usuari loguejat
    conn = connect_to_mariadb()
    projectes = []
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.titol AS nom_projecte, p.assignatura, p.estat, p.nota, u.usuari
                FROM projectes p
                JOIN usuaris u ON p.alumne_id = u.id
                WHERE LOWER(u.usuari) = LOWER(%s)
            """, (usuario_actual,))
            projectes = cursor.fetchall()
        finally:
            conn.close()

    if request.method == "POST":
        proyecto_seleccionado = request.form.get("proyecto")
        if proyecto_seleccionado:
            proyecto_codificado = quote(proyecto_seleccionado)
            return redirect(url_for('projecte', proyecto=proyecto_codificado))
        else:
            return render_template("indexprojectes.html", proyectos=projectes, error="Per favor, selecciona un projecte.", usuario=usuario_actual)
    return render_template("indexprojectes.html", proyectos=projectes, usuario=usuario_actual)

def generar_pdf_projecte(proyecto, output_pdf, title_size, content_size, font_name):
    os.makedirs(os.path.dirname(output_pdf), exist_ok=True)
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    y_position = height - 50
    c.setFont(font_name, title_size)
    c.drawString(100, y_position, f"Projecte: {proyecto.get('nom_projecte', 'Sense títol')}")
    y_position -= 20
    c.setFont(font_name, content_size)
    c.drawString(100, y_position, f"Assignatura: {proyecto.get('assignatura', 'Sense assignatura')}")
    c.save()
    print(f"PDF generat: {output_pdf}")

@app.route('/projecte/<proyecto>', methods=["GET", "POST"])
def projecte(proyecto):
    usuario_actual = session.get("usuario")
    proyecto_decodificado = unquote(proyecto)
    proyecto_encontrado = None
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.titol AS nom_projecte, p.assignatura, p.estat, p.nota, u.usuari
                FROM projectes p
                JOIN usuaris u ON p.alumne_id = u.id
                WHERE p.titol = %s AND LOWER(u.usuari) = LOWER(%s)
            """, (proyecto_decodificado, usuario_actual))
            proyecto_encontrado = cursor.fetchone()
        finally:
            conn.close()

    if not proyecto_encontrado:
        return render_template("error.html", mensaje=f"No tens permís per accedir a '{proyecto_decodificado}' o el projecte no existeix.", usuario=usuario_actual), 403

    if request.method == "POST":
        proyecto_form = request.form.get("proyecto", proyecto_decodificado)
        title_size = int(request.form.get('title_size', 16))
        content_size = int(request.form.get('content_size', 12))
        font_name = request.form.get('font_name', 'Helvetica')
        proyecto_safe = proyecto_form.replace(" ", "_")
        output_pdf = os.path.join("static/pdf", f"{proyecto_safe}.pdf")
        generar_pdf_projecte(proyecto_encontrado, output_pdf, title_size, content_size, font_name)
        return send_file(output_pdf, as_attachment=True, mimetype="application/pdf")
    return render_template("projecte.html", proyecto=proyecto_encontrado)

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contra = request.form["contraseña"]
        rol = verificar_credenciales(usuario, contra)

        if rol in ["Professor", "Alumne"]:
            session["usuario"] = usuario
            session["rol"] = rol
            print(f"Session['rol'] configurat com: {session['rol']}")
            return redirect(url_for('home'))
        else:
            return render_template("login.html", mensaje="Usuari o contrasenya incorrectes")

    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("rol", None)
    return redirect(url_for("login"))

# Pàgina d'error
@app.route("/403")
def error403():
    return render_template("403.html"), 403

# Funció per afegir dades personals
@app.route("/afegir_dades_personals", methods=["GET", "POST"])
@login_required
def afegir_dades_personals():
    if "usuario" not in session:
        return redirect(url_for('login'))

    usuario_sessio = session["usuario"]

    if request.method == "POST":
        try:
            nom = request.form["nom"]
            edat = request.form["edat"]
            telefon = request.form["telefon"]
        except KeyError as e:
            return render_template("dadespersonals.html", missatge=f"Error: Falta el camp {e} al formulari.")

        # Actualitza les dades a MariaDB
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE usuaris SET nom = ?, edat = ?, telefon = ? WHERE usuari = ?",
                    (nom, edat, telefon, usuario_sessio)
                )
                conn.commit()
            finally:
                conn.close()

        return render_template("home.html", usuario=session["usuario"])

    return render_template("dadespersonals.html", usuario=session["usuario"])

# Funció per registrar usuaris
@app.route("/registrar", methods=["GET", "POST"])
@professor_required
def registrar():
    rol = request.args.get("rolusuari")
    mensaje = None

    if request.method == "POST":
        segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        usuario = request.form["usuario"]
        contraseña = request.form["contrasena"]
        nombre = request.form["nombre"]
        edad = request.form["edad"]
        telefono = request.form["telefono"]

        if not rol:
            rol = request.form.get("rolusuari")

        if not rol:
            return render_template("registrar.html", mensaje="Debes seleccionar un rol antes de registrarte.")

        if not re.match(segura, contraseña):
            return render_template("registrar.html", mensaje="La contraseña no es segura.")

        # Verifica si l'usuari ja existeix
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT usuari FROM usuaris WHERE usuari = ?", (usuario,))
                if cursor.fetchone():
                    return render_template("registrar.html", mensaje="El usuario ya existe.")
            finally:
                conn.close()

        # Genera identificador d'alumne si és alumne
        identificador_alumne = generar_identificador_alumne() if rol == "alumne" else ""
        placa_fixa = "SI" if rol == "professor" else ""

        # Insereix l'usuari a MariaDB
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO usuaris (usuari, contrasenya, nom, email, edat, telefon, rol, placa_fixa, identificador_alumne) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (usuario, contraseña, nombre, f"{nombre.lower()}@iesmontsia.org", edad, telefono, rol.capitalize(), placa_fixa, identificador_alumne)
                )
                conn.commit()
            finally:
                conn.close()

        return redirect(url_for("home"))

    return render_template("registrar.html", usuario=session.get("usuario", ""), rol=rol, mensaje=mensaje)

# Funció per llistar usuaris
@app.route("/usuaris")
def listar_usuaris():
    usuaris = cargar_usuaris()
    return render_template("usuaris.html", usuaris=usuaris, usuario=session["usuario"])

@app.route("/canviarcontra", methods=["GET", "POST"])
@professor_required
def canviarcontra():
    segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if request.method == "POST":
        usuari = request.form["usuari"]
        nova = request.form["nova"]
        confirmar = request.form["confirmar"]
        if nova != confirmar:
            return render_template("canviarcontra.html", mensaje="Las contraseñas no coinciden.", usuario=session["usuario"])

        if not re.match(segura, nova):
            return render_template("canviarcontra.html", mensaje="La contraseña no es segura. Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", usuario=session["usuario"])

        conn = connect_to_mariadb()
        trobat = False
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("UPDATE usuaris SET contrasenya = ? WHERE usuari = ?", (nova, usuari))
                if cursor.rowcount > 0:
                    trobat = True
                conn.commit()
            finally:
                conn.close()

        if not trobat:
            return render_template("canviarcontra.html", mensaje="Usuario no encontrado.", usuario=session["usuario"])
        return render_template("canviarcontra.html", mensaje="Contraseña cambiada exitosamente.", usuario=session["usuario"])
    return render_template("canviarcontra.html", usuario=session["usuario"])

@app.route("/notes", methods=["GET", "POST"])
@professor_required
def notes():
    if request.method == "POST":
        # Obtenir les dades del formulari
        nota = request.form["nota"]
        buscusuari = request.form["buscusuari"]
        buscprojecte = request.form["buscprojecte"]
        asignatura = request.form["buscasignatura"]

        # Validar la nota (ha de ser un número entre 0 i 10)
        try:
            nota = float(nota)
            if not 0 <= nota <= 10:
                return render_template("notes.html", datos=[], usuario=session["usuario"], mensaje="La nota ha d'estar entre 0 i 10.")
        except ValueError:
            return render_template("notes.html", datos=[], usuario=session["usuario"], mensaje="La nota ha de ser un número vàlid.")

        # Obtenir el projecte_id i l'alumne_id
        conn = connect_to_mariadb()
        projecte_id = None
        alumne_id = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuaris WHERE usuari = ?", (buscusuari,))
                result = cursor.fetchone()
                if result:
                    alumne_id = result[0]
                else:
                    return render_template("notes.html", datos=[], usuario=session["usuario"], mensaje="Usuari no trobat.")

                cursor.execute("""
                    SELECT id FROM projectes
                    WHERE alumne_id = ? AND titol = ? AND assignatura = ?
                """, (alumne_id, buscprojecte, asignatura))
                result = cursor.fetchone()
                if result:
                    projecte_id = result[0]
                else:
                    return render_template("notes.html", datos=[], usuario=session["usuario"], mensaje="Projecte no trobat.")
            finally:
                conn.close()

        # Obtenir el professor_id (de l'usuari actual)
        conn = connect_to_mariadb()
        professor_id = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuaris WHERE usuari = ?", (session["usuario"],))
                result = cursor.fetchone()
                if result:
                    professor_id = result[0]
            finally:
                conn.close()

        # Inserir la correcció a la taula correccions
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO correccions (projecte_id, professor_id, nota)
                    VALUES (?, ?, ?)
                """, (projecte_id, professor_id, nota))
                conn.commit()
            finally:
                conn.close()

        # Actualitzar la taula projectes
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE projectes
                    SET nota = ?, estat = 'Revisat'
                    WHERE id = ?
                """, (nota, projecte_id))
                conn.commit()
            finally:
                conn.close()

    # Carregar els projectes per mostrar-los
    datos = []
    conn = connect_to_mariadb()
    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT p.titol AS Nomprojecte, p.assignatura, p.estat, p.nota, u.usuari
                FROM projectes p
                JOIN usuaris u ON p.alumne_id = u.id
            """)
            for fila in cursor:
                datos.append({
                    "usuario": fila["usuari"],
                    "Nomprojecte": fila["Nomprojecte"],
                    "asignatura": fila["assignatura"],
                    "contenido": "",
                    "notes": fila["nota"] if fila["nota"] is not None else fila["estat"]
                })
        finally:
            conn.close()

    return render_template("notes.html", datos=datos, usuario=session["usuario"])

@app.route("/afegir_comentari", methods=["GET", "POST"])
@professor_required
def afegir_comentari():
    if request.method == "POST":
        # Obtenir les dades del formulari
        projecte_id = request.form.get("projecte_id")
        text_comentari = request.form.get("text_comentari")

        # Validar les dades
        if not projecte_id or not text_comentari:
            projectes = carregar_projectes()
            return render_template("afegir_comentari.html", usuario=session["usuario"], mensaje="Falten dades: projecte o comentari.", projectes=projectes)

        try:
            projecte_id = int(projecte_id)
        except ValueError:
            projectes = carregar_projectes()
            return render_template("afegir_comentari.html", usuario=session["usuario"], mensaje="El projecte ID ha de ser un número.", projectes=projectes)

        # Obtenir el professor_id
        conn = connect_to_mariadb()
        professor_id = None
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuaris WHERE usuari = ?", (session["usuario"],))
                result = cursor.fetchone()
                if result:
                    professor_id = result[0]
                else:
                    projectes = carregar_projectes()
                    return render_template("afegir_comentari.html", usuario=session["usuario"], mensaje="Professor no trobat.", projectes=projectes)
            finally:
                conn.close()

        # Verificar que el projecte existeix a MariaDB
        conn = connect_to_mariadb()
        projecte_existeix = False
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM projectes WHERE id = ?", (projecte_id,))
                if cursor.fetchone():
                    projecte_existeix = True
            finally:
                conn.close()

        if not projecte_existeix:
            projectes = carregar_projectes()
            return render_template("afegir_comentari.html", usuario=session["usuario"], mensaje="Projecte no trobat.", projectes=projectes)

        # Afegir el comentari a MongoDB
        comentari_nou = {
            "professor_id": professor_id,
            "text": text_comentari,
            "data": datetime.utcnow().isoformat()
        }

        # Actualitzar o inserir el document a la col·lecció comentaris
        comentaris_collection.update_one(
            {"projecte_id": projecte_id},
            {"$push": {"comentaris": comentari_nou}},
            upsert=True
        )

        projectes = carregar_projectes()
        return render_template("afegir_comentari.html", usuario=session["usuario"], mensaje="Comentari afegit correctament.", projectes=projectes)

    # Carregar la llista de projectes per mostrar-la al formulari
    projectes = carregar_projectes()
    return render_template("afegir_comentari.html", usuario=session["usuario"], projectes=projectes)

@app.route("/projectes", methods=["GET", "POST"])
@login_required
def projectes():
    if request.method == "POST":
        usuario = session["usuario"]
        Nomprojecte = request.form["Nomprojecte"]
        contingut = request.form["contingut"]
        asignatura = request.form["asignatura"]

        # Obté l'alumne_id a partir del nom d'usuari
        alumne_id = None
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM usuaris WHERE usuari = ?", (usuario,))
                result = cursor.fetchone()
                if result:
                    alumne_id = result[0]
            finally:
                conn.close()

        if not alumne_id:
            return render_template("projectes.html", mensaje="Error: Usuari no trobat", usuario=session["usuario"])

        # Comprova si el projecte ja existeix
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM projectes
                    WHERE alumne_id = ? AND titol = ? AND assignatura = ?
                """, (alumne_id, Nomprojecte, asignatura))
                if cursor.fetchone():
                    return render_template("projectes.html", mensaje="El projecte ja ha sigut creat", usuario=session["usuario"])
            finally:
                conn.close()

        # Insereix el projecte a MariaDB
        conn = connect_to_mariadb()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO projectes (alumne_id, assignatura, titol, estat, nota)
                    VALUES (?, ?, ?, 'Pendent', NULL)
                """, (alumne_id, asignatura, Nomprojecte))
                conn.commit()
            finally:
                conn.close()

        return render_template("projectes.html", mensaje="Creado", usuario=session["usuario"])
    return render_template("projectes.html", usuario=session["usuario"])

@app.route("/mostraprojectes", methods=["GET", "POST"])
@login_required
def mostraprojectes():
    usuario_actual = session["usuario"]
    conn = connect_to_mariadb()
    proyectos = []
    buscasignatura = None

    if request.method == "POST":
        # Si es selecciona un projecte per veure'l
        proyecto_seleccionado = request.form.get("proyecto")
        if proyecto_seleccionado:
            proyecto_codificado = quote(proyecto_seleccionado)
            return redirect(url_for('projecte', proyecto=proyecto_codificado))

        # Si es filtra per assignatura
        buscasignatura = request.form.get("buscasignatura")

    if conn:
        try:
            cursor = conn.cursor(dictionary=True)
            if buscasignatura and buscasignatura != "Tots":
                cursor.execute("""
                    SELECT p.titol, p.assignatura, p.nota
                    FROM projectes p
                    JOIN usuaris u ON p.alumne_id = u.id
                    WHERE LOWER(u.usuari) = LOWER(%s) AND p.assignatura = %s
                """, (usuario_actual, buscasignatura))
            else:
                cursor.execute("""
                    SELECT p.titol, p.assignatura, p.nota
                    FROM projectes p
                    JOIN usuaris u ON p.alumne_id = u.id
                    WHERE LOWER(u.usuari) = LOWER(%s)
                """, (usuario_actual,))
            proyectos = cursor.fetchall()
        except Exception as e:
            return render_template("error.html", mensaje=f"Error al carregar projectes: {str(e)}", usuario=usuario_actual), 500
        finally:
            conn.close()
    else:
        return render_template("error.html", mensaje="No s'ha pogut connectar a la base de dades.", usuario=usuario_actual), 500

    return render_template("mostraprojectes.html", proyectos=proyectos, usuario=usuario_actual, error=None)

@app.route("/enviar_revisio", methods=["GET", "POST"])
@alumne_required
def enviar_revisio():
    if request.method == "POST":
        projecte_id = request.form.get("projecte_id")
        text_comentari = request.form.get("text_comentari")
        fitxer_pdf = request.files.get("fitxer_pdf")

        # Validacions
        if not projecte_id or not text_comentari or not fitxer_pdf:
            projectes = carregar_projectes()
            return render_template("enviar_revisio.html", mensaje="Tots els camps són obligatoris", usuario=session["usuario"], projectes=projectes)

        # Comprova que el fitxer sigui PDF
        if not fitxer_pdf.filename.endswith(".pdf"):
            projectes = carregar_projectes()
            return render_template("enviar_revisio.html", mensaje="El fitxer ha de ser un PDF", usuario=session["usuario"], projectes=projectes)

        try:
            projecte_id = int(projecte_id)
        except ValueError:
            projectes = carregar_projectes()
            return render_template("enviar_revisio.html", usuario=session["usuario"], mensaje="El projecte ID ha de ser un número.", projectes=projectes)

        # Verificar que el projecte existeix a MariaDB i pertany a l'alumne
        conn = connect_to_mariadb()
        projecte_existeix = False
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT p.id FROM projectes p
                    JOIN usuaris u ON p.alumne_id = u.id
                    WHERE p.id = ? AND u.usuari = ?
                """, (projecte_id, session["usuario"]))
                if cursor.fetchone():
                    projecte_existeix = True
            finally:
                conn.close()

        if not projecte_existeix:
            projectes = carregar_projectes()
            return render_template("enviar_revisio.html", usuario=session["usuario"], mensaje="Projecte no trobat o no tens permís per accedir-hi.", projectes=projectes)

        # Llegeix el fitxer PDF com a dades binàries
        pdf_data = fitxer_pdf.read()

        # Formateja la data al format desitjat (YYYY/MM/DD - HH:MM) amb la zona horària d'Espanya
        from datetime import datetime
        import pytz
        timezone = pytz.timezone("Europe/Madrid")
        data_local = datetime.now(timezone)
        data_formatejada = data_local.strftime("%Y/%m/%d - %H:%M")

        # Insereix la revisió a MongoDB
        revisions_alumnes_collection.insert_one({
            "projecte_id": projecte_id,
            "usuari": session["usuario"],
            "comentari": text_comentari,
            "fitxer_pdf": pdf_data,
            "data": data_formatejada
        })

        projectes = carregar_projectes()
        return render_template("enviar_revisio.html", mensaje="Revisió enviada correctament", usuario=session["usuario"], projectes=projectes)

    # GET: Mostra el formulari
    projectes = carregar_projectes()
    return render_template("enviar_revisio.html", usuario=session["usuario"], projectes=projectes)

@app.route('/perfil', methods=['GET', 'POST'])
def perfil():
    if "usuario" not in session:
        return redirect(url_for('login'))

    usuari = session["usuario"]
    try:
        conn = mariadb.connect(**db_config)
        cursor = conn.cursor(dictionary=True)

        # Obtenir dades de MariaDB
        cursor.execute("SELECT * FROM usuaris WHERE usuari = %s", (usuari,))
        usuari_data = cursor.fetchone()

        if not usuari_data:
            return "Usuari no trobat", 404

        # Obtenir dades de MongoDB
        if mongo_perfils is None:
            return "Error: No s'ha pogut connectar a MongoDB", 500

        perfil_data = mongo_perfils.find_one({"usuari": usuari}) or {}
        foto_perfil = perfil_data.get("foto", None)
        dades_personalitzables = perfil_data.get("dades_personalitzables", {})

        if request.method == 'POST':
            # Obtenir dades del formulari
            nom = request.form.get('nom')
            telefon = request.form.get('telefon')
            contrasenya_antiga = request.form.get('contrasenya_antiga', '')
            nova_contrasenya = request.form.get('nova_contrasenya', '')
            color_favorit = request.form.get('color_favorit', '')
            descripcio = request.form.get('descripcio', '')
            foto = request.files.get('foto')

            # Gestionar el canvi de tema
            if request.form.get('canviar_tema'):
                tema_actual = session.get('tema', 'clar')
                session['tema'] = 'fosc' if tema_actual == 'clar' else 'clar'
                return redirect(url_for('perfil'))

            # Actualitzar dades a MariaDB
            updates = []
            params = []
            if nom:
                updates.append("nom = %s")
                params.append(nom)
            if telefon:
                updates.append("telefon = %s")
                params.append(telefon)
            if nova_contrasenya and contrasenya_antiga:
                if usuari_data['contrasenya'] == contrasenya_antiga:
                    updates.append("contrasenya = %s")
                    params.append(nova_contrasenya)
                else:
                    return render_template('perfil.html', usuari_data=usuari_data, foto_perfil=foto_perfil,
                                          dades_personalitzables=dades_personalitzables, usuario=usuari,
                                          error="Contrasenya antiga incorrecta")

            if updates:
                params.append(usuari)
                query = f"UPDATE usuaris SET {', '.join(updates)} WHERE usuari = %s"
                cursor.execute(query, params)
                conn.commit()

            # Actualitzar dades a MongoDB
            perfil_update = {"usuari": usuari}
            has_changes = False
            if foto and foto.filename:
                foto_data = foto.read()
                foto_base64 = base64.b64encode(foto_data).decode('utf-8')
                perfil_update["foto"] = foto_base64
                has_changes = True
            dades_personalitzables_update = {}
            if color_favorit:
                dades_personalitzables_update["color_favorit"] = color_favorit
                has_changes = True
            if descripcio:
                dades_personalitzables_update["descripcio"] = descripcio
                has_changes = True
            if dades_personalitzables_update:
                perfil_update["dades_personalitzables"] = dades_personalitzables_update

            if has_changes:
                mongo_perfils.update_one({"usuari": usuari}, {"$set": perfil_update}, upsert=True)

            return redirect(url_for('mostraprojectes'))

        cursor.close()
        conn.close()
        return render_template('perfil.html', usuari_data=usuari_data, foto_perfil=foto_perfil,
                              dades_personalitzables=dades_personalitzables, usuario=usuari)
    except mariadb.Error as err:
        return f"Error de connexió a MariaDB: {err}", 500
    except pymongo.errors.PyMongoError as e:
        return f"Error de MongoDB: {e}", 500
    except Exception as e:
        return f"Error inesperat: {e}", 500
    


if __name__ == "__main__":
    app.run(debug=True)