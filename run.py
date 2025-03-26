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
    #herencia
    def __init__(self, usuario, nom, cognom, edat, telefon, placa_fixa):
        super().__init__(usuario, nom, cognom, edat, telefon)
        self.placa_fixa = placa_fixa

    #polimorfisme
    def to_dict(self):
        data = super().to_dict()
        data["placa_fixa"] = self.placa_fixa
        return data

class Alumne(Usuari):
    #herencia
    def __init__(self, usuario, nom, cognom, edat, telefon, identificador_alumne):
        super().__init__(usuario, nom, cognom, edat, telefon)
        self.identificador_alumne = identificador_alumne
    
    #polimorfisme
    def to_dict(self):
        data = super().to_dict()
        data["identificador_alumne"] = self.identificador_alumne
        return data

#funcio per a llegir els usuaris
def llegir_usuaris():
    usuaris = {}
    if os.path.exists("dadespersonals.csv"):
        with open("dadespersonals.csv", mode="r", encoding="utf-8") as fitxer:
            lector = csv.DictReader(fitxer)
            for fila in lector:
                usuaris[fila["usuario"]] = fila
    return usuaris

#Verifica el usuari i contrasenya en el archiu CSV i torna el rol si es valid     
def verificar_credenciales(user, password):
    try:
        with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == user and fila["contraseña"] == password:
                    return fila["rol"]  # retorna el rol de l'usuari
    except FileNotFoundError:
        print("Error: L'arxiu 'dadespersonals.csv' no existeix.")
    return None  # retorna None si no troba l'usuari o la contrasenya és incorrecta

def es_professor():
    usuario = session.get("usuario")  # obte el usuari de la sesio   
    usuaris = llegir_usuaris()  # llegeix les dades del csv                              
    
    datos_usuario = usuaris.get(usuario, {})
    
    es_rol_professor = datos_usuario.get("rol") == "professor"
    
    return es_rol_professor

def login_required(f):
    @wraps(f)  # aquesta linea evita duplicacions             
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def professor_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("usuario"):  # verifiquem di hi ha un usuari en la sesio
            return redirect(url_for("login"))  # redirigix al login si no hi hagues usuari
        if not es_professor():
            return redirect(url_for("error403"))
        return f(*args, **kwargs)
    return wrapped

# busca l'ultim identificador de alumne i suma 1 a un format de 3 digits
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

# carguem els usuaris
def cargar_usuaris():
    usuaris = []
    with open("dadespersonals.csv", newline="", encoding="utf-8") as file:
        lector = csv.reader(file)
        next(lector)  # saltar capçalera 
        for fila in lector:
            if len(fila) < 10:
                continue  # saltar files incompletes
            login, usuario, contraseña, nom, cognom, edat, telefon, rol, placa_fixa, identificador_alumne = fila

            if rol.lower() == "professor":
                usuario_obj = Professor(usuario, nom, cognom, edat, telefon, placa_fixa)
            elif rol.lower() == "alumne":
                usuario_obj = Alumne(usuario, nom, cognom, edat, telefon, identificador_alumne)
            else:
                continue  # si el rol no es valid l'ignorem    
            usuaris.append(usuario_obj.to_dict())

    return usuaris


# usem el login per a detectar si es alumne o profesor,per a sabre si es valid la 
# entrada i si el usuari acaba de entrar per primera vegada, l'enviara directament a afegir dades personals
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contra = request.form["contraseña"]
        rol = verificar_credenciales(usuario, contra)

        if rol in ["professor", "alumne"]:
            session["usuario"] = usuario  # guardem el nom de l'usuari a la sessió    
            session["rol"] = rol

            login_valido = False  # determinem si el login és vàlid o no        
            with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                for fila in lector:
                    if fila["usuario"] == usuario and fila.get("login") == "1":
                        login_valido = True  # si trobem login 1, significa que ja ha entrat abans
                        break
            
            # Redirigir segons l'estat del login
            if login_valido:
                return redirect(url_for('home'))
            else:
                return render_template("dadespersonals.html", usuario=session["usuario"])

        else:
            return render_template("login.html", mensaje="Usuari o contrasenya incorrectes")

    return render_template("login.html")


#logout per a tancar la sesio
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

#pagina d'error
@app.route("/403")
def error403():
    return render_template("403.html"), 403

