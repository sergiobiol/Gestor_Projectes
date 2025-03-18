from flask import Flask, render_template, request, redirect, url_for, session
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
                return "admin" if fila["administrador"] == "1" else "user"  # Devuelve el rol del usuario
    return False  # Si no coincide ninguna credencial

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        rol = verificar_credenciales(usuario, contraseña)

        if rol:
            session["usuario"] = usuario  # Guarda sesión
            return render_template("homeadmin.html") if rol == "admin" else render_template("home.html")
        else:
            return render_template("login.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("login.html")  # Muestra el formulario de login


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        

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
            escritor.writerow([usuario, contraseña])

        # Redirigir al login después de registrar el usuario
        return redirect(url_for("login"))
        
    return render_template("signup.html")

@app.route("/notes", methods=["GET", "POST"])
def notes():

    return render_template("notes.html")

@app.route("/home")
def home():
    if "usuario" in session:
        return render_template("home.html", usuario=session["usuario"])
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    session.pop("usuario", None)  # Eliminar sesión
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="192.168.221.217" ,debug=True)
