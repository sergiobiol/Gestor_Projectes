from flask import Flask, request, render_template, session, redirect, url_for
from functools import wraps
import csv
import os
import re

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"  # Necessari per gestionar sessions

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
    if os.path.exists("dades_personals.csv"):
        with open("dades_personals.csv", mode="r", encoding="utf-8") as fitxer:
            lector = csv.DictReader(fitxer)
            for fila in lector:
                usuaris[fila["usuario"]] = fila
    return usuaris

def verificar_credenciales(usuario, contraseña):
    """Verifica el usuario y contraseña en el archivo CSV y devuelve el rol si es válido."""
    try:
        with open("dades_personals.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == usuario and fila["contraseña"] == contraseña:
                    return fila["rol"]  # Devuelve el rol del usuario
                
    except FileNotFoundError:
        print("Error: El archivo 'dades_personals.csv' no existe.")
    return render_template("login.html", mensaje="Usuario o contraseña incorrectos")  # Si no encuentra el usuario, devuelve False

def es_professor():
    usuario = session.get("usuario")  # Obtiene el usuario de la sesión
    usuaris = llegir_usuaris()  # Lee los datos del CSV (asumimos que devuelve un diccionario)
    
    datos_usuario = usuaris.get(usuario, {})
    
    es_rol_professor = datos_usuario.get("rol") == "professor"
    es_admin = datos_usuario.get("admin") == "1"  # Compara como string, ya que el CSV almacena "1" o "0"
    
    return es_rol_professor or es_admin

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

'''@app.route("/")
def home():
    return render_template("login.html")
'''
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contra = request.form["contraseña"]
        rol = verificar_credenciales(usuario, contra)

        if rol:
            print(rol,"+++++++++++++++++++++")
            session["usuario"] = usuario  # Guarda el nombre de usuario en la sesión
            session["rol"] = rol

            login_valido = False  # Variable para determinar si el login es válido
            # Leer archivo CSV solo una vez
            with open("dades_personals.csv", mode="r", encoding="utf-8") as archivo:
                lector = csv.DictReader(archivo)
                
                for fila in lector:
                    if fila["login"] == "1" and fila["usuario"] == usuario:
                        print("--------------")
                        login_valido = True  # Si encontramos un login válido

            # Ahora que hemos leído el archivo, hacemos las redirecciones
            if login_valido:
                # Si el login es válido, redirigimos según el rol
                if rol == "professor":
                    return render_template("homeadmin.html", usuario=session["usuario"])
                else:
                    return render_template("home.html", usuario=session["usuario"])
            else:
                print("pppppppppppppppppppppp")
                # Si el login no es válido, redirigimos a dades_personals.html
                return render_template("dades_personals.html", usuario=session["usuario"])

        else:
            print("+++++++++++++")
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
            return render_template("dades_personals.html", missatge=f"Error: Falta el camp {e} al formulari.")

        # Actualizar los campos editables
        usuaris[usuario_sessio]["nom"] = nom
        usuaris[usuario_sessio]["cognom"] = cognom
        usuaris[usuario_sessio]["edat"] = edat
        usuaris[usuario_sessio]["telefon"] = telefon

        # Actualizar el campo login a 1 para indicar que ya se editaron los datos
        usuaris[usuario_sessio]["login"] = "1"

        # Guardar todos los campos en el archivo CSV
        with open("dades_personals.csv", mode="w", newline="", encoding="utf-8") as fitxer:
            fieldnames = ["login", "usuario", "contraseña", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"]
            writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(usuaris.values())

        if usuario_sessio == "professor":
            return render_template("homeadmin.html", usuario=session["usuario"])
        else:
            return render_template("home.html", usuario=session["usuario"])

    return render_template()


@app.route("/gestionar_projectes")
@login_required
@professor_required
def gestionar_projectes():
    return render_template("gestionar_projectes.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        professor = request.form["professor"]        
        #Usem un a expresio regular per a asegurarnos que la contraseña sigui segura
        if not re.match(segura, contraseña):
            return render_template("signup.html", mensaje="La contraseña no es segura. Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.")

        archivo_existe = os.path.exists("dades_personals.csv")
        
        with open("dades_personals.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == usuario:
                    return render_template("signup.html", mensaje="El usuario ya existe")
                
        
        # Si el archivo no existe, se crea con encabezados
        with open("dades_personals.csv", mode="a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            
            # Escribir los encabezados solo si el archivo no existe
            if not archivo_existe:
                escritor.writerow(["usuario", "contraseña"])
            
            # Escribir el nuevo usuario amb el nom de usuari, la contraseña, si es admin(1) o no (0) i el usuari que l'ha creat
            if professor == "1":
                escritor.writerow([0,usuario, contraseña,0,0,0,0,"professor",0])
            else:
                escritor.writerow([0,usuario, contraseña,0,0,0,0,"alumne",0])

        # Redirigir al login después de registrar el usuario
        return redirect(url_for("homeadmin"))
        
    return render_template("signup.html")



@app.route("/convertir", methods=["GET", "POST"])
def convertir():
    return render_template("convertirapdf.html")

@app.route("/cambiarcontra", methods=["GET", "POST"])
def cambiarcontra():
    segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    if request.method == "POST":
        usuari = request.form["usuari"]
        nova = request.form["nova"]
        confirmar = request.form["confirmar"]
        nou = []
        trobat = False
        if nova != confirmar:
            return render_template("cambiarcontra.html", mensaje="Las contraseñas no coinciden.")

        # Validar si la nueva contraseña es segura
        if not re.match(segura, nova):
            return render_template("cambiarcontra.html", mensaje="La contraseña no es segura. Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.")

         
        with open("dades_personals.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)    
            for fila in lectura:
                if fila["usuario"] == usuari:
                    fila["contraseña"] = nova  
                    trobat = True
                nou.append(fila)

        if not trobat:
            return render_template("cambiarcontra.html", mensaje="Usuario no encontrado.")
        
        with open("dades_personals.csv", mode="w", newline="", encoding="utf-8") as archivo:
            fieldnames  = ["login", "usuario" , "contraseña" , "nom" , "cognom" , "edat" , "telefon", "rol" , "placa_fixa" , "identificador_alumne"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames )
            writer.writeheader()
            writer.writerows(nou)
        return render_template("cambiarcontra.html", mensaje="Contraseña cambiada exitosamente.")
    return render_template("cambiarcontra.html")


@app.route("/notes", methods=["GET", "POST"])
def notes():
    if request.method == "POST":
        nota = request.form["nota"]  
        buscusuari=request.form["buscusuari"]  
        buscprojecte= request.form["buscprojecte"]
        asignatura = request.form["buscasignatura"]
        proyectos_actualizados = []
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
           
            for fila in lectura:
                if fila["usuario"] == buscusuari and fila["asignatura"] == asignatura and fila["Nomprojecte"] == buscprojecte:
                    fila["notes"] = nota  # Agregar la nota al proyecto
                proyectos_actualizados.append(fila)
        # Guardar los proyectos con las nuevas notas en el archivo
        with open("projectes.csv", mode="w", encoding="utf-8", newline="") as archivo:
            fieldnames = ["Nomprojecte", "contingut" , "usuario", "asignatura" , "notes"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(proyectos_actualizados)
    return render_template("notes.html") 


@app.route("/projectes", methods=["GET", "POST"])
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
                    return render_template("projectes.html", mensaje="El projecte ja ha sigut creat")
                
        with open("projectes.csv", mode="a", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            escritor.writerow([Nomprojecte,contingut,usuario,asignatura,notes])
            print("aaaaaaaaaaaa")
            return render_template("projectes.html", mensaje="Creado")
    return render_template("projectes.html")


@app.route("/homeadmin", methods=["GET", "POST"])
def homeadmin():
    return render_template("homeadmin.html")

@app.route("/home", methods=["GET", "POST"])
def home():
    return render_template("home.html")

@app.route("/mostraprojectes", methods=["GET", "POST"])
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
    return render_template("mostraprojectes.html", datos=datos)




if __name__ == "__main__":
    app.run(host="192.168.221.246", debug=True)