# funcio per a afegir les dades personals
@app.route("/afegir_dades_personals", methods=["GET", "POST"])
@login_required
def afegir_dades_personals():
    if "usuario" not in session:
        return redirect(url_for('login'))  # protegeix per si no hi ha usuari a la sesio
    #CREC Q NO CAL

    usuario_sessio = session["usuario"]
    usuaris = llegir_usuaris()  # ha de retornar la clau 'usuario'    

    if request.method == "POST":
        # recull les dades del formulari                        
        try:
            nom = request.form["nom"]
            cognom = request.form["cognom"]
            edat = request.form["edat"]
            telefon = request.form["telefon"]
        except KeyError as e:
            return render_template("dadespersonals.html", missatge=f"Error: Falta el camp {e} al formulari.")

        # actualitza els camps editables
        usuaris[usuario_sessio]["nom"] = nom
        usuaris[usuario_sessio]["cognom"] = cognom
        usuaris[usuario_sessio]["edat"] = edat
        usuaris[usuario_sessio]["telefon"] = telefon

        # cambia el camp login a 1 per a que si torna a iniciar sesio no el porti a la pagina afegir dades
        usuaris[usuario_sessio]["login"] = "1"

        # guardem tots els camps al archiu csv    
        with open("dadespersonals.csv", mode="w", newline="", encoding="utf-8") as fitxer:
            fieldnames = ["login", "usuario", "contraseña", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"]
            writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(usuaris.values())

    return render_template("home.html", usuario=session["usuario"])


# funcio per a registrar usuaris
@app.route("/registrar", methods=["GET", "POST"])
@professor_required
def registrar():
    rol = request.args.get("rolusuari")  # capturem el rol en GET
    mensaje = None #CREC NO CAL

    if request.method == "POST":
        #creem l'expresio regular per a controlar que la contrasenya creada sigui segura
        segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        usuario = request.form["usuario"]
        contraseña = request.form["contrasena"]
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        edad = request.form["edad"]
        telefono = request.form["telefono"]
        professor = request.form.get("professor")  

        # si el rol no a pasat per GET intenta capturarlo desde POST
        if not rol:
            rol = request.form.get("rolusuari")

        if not rol:
            return render_template("registrar.html", mensaje="Debes seleccionar un rol antes de registrarte.")
        #ESTOS DE DALT CREC Q NO CAL

        # validem la seguretat de la contrasenya
        if not re.match(segura, contraseña):
            return render_template("registrar.html", mensaje="La contraseña no es segura.")

        # verifiquem si el usuari ya existeix
        archivo_existe = os.path.exists("dadespersonals.csv")
        if archivo_existe:
            with open("dadespersonals.csv", mode="r", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                for fila in lector:
                    if fila["usuario"] == usuario:
                        return render_template("registrar.html", mensaje="El usuario ya existe.")

        # generem el identificador d'alumne si es alumne
        identificador_alumne = generar_identificador_alumne() if rol == "alumne" else ""
        # si es professor marca el identificador com a si
        identificador_professor = "SI" if rol == "professor" else ""
        # escribim al csv
        with open("dadespersonals.csv", mode="a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if not archivo_existe:
                escritor.writerow(["login", "usuario", "contrasena", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"])
            
            escritor.writerow([
                0, usuario, contraseña, nombre, apellido, edad, telefono, rol, identificador_professor, identificador_alumne
            ])

        return redirect(url_for("home"))

    return render_template("registrar.html", usuario=session.get("usuario", ""), rol=rol, mensaje=mensaje)


# funcio per a cargar projectes desde e archiu csv 
@app.route("/usuaris")
def listar_usuaris():
    usuaris = cargar_usuaris()  # Cambié de usuari a usuaris
    return render_template("usuaris.html", usuaris=usuaris, usuario=session["usuario"])  # Aquí también usuaris


def carregar_projectes(com_notes=False):
    projectes = []
    try:
        with open('projectes.csv', newline='', encoding='utf-8') as file:
            lector = csv.reader(file)
            next(lector)  # Saltem la capçalera
            for fila in lector:
                if len(fila) >= 1:
                    projecte = {
                        "nom_projecte": fila[0],
                        "contingut": fila[1],
                        "usuario": fila[2],
                        "asignatura": fila[3],
                        "notes": fila[4] if com_notes and len(fila) > 1 else "" 
                    }
                    projectes.append(projecte)
    except FileNotFoundError:
        print("Error: L'arxiu 'projectes.csv' no existeix.")

    return projectes


@app.route("/cargarproyectos", methods=["GET", "POST"])
@login_required
def cargar_proyectos_home():
    proyectos = []
    usuario = session.get('usuario')
    rol = session.get('rol')

    projectes_notes = carregar_projectes(com_notes=True)
    for projecte in projectes_notes:
        if isinstance(projecte, dict):  # Comprovem que sigui un diccionari
            if rol == 'professor' or (rol == 'alumne' and projecte["usuario"] == usuario):
                proyectos.append(projecte)
    
    return proyectos

@app.route("/home")
@login_required
def home():
    projectes = carregar_projectes(com_notes=True)
    proyectos = cargar_proyectos_home()
    session['proyectos'] = proyectos
    return render_template("home.html", proyectos=proyectos, usuario=session["usuario"], projectes=projectes)

@app.route("/guardar_y_redirigir", methods=["GET", "POST"])
@login_required
def guardar_y_redirigir():
    proyectos = carregar_projectes()
    session['proyectos'] = proyectos
    return redirect(url_for('home'))

# ruta per a la pagina de projectes de crear pdf
@app.route("/indexprojectes", methods=["GET", "POST"])
@login_required
def indexprojectes():
    # Carreguem els projectes des del arxiu csv
    proyectos = carregar_projectes()  # Assegura't que carregar_projectes() retorni una llista de projectes.
    
    if request.method == "POST":
        # Obtenim el projecte seleccionat per l'usuari
        proyecto_seleccionado = request.form.get("proyecto")
        
        if proyecto_seleccionado:
            # Redirigir a la pàgina del projecte seleccionat
            return redirect(url_for('projecte', proyecto=proyecto_seleccionado))
        else:
            # Si no s'ha seleccionat un projecte, mostrar missatge d'error
            return render_template("indexprojectes.html", proyectos=proyectos, error="Per favor, selecciona un projecte.")

    return render_template("indexprojectes.html", proyectos=proyectos, usuario=session["usuario"])


# generem el pdf del projecte              

def generar_pdf_projecte(proyecto, output_pdf, title_size, content_size, font_name):
    c = canvas.Canvas(output_pdf, pagesize=letter)
    width, height = letter
    y_position = height - 50  

    c.setFont(font_name, title_size)
    c.drawString(100, y_position, f"Projecte: {proyecto[0]}")  

    y_position -= 20  

    c.setFont(font_name, content_size)
    c.drawString(100, y_position, f"Contingut: {proyecto[1]}") 

    c.save()
    print(f"PDF generat: {output_pdf}")

# funcio per a mostrar els detalls del projecte i permetre la descarga del pdf
# Ruta per mostrar els detalls del projecte i permetre la descàrrega del PDF
@app.route('/projecte/<proyecto>', methods=["GET", "POST"])
def projecte(proyecto):
    proyecto_encontrado = None

    with open("projectes.csv", newline='', encoding='utf-8') as file:
        lector = csv.reader(file)
        next(lector) 
        for fila in lector:
            if len(fila) > 1 and fila[0] == proyecto:
                proyecto_encontrado = fila
                break

    if proyecto_encontrado:
        if request.method == "POST":
            title_size = int(request.form.get('title_size', 16))  
            content_size = int(request.form.get('content_size', 12))  
            font_name = "Helvetica"  
            output_pdf = os.path.join("static/pdf", f"{proyecto}.pdf")
            generar_pdf_projecte(proyecto_encontrado, output_pdf, title_size, content_size, font_name)

            return send_file(output_pdf, as_attachment=True)

        return render_template("projecte.html", proyecto=proyecto_encontrado)
    else:
        return f"Projecte '{proyecto}' no trobat.", 404


#funcio per a cambiar la contraseña
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

        # validem si la nova contraseña es segura
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


#funcio per a modificar les notes i mostrar tots els projectes
@app.route("/notes", methods=["GET", "POST"])
@professor_required
def notes():
    if request.method == "POST":
        projectes = carregar_projectes()  # definim la funcio per a cargar projectes             
        datos = []
        nota = request.form["nota"]  # obtenim la nova nota  
        buscusuari = request.form["buscusuari"]  # l'usuari que esta buscant  
        buscprojecte = request.form["buscprojecte"]  # projecte per a modificar
        asignatura = request.form["buscasignatura"]  # adignatura del projecte
        proyectos_actualizados = []

        # obrir archiu i cargar projectes      
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
        
        # obrir projectes novament per a modificar la nota si coincideix amb els criteris
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                if fila["usuario"] == buscusuari and fila["asignatura"] == asignatura and fila["Nomprojecte"] == buscprojecte:
                    fila["notes"] = nota  # modifiquem la nota del projecte
                proyectos_actualizados.append(fila)
        
        # guardem els projectes amb les noves notes 
        with open("projectes.csv", mode="w", encoding="utf-8", newline="") as archivo:
            fieldnames = ["Nomprojecte", "contingut", "usuario", "asignatura", "notes"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(proyectos_actualizados)
        
        # mostrem els projectes actualizats
        return render_template("notes.html", datos=datos, usuario=session["usuario"], projectes=projectes)

    # si la peticio es get nomes mostra els projectes
    else:
        projectes = carregar_projectes()  
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

#funcio per a crear projectes 
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

#funcio per a la pagina mostrar projectes
@app.route("/mostraprojectes", methods=["GET", "POST"])
@login_required
def mostraprojectes():
    datos = []
    if request.method == "POST":
        buscasignatura = request.form.get("buscasignatura")
        # filtrem projectes per asignatura
        
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                if fila["asignatura"].strip().lower() == buscasignatura.strip().lower():
                    datos.append({
                        "usuario": fila["usuario"],
                        "Nomprojecte": fila["Nomprojecte"],
                        "asignatura": fila["asignatura"],
                        "contenido": fila.get("contingut", "No especificado"),
                        "notes": fila.get("notes", "No asignada")  
                    })
                else: 
                    datos.append({
                        "usuario": fila["usuario"],
                        "Nomprojecte": fila["Nomprojecte"],
                        "asignatura": fila["asignatura"],
                        "contenido": fila.get("contingut", "No especificado"),
                        "notes": fila.get("notes", "No asignada")  
                    })

    return render_template("mostraprojectes.html", datos=datos, usuario=session["usuario"])

if __name__ == "__main__":
    app.run(debug=True)