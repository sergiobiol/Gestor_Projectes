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
                return "admin" if fila["admin"] == "1" else "user"  # Devuelve el rol del usuario
    return False  # Si no coincide ninguna credencial

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]

        rol = verificar_credenciales(usuario, contraseña)

        if rol:
            session["usuario"] = usuario  # Guarda sesión
            return render_template("homeadmin.html", usuario=session["usuario"]) if rol == "admin" else render_template("home.html", usuario=session["usuario"])
        else:
            return render_template("login.html", mensaje="Usuario o contraseña incorrectos")

    return render_template("login.html")  # Muestra el formulario de login



@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        usuario = request.form["usuario"]
        contraseña = request.form["contraseña"]
        admin = request.form["admin"]
        comprobar=session["admin"]
        if comprobar== "0":
            return redirect(url_for("home"))
        
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

@app.route("/notes", methods=["GET", "POST"])
def notes():

    return render_template("notes.html")

@app.route("/home")
def home():
    if "usuario" in session:
        return render_template("home.html", usuario=session["usuario"])
    return redirect(url_for("login"))

@app.route("/homeadmin")
def homeadmin():
    return render_template("homeadmin.html", usuario=session["usuario"])

@app.route("/logout")
def logout():
    session.pop("usuario", None)  # Eliminar sesión
    return redirect(url_for("login"))

@app.route("/projectes", methods=["GET", "POST"])
def projectes():
    if request.method == "POST":
        usuario=session["usuario"]
        Nomprojecte = request.form["Nomprojecte"]
        contingut = request.form["contingut"]

        with open("projectes.csv", mode="r", encoding="utf-8") as archivo:
            lector = csv.DictReader(archivo)
            for fila in lector:
                if fila["Nomprojecte"] == Nomprojecte:
                    return render_template("projectes.html", mensaje="El projecte ja ha sigut creat")
                else:
                    with open("projectes.csv", mode="a", encoding="utf-8") as archivo:
                        escritor = csv.writer(archivo)
                        escritor.writerow([usuario,Nomprojecte,contingut])

                    return render_template("projectes.html", mensaje="Creado")
    return render_template("projectes.html")





if __name__ == "__main__":
    app.run(host="192.168.191.89" ,debug=True)
