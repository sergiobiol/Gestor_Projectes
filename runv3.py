from flask import Flask, request, render_template, session, redirect, url_for, send_file
from functools import wraps
import csv
import os
import re
import reportlab
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = "clau_hiper_ultra_mega_secreta_bro_123"  # Necessari per gestionar sessions

class Usuari:
    def __init__(self, usuario, nom, cognom, edat, telefon):
        self.usuario = usuario
        self.nom = nom
        self.cognom = cognom
        self.edat = edat
        self.telefon = telefon

    def to_dict(self):
        return {
            "usuario": self.usuario,
            "nom": self.nom,
            "cognom": self.cognom,
            "edat": self.edat,
            "telefon": self.telefon,
            "rol": self.__class__.__name__.lower()
        }

class Professor(Usuari):
    def __init__(self, usuario, nom, cognom, edat, telefon, placa_fixa):
        super().__init__(usuario, nom, cognom, edat, telefon)
        self.placa_fixa = placa_fixa

    def to_dict(self):
        data = super().to_dict()
        data["placa_fixa"] = self.placa_fixa
        return data

class Alumne(Usuari):
    def __init__(self, usuario, nom, cognom, edat, telefon, identificador_alumne):
        super().__init__(usuario, nom, cognom, edat, telefon)
        self.identificador_alumne = identificador_alumne

    def to_dict(self):
        data = super().to_dict()
        data["identificador_alumne"] = self.identificador_alumne
        return data

def llegir_usuaris():
    usuaris = {}
    if os.path.exists("dadespersonals.csv"):
        with open("dadespersonals.csv", mode="r", encoding="utf-8") as fitxer:
            lector = csv.DictReader(fitxer)
            for fila in lector:
                usuaris[fila["usuario"]] = fila
    return usuaris

#Verifica el usuario y contraseña en el archivo CSV y devuelve el rol si es válido.
def verificar_credenciales(user,password):
    try:
        user = request.form["usuario"]
        password = request.form["contraseña"]
        with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == user:
                    if fila["contraseña"] == password:
                        return fila["rol"]  # Devuelve el rol del usuario
                    else:
                        return render_template("login.html", mensaje="Usuario o contraseña incorrectos")
    except FileNotFoundError:
        print("Error: El archivo 'dadespersonals.csv' no existe.")
        
    return render_template("login.html", mensaje="Usuario o contraseña incorrectos")  # Si no encuentra el usuario, devuelve False

def es_professor():
    usuario = session.get("usuario")  # Obtiene el usuario de la sesión
    usuaris = llegir_usuaris()  # Lee los datos del CSV (asumimos que devuelve un diccionario)
    
    datos_usuario = usuaris.get(usuario, {})
    
    es_rol_professor = datos_usuario.get("rol") == "professor"
    
    return es_rol_professor

def login_required(f):
    @wraps(f)  # Afegeix aquesta línia per evitar duplicacions
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def professor_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("usuario"):  # Verifica si hay un usuario en la sesión
            return redirect(url_for("login"))  # Redirige al login si no hay usuario
        if not es_professor():
            return redirect(url_for("error403"))
        return f(*args, **kwargs)
    return wrapped

#   Busca el último identificador de alumno y suma 1, formato 3 dígitos (001, 002...)
def generar_identificador_alumne():
    if not os.path.exists("dadespersonals.csv"):
        return '001'

    max_id = 0
    with open("dadespersonals.csv", 'r', encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)
        for fila in reader:
            if len(fila) >= 10 and fila[7] == 'alumne' and fila[9]:
                try:
                    num = int(fila[9])
                    if num > max_id:
                        max_id = num
                except ValueError:
                    continue
    return str(max_id + 1).zfill(3)

