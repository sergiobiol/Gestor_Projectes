from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps

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

    return render_template("login.html")  # Muestra el formulario de login
'''
def admin_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'usuario' not in session or session.get('rol') != 'admin':
            return render_template("403.html"), 403
        return f(*args, **kwargs)
    return wrap
'''
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        admin = request.form["admin"]        
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
            
            # Escribir el nuevo usuario
            if admin == "1":
                escritor.writerow([usuario, contraseña, 1])
            else:
                escritor.writerow([usuario, contraseña, 0])

        # Redirigir al login después de registrar el usuario
        return redirect(url_for("login"))
        
    return render_template("signup.html")

'''@app.route('/projectes')
@admin_required
def blockProj():
    return render_template('projectes.html')'''

'''@app.route('/notes')
@admin_required
def blockNotes():
    return render_template('notes.html')

@app.route('/homeadmin')
@admin_required
def blockSignup():
    return render_template('homeadmin.html')'''


@app.route("/mostraprojectes", methods=["GET", "POST"])
def mostraprojectes():
    if request.method == "POST":
        # Verificar si el usuario es admin (comprobamos si admin es True)
        usuario = session.get("usuario")
        admin = session.get("admin")  # Asumimos que "admin" está almacenado como True/False en la sesión

        # Convertir `admin` a 1 si es True (y 0 si es False)
        if admin:
            admin = 1
        else:
            admin = 0

        # Obtener datos del formulario
        buscasignatura = request.form.get("buscasignatura")
        nota = request.form.get("nota")  # Campo de texto donde el admin puede poner la nota
        usuario_proyecto = request.form.get("usuario_proyecto")  # Usuario del proyecto al que agregar la nota

        # Si es admin, agregar la nota al proyecto correspondiente
        if admin == 1:  # Si el usuario es admin, podemos agregar la nota
            # Abrir el archivo CSV y actualizar la información
            proyectos_actualizados = []
            with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
                lectura = csv.DictReader(archivo)
                for fila in lectura:
                    if fila["usuario"] == usuario_proyecto:
                        fila["nota"] = nota  # Agregar la nota al proyecto
                    proyectos_actualizados.append(fila)

            # Guardar los proyectos con las nuevas notas en el archivo
            with open("projectes.csv", mode="w", encoding="utf-8", newline="") as archivo:
                fieldnames = ["usuario", "Nomprojecte", "asignatura", "contingut", "nota"]
                writer = csv.DictWriter(archivo, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(proyectos_actualizados)

        # Filtrar proyectos por asignatura
        datos = []
        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lectura = csv.DictReader(archivo)
            for fila in lectura:
                if fila["asignatura"].strip().lower() == buscasignatura.strip().lower():
                    datos.append({
                        "usuario": fila["usuario"],
                        "Nomprojecte": fila["Nomprojecte"],
                        "asignatura": fila["asignatura"],
                        "contenido": fila.get("contingut", "No especificado"),
                        "nota": fila.get("nota", "No asignada")  # Mostrar la nota si existe
                    })

        return render_template("mostraprojectes.html", datos=datos)

    return render_template("mostraprojectes.html") 

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
    app.run(host="192.168.221.251" ,debug=True)
