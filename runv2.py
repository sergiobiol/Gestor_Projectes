from flask import Flask, request, render_template, session, redirect, url_for
from functools import wraps
import csv
import os


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
#
def es_professor():
    usuario = session.get("usuario")
    usuaris = llegir_usuaris()
    return usuaris.get(usuario, {}).get("rol") == "professor"

def login_required(f):
    @wraps(f)  # Afegeix aquesta línia per evitar duplicacions
    def wrapped(*args, **kwargs):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped

def professor_required(f):
    @wraps(f)  # Afegeix aquesta línia per evitar duplicacions
    def wrapped(*args, **kwargs):
        if not es_professor():
            return redirect(url_for("error403"))
        return f(*args, **kwargs)
    return wrapped


@app.route("/403")
def error403():
    return render_template("403.html"), 403

@app.route("/afegir_dades_personals", methods=["GET", "POST"])
@login_required
def afegir_dades_personals():
    usuario_sessio = session["usuario"]
    usuaris = llegir_usuaris()
    
    if request.method == "POST":
        usuario = request.form["usuario"]
        if usuario != usuario_sessio:
            return render_template("dades_personals.html", missatge="No tens permís per modificar aquestes dades.")
        
        rol = request.form["rol"]
        nom = request.form["nom"]
        cognom = request.form["cognom"]
        edat = request.form["edat"]
        telefon = request.form["telefon"]
        
        if rol == "professor":
            placa_fixa = request.form.get("placa_fixa", "")
            nou_usuari = Professor(usuario, nom, cognom, edat, telefon, placa_fixa)
        elif rol == "alumne":
            identificador_alumne = request.form.get("identificador_alumne", "")
            nou_usuari = Alumne(usuario, nom, cognom, edat, telefon, identificador_alumne)
        else:
            return render_template("dades_personals.html", missatge="Rol invàlid")
        
        usuaris[usuario] = nou_usuari.to_dict()
        
        with open("dades_personals.csv", mode="w", newline="", encoding="utf-8") as fitxer:
            fieldnames = ["usuario", "nom", "cognom", "edat", "telefon", "rol", "placa_fixa", "identificador_alumne"]
            writer = csv.DictWriter(fitxer, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(usuaris.values())
        
        return render_template("dades_personals.html", missatge="Dades actualitzades correctament.")
    
    return render_template("dades_personals.html")

@app.route("/")
def home():
    return render_template("login.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        session["usuario"] = request.form["usuario"]
        return redirect(url_for("home"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))

@app.route("/gestionar_projectes")
@login_required
@professor_required
def gestionar_projectes():
    return render_template("gestionar_projectes.html")

if __name__ == "__main__":
    app.run(debug=True)