def cargar_usuaris():
    usuaris = []
    with open("dadespersonals.csv", newline="", encoding="utf-8") as file:
        lector = csv.reader(file)
        next(lector)  # Saltar encabezado
        for fila in lector:
            if len(fila) < 10:
                continue  # Saltar filas incompletas
            login, usuario, contraseña, nom, cognom, edat, telefon, rol, placa_fixa, identificador_alumne = fila

            if rol.lower() == "professor":
                usuario_obj = Professor(usuario, nom, cognom, edat, telefon, placa_fixa)
            elif rol.lower() == "alumne":
                usuario_obj = Alumne(usuario, nom, cognom, edat, telefon, identificador_alumne)
            else:
                continue  # Si el rol no es válido, lo ignoramos
            usuaris.append(usuario_obj.to_dict())

    return usuaris



@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contra = request.form["contraseña"]
        rol = verificar_credenciales(usuario, contra)

        if rol == "professor" or rol == "alumne":
            session["usuario"] = usuario  # Guarda el nombre de usuario en la sesión
            session["rol"] = rol

            login_valido = False  # Variable para determinar si el login es válido
            # Leer archivo CSV solo una vez
            with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                
                for fila in lector:
                    if fila["login"] == "1" and fila["usuario"] == usuario:
                        login_valido = True  # Si encontramos un login válido

            # Ahora que hemos leído el archivo, hacemos las redirecciones
            if login_valido:                
                 return redirect(url_for('home'))

            else:
                # Si el login és per primer cop, redirigimos a dadespersonals.html
                return render_template("dadespersonals.html", usuario=session["usuario"])

        else:
            # Si las credenciales no son correctas  
            return render_template("login.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("login.html")



@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

@app.route("/403")
def error403():
    return render_template("403.html"), 403

@app.route("/afegir_dades_personals", methods=["GET", "POST"])
@login_required
def afegir_dades_personals():
    if "usuario" not in session:
        return redirect(url_for('login'))  # Protección por si no hay usuario en sesión

    usuario_sessio = session["usuario"]
    usuaris = llegir_usuaris()  # Debe devolver dict con clave 'usuario'

    if request.method == "POST":
        # Recoger los datos del formulario con manejo de errores
        try:
            nom = request.form["nom"]
            cognom = request.form["cognom"]
            edat = request.form["edat"]
            telefon = request.form["telefon"]
        except KeyError as e:
            return render_template("dadespersonals.html", missatge=f"Error: Falta el camp {e} al formulari.")

        # Actualizar los campos editables
        usuaris[usuario_sessio]["nom"] = nom
        usuaris[usuario_sessio]["cognom"] = cognom
        usuaris[usuario_sessio]["edat"] = edat
        usuaris[usuario_sessio]["telefon"] = telefon

        # Actualizar el campo login a 1 para indicar que ya se editaron los datos
        usuaris[usuario_sessio]["login"] = "1"

        # Guardar todos los campos en el archivo CSV
        with open("dadespersonals.csv", mode="w", newline="", encoding="utf-8") as fitxer:
            fieldnames = ["login", "usuario", "contraseña", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"]
            writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(usuaris.values())

    return render_template("home.html", usuario=session["usuario"])

@app.route("/registrar", methods=["GET", "POST"])
@professor_required
def registrar():
    rol = request.args.get("rolusuari")  # Captura el rol en GET
    mensaje = None

    if request.method == "POST":
        segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        usuario = request.form["usuario"]
        contraseña = request.form["contrasena"]
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        edad = request.form["edad"]
        telefono = request.form["telefono"]
        professor = request.form.get("professor")  # Checkbox (1 si está marcado)

        # Si el rol no se pasó por GET, intenta capturarlo desde POST
        if not rol:
            rol = request.form.get("rolusuari")

        if not rol:
            return render_template("registrar.html", mensaje="Debes seleccionar un rol antes de registrarte.")

        # Validar seguridad de la contraseña
        if not re.match(segura, contraseña):
            return render_template("registrar.html", mensaje="La contraseña no es segura.")

        # Verificar si el usuario ya existe
        archivo_existe = os.path.exists("dadespersonals.csv")
        if archivo_existe:
            with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                for fila in lector:
                    if fila["usuario"] == usuario:
                        return render_template("registrar.html", mensaje="El usuario ya existe.")

        # Generar identificador_alumne solo si es alumno
        identificador_alumne = generar_identificador_alumne() if rol == "alumne" else ""
        identificador_professor = "SI" if rol == "professor" else ""
        # Escribir en CSV
        with open("dadespersonals.csv", mode="a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if not archivo_existe:
                escritor.writerow(["login", "usuario", "contrasena", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"])
            
            escritor.writerow([
                0, usuario, contraseña, nombre, apellido, edad, telefono, rol, identificador_professor, identificador_alumne
            ])

        return redirect(url_for("home"))

    return render_template("registrar.html", usuario=session.get("usuario", ""), rol=rol, mensaje=mensaje)


@app.route("/usuaris")
def listar_usuaris():
    usuaris = cargar_usuaris()
    return render_template("usuaris.html", usuaris=usuaris)
# Función para cargar proyectos desde el archivo CSV

def cargar_projectes():
    proyectos = []
    with open('projectes.csv', newline='', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)  # Saltar encabezado
        for fila in lector:
            if len(fila) > 0:  # Verificar que la fila no esté vacía
                proyectos.append(fila[0])  # Guardamos solo el título del proyecto
    return proyectos


def cargar_projectes_notes():
    projectesnotes = []
    with open('projectes.csv', newline='', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)  # Saltar encabezado
        for fila in lector:
            if len(fila) >= 4:  # Asegurar que la fila tiene todos los datos
                projectesnotes.append({
                    "nom_projecte": fila[0],
                    "contingut": fila[1],
                    "usuario": fila[2],
                    "asignatura": fila[3],
                    "notes": fila[4]
                })
    return projectesnotes


@app.route("/cargarproyectos", methods=["GET", "POST"])
@login_required
def cargar_proyectos_home():
    proyectos = []
    usuario = session.get('usuario')
    rol = session.get('rol')

    with open('projectes.csv', newline='', encoding='utf-8') as file:
            lector = csv.reader(file)
            next(lector)  # Saltar encabezado
            for fila in lector:
                if len(fila) > 0:
                    proyecto = fila[0]  # Nombre del proyecto
                    contenido = fila[1]  # Contenido del proyecto
                    proyecto_usuario = fila[2]  # Usuario propietario del proyecto
                    proyecto_asignatura = fila[3] #asignatura del proyecto
                    # Si el usuario es profesor, mostramos todos los proyectos
                    if rol == 'professor':
                        proyectos.append({'nombre': proyecto, 'contenido': contenido, 'usuario': proyecto_usuario, 'asignatura': proyecto_asignatura})
                    # Si el usuario es alumno, mostramos solo sus proyectos
                    elif rol == 'alumne' and proyecto_usuario == usuario:
                        proyectos.append({'nombre': proyecto, 'contenido': contenido, 'usuario': proyecto_usuario, 'asignatura': proyecto_asignatura})

    return proyectos

@app.route("/home")
@login_required
def home():
    projectes = []
    try:
        with open('projectes.csv', newline='', encoding='utf-8') as file:
            lector = csv.reader(file)
            next(lector)  # Saltar encabezado
            for fila in lector:
                if len(fila) >= 4:  # Asegurar que la fila tiene datos
                    projectes.append({
                        "nom_projecte": fila[0],
                        "contingut": fila[1],
                        "usuario": fila[2],
                        "asignatura": fila[3],
                        "notes": fila[4]
                    })
    except FileNotFoundError:
        projectes = []
    # Cargar proyectos según el rol del usuario
    proyectos = cargar_proyectos_home()

    # Almacenar los proyectos en la sesión para usarlos en otras rutas
    session['proyectos'] = proyectos

    # Devolvemos la plantilla con los proyectos
    return render_template("home.html", proyectos=proyectos, usuario=session["usuario"], projectes=projectes)

@app.route("/guardar_y_redirigir", methods=["GET", "POST"])
@login_required
def guardar_y_redirigir():
    # Obtener los proyectos según el rol del usuario
    proyectos = cargar_projectes()

    # Guardamos los proyectos en la sesión (para pasarlos a la página de home)
    session['proyectos'] = proyectos

    # Redirigimos al usuario a la página de home
    return redirect(url_for('home'))  # Redirige a la página /home


# Ruta para la página principal de proyectos
@app.route("/indexprojectes", methods=["GET", "POST"])
@login_required
def indexprojectes():
    # Cargar proyectos siempre desde el archivo CSV
    proyectos = cargar_projectes()

    if request.method == "POST":
        # Obtener el proyecto seleccionado por el usuario
        proyecto_seleccionado = request.form.get("proyecto")
        if proyecto_seleccionado:
            return redirect(url_for('projecte', proyecto=proyecto_seleccionado))
        else:
            # En caso de que no se haya seleccionado un proyecto (por alguna razón)
            return render_template("indexprojectes.html", proyectos=proyectos, error="Por favor, selecciona un proyecto.")

    return render_template("indexprojectes.html", proyectos=proyectos)


# Función para generar el PDF del proyecto
def generar_pdf_projecte(proyecto, output_pdf):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    y_position = height - 50

    # Configuramos la fuente y el tamaño de letra
    c.setFont("Helvetica", 12)

    # Título del proyecto
    c.drawString(100, y_position, f"Proyecto: {proyecto[0]}")
    y_position -= 20
    
    # Contenido del proyecto
    c.drawString(100, y_position, f"Contenido: {proyecto[1]}")
    y_position -= 40

    # Guardamos el archivo PDF
    c.save()

# Función para mostrar los detalles del proyecto y permitir la descarga del PDF
@app.route('/projecte/<proyecto>', methods=["GET", "POST"])
def projecte(proyecto):
    proyecto_encontrado = None
    with open('projectes.csv', newline='', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector)  # Saltar encabezado
        for fila in lector:
            if len(fila) > 0 and fila[0] == proyecto:
                proyecto_encontrado = fila  # Guardamos la fila del proyecto encontrado
                break  # Terminamos el ciclo si encontramos el proyecto

    # Verificamos si encontramos el proyecto
    if proyecto_encontrado:
        if request.method == "POST":
            # Nombre del archivo PDF será el nombre del proyecto
            output_pdf = f"{proyecto}.pdf"  # Usamos el nombre del proyecto como nombre del archivo PDF
            
            # Generamos el PDF
            generar_pdf_projecte(proyecto_encontrado, output_pdf)
            
            # Enviar el archivo PDF al usuario para su descarga
            return send_file(output_pdf, as_attachment=True)
        
        # Si la petición es GET, mostrar la vista con los detalles del proyecto
        return render_template("projecte.html", proyecto=proyecto_encontrado)
    else:
        return f"Proyecto '{proyecto}' no encontrado.", 404

@app.route("/canviarcontra", methods=["GET", "POST"])
@professor_required
def canviarcontra():
    segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if request.method == "POST":
        usuari=request.form["usuari"]
        nova = request.form["nova"]
        confirmar = request.form["confirmar"]
        nou = []
        trobat = False
        if nova != confirmar:
            return render_template("canviarcontra.html", mensaje="Las contraseñas no coinciden.", usuario=session["usuario"])

        # Validar si la nueva contraseña es segura
        if not re.match(segura, nova):
            return render_template("canviarcontra.html", mensaje="La contraseña no es segura. Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.", usuario=session["usuario"])

         
        with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)    
            for fila in lectura:
                if fila["usuario"] == usuari:
                    fila["contraseña"] = nova  
                    trobat = True
                nou.append(fila)

        if not trobat:
            return render_template("canviarcontra.html", mensaje="Usuario no encontrado.", usuario=session["usuario"])
        
        with open("dadespersonals.csv", mode="w", newline="", encoding="utf-8") as archivo:
            fieldnames  = ["login", "usuario" , "contraseña" , "nom" , "cognom" , "edat" , "telefon", "rol" , "placa_fixa" , "identificador_alumne"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames )
            writer.writeheader()
            writer.writerows(nou)
        return render_template("canviarcontra.html", mensaje="Contraseña cambiada exitosamente.", usuario=session["usuario"])
    return render_template("canviarcontra.html", usuario=session["usuario"])


@app.route("/notes", methods=["GET", "POST"])
@professor_required
def notes():
    if request.method == "POST":
        projectes = cargar_projectes_notes()  # Aquí debes definir esta función para cargar los proyectos
        datos = []
        nota = request.form["nota"]  # Obtiene la nueva nota
        buscusuari = request.form["buscusuari"]  # El usuario que está buscando
        buscprojecte = request.form["buscprojecte"]  # El proyecto a modificar
        asignatura = request.form["buscasignatura"]  # La asignatura del proyecto
        proyectos_actualizados = []

        # Abrir el archivo y cargar los proyectos
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                datos.append({
                    "usuario": fila["usuario"],
                    "Nomprojecte": fila["Nomprojecte"],
                    "asignatura": fila["asignatura"],
                    "contenido": fila.get("contingut", "No especificado"),
                    "notes": fila.get("notes", "No asignada")  # Mostrar la nota si existe
                })
        
        # Abrir los proyectos nuevamente para modificar la nota si coincide con los criterios
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                if fila["usuario"] == buscusuari and fila["asignatura"] == asignatura and fila["Nomprojecte"] == buscprojecte:
                    fila["notes"] = nota  # Modificar la nota del proyecto
                proyectos_actualizados.append(fila)
        
        # Guardar los proyectos con las nuevas notas
        with open("projectes.csv", mode="w", encoding="utf-8", newline="") as archivo:
            fieldnames = ["Nomprojecte", "contingut", "usuario", "asignatura", "notes"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(proyectos_actualizados)
        
        # Mostrar los proyectos actualizados
        return render_template("notes.html", datos=datos, usuario=session["usuario"], projectes=projectes)

    # Si la petición es GET, solo mostrar los proyectos
    else:
        projectes = cargar_projectes_notes()  # Cargar los proyectos (asegurate de que esta función esté definida)
        datos = []
        
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                datos.append({
                    "usuario": fila["usuario"],
                    "Nomprojecte": fila["Nomprojecte"],
                    "asignatura": fila["asignatura"],
                    "contenido": fila.get("contingut", "No especificado"),
                    "notes": fila.get("notes", "No asignada")
                })

        return render_template("notes.html", datos=datos, usuario=session["usuario"], projectes=projectes)


@app.route("/projectes", methods=["GET", "POST"])
@login_required
def projectes():
    if request.method == "POST":
        usuario=session["usuario"]
        Nomprojecte = request.form["Nomprojecte"]
        contingut = request.form["contingut"]
        asignatura = request.form["asignatura"]
        notes = "Per evaluar"
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == usuario and fila["Nomprojecte"] == Nomprojecte and fila["asignatura"] == asignatura:
                    return render_template("projectes.html", mensaje="El projecte ja ha sigut creat", usuario=session["usuario"])
                
        with open("projectes.csv", mode="a", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow([Nomprojecte,contingut,usuario,asignatura,notes])
            return render_template("projectes.html", mensaje="Creado", usuario=session["usuario"])
    return render_template("projectes.html", usuario=session["usuario"])


@app.route("/mostraprojectes", methods=["GET", "POST"])
@login_required
def mostraprojectes():
    datos = []
    if request.method == "POST":
        buscasignatura = request.form.get("buscasignatura")
        # Filtrar proyectos por asignatura
        
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                if fila["asignatura"].strip().lower() == buscasignatura.strip().lower():
                    datos.append({
                        "usuario": fila["usuario"],
                        "Nomprojecte": fila["Nomprojecte"],
                        "asignatura": fila["asignatura"],
                        "contenido": fila.get("contingut", "No especificado"),
                        "notes": fila.get("notes", "No asignada")  # Mostrar la nota si existe
                    })       
    return render_template("mostraprojectes.html", datos=datos, usuario=session["usuario"])

if __name__ == "__main__":
    app.run(debug=True)