from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
import re
import csv
import os

app = Flask(__name__)
app.secret_key = "clave_secreta_segura"  # Necesaria para sesiones

# Función para verificar credenciales desde el CSV
def verificar_credenciales(usuario, contraseña):
    with open("usuarios.csv", mode="r", encoding="utf-8") as archivo:
        lector = csv.DictReader(archivo)
        for fila in lector:
            if fila["usuario"] == usuario and fila["contraseña"] == contraseña:
                return "admin" if fila["admin"] == "1" else "user"  # Devuelve el rol del usuario
    return False  # Si no coincide ninguna credencial
'''
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        rol = verificar_credenciales(usuario, contraseña)
        #Proces per revisar si l'usuari té rol administrador tenint en conte si al camp de admin CSV es 1
        
        if rol: 
            session["usuario"] = usuario  # Guarda sesión
            return render_template("homeadmin.html", usuario=session["usuario"]) if rol == "admin" else render_template("home.html", usuario=session["usuario"])
        else:
            return render_template("login.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("login.html")  # Muestra el formulario de login'''

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        rol = verificar_credenciales(usuario, contraseña)  # Esta función debe devolver el rol del usuario

        if rol:  # Si rol es válido (por ejemplo, "admin" o "usuario")
            session["usuario"] = usuario  # Guarda el nombre de usuario en la sesión
            session["rol"] = rol  # Guarda el rol del usuario en la sesión (admin o usuario normal)

            # Si el rol es admin, redirige a la página del admin, si no, a la página normal
            if rol == "admin":
                return render_template("homeadmin.html", usuario=session["usuario"])
            else:
                return render_template("home.html", usuario=session["usuario"])
        else:
            return render_template("login.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("login.html")

def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'usuario' not in session or session.get('rol') != 'admin':
            return render_template("403.html"), 403
        return f(*args, **kwargs)
    return wrap


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        segura = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        ara = session["usuario"]
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        admin = request.form["admin"]        
        #Usem un a expresio regular per a asegurarnos que la contraseña sigui segura
        if not re.match(segura, contraseña):
            return render_template("signup.html", mensaje="La contraseña no es segura. Debe tener al menos 8 caracteres, una mayúscula, una minúscula, un número y un carácter especial.")

        archivo_existe = os.path.exists("usuarios.csv")
        
        with open("usuarios.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["usuario"] == usuario:
                    return render_template("signup.html", mensaje="El usuario ya existe")
                
        
        # Si el archivo no existe, se crea con encabezados
        with open("usuarios.csv", mode="a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            
            # Escribir los encabezados solo si el archivo no existe
            if not archivo_existe:
                escritor.writerow(["usuario", "contraseña"])
            
            # Escribir el nuevo usuario amb el nom de usuari, la contraseña, si es admin(1) o no (0) i el usuari que l'ha creat
            if admin == "1":
                escritor.writerow([usuario, contraseña, 1,ara])
            else:
                escritor.writerow([usuario, contraseña, 0,ara])

        # Redirigir al login después de registrar el usuario
        return redirect(url_for("homeadmin"))
        
    return render_template("signup.html")


'''@app.route('/projectes')
@admin_required
def blockProj():
    return render_template('projectes.html')

@app.route('/notes')
@admin_required
def blockNotes():
    return render_template('notes.html')

@app.route('/homeadmin')
@admin_required
def blockSignup():
    return render_template('homeadmin.html')'''

@app.route("/convertir", methods=["GET", "POST"])
def convertir():
    if request.method == "POST":
        lletra = request.form["lletra"]
        mida = request.form ["mida"]
        
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

         
        with open("usuarios.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)    
            for fila in lectura:
                if fila["usuario"] == usuari:
                    fila["contraseña"] = nova  # Agregar la nota al proyecto
                    trobat = True
                nou.append(fila)

        if not trobat:
            return render_template("cambiarcontra.html", mensaje="Usuario no encontrado.")
        
        with open("usuarios.csv", mode="w", newline="", encoding="utf-8") as archivo:
            fieldnames  = ["usuario" , "contraseña" , "admin" , "creat per"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames )
            writer.writeheader()
            writer.writerows(nou)
        return render_template("cambiarcontra.html", mensaje="Contraseña cambiada exitosamente.")
    return render_template("cambiarcontra.html")

@app.route("/notes", methods=["GET", "POST"])
def notes():
    if request.method == "POST":
        nota = request.form["nota"]  # Campo de texto donde el admin puede poner la nota
        usuario=request.form["usuario"]  # Usuario del proyecto al que agregar la nota
        asignatura = request.form["buscasignatura"]
        proyectos_actualizados = []
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
           
            for fila in lectura:
                if fila["usuario"] == usuario and fila["asignatura"] == asignatura:
                    fila["notes"] = nota  # Agregar la nota al proyecto
                proyectos_actualizados.append(fila)
        # Guardar los proyectos con las nuevas notas en el archivo
        with open("projectes.csv", mode="w", encoding="utf-8", newline="") as archivo:
            fieldnames = ["Nomprojecte", "contingut" , "usuario", "asignatura" , "notes"]
            writer = csv.DictWriter(archivo, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(proyectos_actualizados)
    return render_template("notes.html") 



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

@app.route("/afegir_dades_personals", methods=["GET", "POST"])
#@admin_required
def afegir_dades_personals():
    if request.method == "POST":
        usuario = request.form["usuario"]
        rol = request.form["rol"]  # "professor" o "alumne"
        nom = request.form["nom"]
        cognom = request.form["cognom"]
        edat = request.form["edat"]
        telefon = request.form["telefon"]
        placa_fixa = request.form.get("placa_fixa", "") if rol == "professor" else ""
        identificador_alumne = request.form.get("identificador_alumne", "") if rol == "alumne" else ""

        # Comprovar si ja existeixen dades personals d'aquest usuari
        existeix = False
        dades_actualitzades = []
        if os.path.exists("dades_personals.csv"):
            with open("dades_personals.csv", mode="r", encoding="utf-8") as fitxer:
                lector = csv.DictReader(fitxer)
                for fila in lector:
                    if fila["usuario"] == usuario:
                        existeix = True
                        fila.update({
                            "rol": rol,
                            "nom": nom,
                            "cognom": cognom,
                            "edat": edat,
                            "telefon": telefon,
                            "placa_fixa": placa_fixa,
                            "identificador_alumne": identificador_alumne
                        })
                    dades_actualitzades.append(fila)

        if existeix:
            # Actualitzar dades
            with open("dades_personals.csv", mode="w", newline="", encoding="utf-8") as fitxer:
                fieldnames = ["usuario", "rol", "nom", "cognom", "edat", "telefon", "placa_fixa", "identificador_alumne"]
                writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(dades_actualitzades)
            missatge = "Dades personals actualitzades correctament."
        else:
            # Afegir nova entrada
            with open("dades_personals.csv", mode="a", newline="", encoding="utf-8") as fitxer:
                fieldnames = ["usuario", "rol", "nom", "cognom", "edat", "telefon", "placa_fixa", "identificador_alumne"]
                writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
                if fitxer.tell() == 0:
                    writer.writeheader()
                writer.writerow({
                    "usuario": usuario,
                    "rol": rol,
                    "nom": nom,
                    "cognom": cognom,
                    "edat": edat,
                    "telefon": telefon,
                    "placa_fixa": placa_fixa,
                    "identificador_alumne": identificador_alumne
                })
            missatge = "Dades personals afegides correctament."

        return render_template("dades_personals.html", missatge=missatge)

    return render_template("dades_personals.html")




@app.route("/home")
def home():
    if "usuario" in session:
        return render_template("home.html", usuario=session["usuario"])
    return redirect(url_for("login"))

@app.route("/homeadmin")
def homeadmin():
    print(f"Valor de admin: {session.get('admin')}")

    return render_template("homeadmin.html", usuario=session["usuario"])

@app.route("/logout")
def logout():
    session.clear()  # Eliminar toda la sesión (usuario, rol, etc.)
    return redirect(url_for("login"))  # Redirigir al login

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

            return render_template("projectes.html", mensaje="Creado")
    return render_template("projectes.html")


#Start Program
if __name__ == "__main__":
    app.run(debug=True) #afegir host="ip"
