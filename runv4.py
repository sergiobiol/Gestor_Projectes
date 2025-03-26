from flask import Flask, request, render_template, session, redirect, url_for, send_file
from functools import wraps
import csv
import os
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key_123")  # Use environment variable for security

# Constants
CSV_USERS = "dadespersonals.csv"
CSV_PROJECTS = "projectes.csv"
PASSWORD_REGEX = r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"

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

# Helper functions
def read_csv(file_path, mode='r', encoding='utf-8'):
    """Generic CSV reader function."""
    data = []
    if os.path.exists(file_path):
        with open(file_path, mode=mode, encoding=encoding) as file:
            reader = csv.DictReader(file)
            data = [row for row in reader]
    return data

def write_csv(file_path, fieldnames, data, mode='w'):
    """Generic CSV writer function."""
    with open(file_path, mode=mode, newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        if mode == 'w':
            writer.writeheader()
        writer.writerows(data)

def get_user_by_username(username):
    """Get user data by username."""
    users = read_csv(CSV_USERS)
    for user in users:
        if user.get('usuario') == username:
            return user
    return None

def is_professor():
    """Check if current user is a professor."""
    if 'usuario' not in session:
        return False
    user = get_user_by_username(session['usuario'])
    return user and user.get('rol') == 'professor'

def login_required(f):
    """Decorator to ensure user is logged in."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def professor_required(f):
    """Decorator to ensure user is a professor."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_professor():
            return redirect(url_for('error403'))
        return f(*args, **kwargs)
    return decorated_function

def generate_student_id():
    """Generate a new student ID."""
    users = read_csv(CSV_USERS)
    max_id = 0
    for user in users:
        if user.get('rol') == 'alumne' and user.get('identificador_alumne'):
            try:
                current_id = int(user['identificador_alumne'])
                max_id = max(max_id, current_id)
            except ValueError:
                continue
    return str(max_id + 1).zfill(3)

def load_projects(with_notes=False):
    """Load projects from CSV."""
    projects = []
    try:
        with open(CSV_PROJECTS, newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                project = {
                    "Nomprojecte": row.get("Nomprojecte", ""),
                    "contingut": row.get("contingut", ""),
                    "usuario": row.get("usuario", ""),
                    "asignatura": row.get("asignatura", ""),
                    "notes": row.get("notes", "") if with_notes else ""
                }
                projects.append(project)
    except FileNotFoundError:
        print(f"Error: File '{CSV_PROJECTS}' not found.")
    return projects

def generate_pdf(project, output_path, title_size=16, content_size=12, font_name="Helvetica"):
    """Generate PDF from project data."""
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter
    y_position = height - 50
    
    c.setFont(font_name, title_size)
    c.drawString(100, y_position, f"Projecte: {project['Nomprojecte']}")
    
    y_position -= 20
    c.setFont(font_name, content_size)
    c.drawString(100, y_position, f"Contingut: {project['contingut']}")
    
    c.save()

# Routes
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("usuario")
        password = request.form.get("contraseña")
        
        user = get_user_by_username(username)
        if user and user.get('contraseña') == password:
            session['usuario'] = username
            session['rol'] = user.get('rol')
            
            if user.get('login') == '1':
                return redirect(url_for('home'))
            return render_template("dadespersonals.html", usuario=username)
        
        return render_template("login.html", mensaje="Usuari o contrasenya incorrectes")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/403")
def error403():
    return render_template("403.html"), 403

@app.route("/afegir_dades_personals", methods=["GET", "POST"])
@login_required
def afegir_dades_personals():
    if request.method == "POST":
        users = read_csv(CSV_USERS)
        updated_users = []
        username = session['usuario']
        
        for user in users:
            if user['usuario'] == username:
                user.update({
                    'nom': request.form.get('nom'),
                    'cognom': request.form.get('cognom'),
                    'edat': request.form.get('edat'),
                    'telefon': request.form.get('telefon'),
                    'login': '1'
                })
            updated_users.append(user)
        
        write_csv(CSV_USERS, updated_users[0].keys(), updated_users)
        return redirect(url_for('home'))
    
    return render_template("dadespersonals.html", usuario=session['usuario'])

@app.route("/registrar", methods=["GET", "POST"])
@professor_required
def registrar():
    role = request.args.get("rolusuari") or request.form.get("rolusuari")
    
    if request.method == "POST":
        if not re.match(PASSWORD_REGEX, request.form.get('contrasena')):
            return render_template("registrar.html", mensaje="La contraseña no es segura.", rol=role)
        
        users = read_csv(CSV_USERS)
        if any(u['usuario'] == request.form['usuario'] for u in users):
            return render_template("registrar.html", mensaje="El usuario ya existe.", rol=role)
        
        new_user = {
            'login': '0',
            'usuario': request.form['usuario'],
            'contraseña': request.form['contrasena'],
            'nom': request.form['nombre'],
            'cognom': request.form['apellido'],
            'edat': request.form['edad'],
            'telefon': request.form['telefono'],
            'rol': role,
            'placa_fixa': 'SI' if role == 'professor' else '',
            'identificador_alumne': generate_student_id() if role == 'alumne' else ''
        }
        
        write_csv(CSV_USERS, new_user.keys(), [new_user], mode='a')
        return redirect(url_for('home'))
    
    return render_template("registrar.html", rol=role)

@app.route("/usuaris")
@login_required
def listar_usuaris():
    users = read_csv(CSV_USERS)
    user_objects = []
    
    for user in users:
        if user.get('rol') == 'professor':
            user_obj = Professor(
                user['usuario'],
                user['nom'],
                user['cognom'],
                user['edat'],
                user['telefon'],
                user.get('placa_fixa', '')
            )
        elif user.get('rol') == 'alumne':
            user_obj = Alumne(
                user['usuario'],
                user['nom'],
                user['cognom'],
                user['edat'],
                user['telefon'],
                user.get('identificador_alumne', '')
            )
        else:
            continue
            
        user_objects.append(user_obj.to_dict())
    
    return render_template("usuaris.html", usuaris=user_objects, usuario=session["usuario"])

@app.route("/home")
@login_required
def home():
    projects = load_projects(with_notes=True)
    user_projects = [
        p for p in projects 
        if session['rol'] == 'professor' or p['usuario'] == session['usuario']
    ]
    return render_template("home.html", proyectos=user_projects, usuario=session['usuario'])

@app.route("/indexprojectes", methods=["GET", "POST"])
@login_required
def indexprojectes():
    projects = load_projects()
    
    if request.method == "POST":
        selected = request.form.get("proyecto")
        if selected:
            return redirect(url_for('projecte', proyecto=selected))
        return render_template("indexprojectes.html", proyectos=projects, error="Selecciona un projecte.")
    
    return render_template("indexprojectes.html", proyectos=projects, usuario=session['usuario'])

@app.route('/projecte/<proyecto>', methods=["GET", "POST"])
def projecte(proyecto):
    projects = load_projects()
    project = next((p for p in projects if p['Nomprojecte'] == proyecto), None)
    
    if not project:
        return f"Projecte '{proyecto}' no trobat.", 404
    
    if request.method == "POST":
        pdf_path = os.path.join("static/pdf", f"{proyecto}.pdf")
        generate_pdf(
            project,
            pdf_path,
            int(request.form.get('title_size', 16)),
            int(request.form.get('content_size', 12))
        )
        return send_file(pdf_path, as_attachment=True)
    
    return render_template("projecte.html", proyecto=project)

@app.route("/canviarcontra", methods=["GET", "POST"])
@professor_required
def canviarcontra():
    if request.method == "POST":
        username = request.form['usuari']
        new_pass = request.form['nova']
        confirm = request.form['confirmar']
        
        if new_pass != confirm:
            return render_template("canviarcontra.html", mensaje="Las contraseñas no coinciden.")
        
        if not re.match(PASSWORD_REGEX, new_pass):
            return render_template("canviarcontra.html", mensaje="La contraseña no es segura.")
        
        users = read_csv(CSV_USERS)
        updated = False
        
        for user in users:
            if user['usuario'] == username:
                user['contraseña'] = new_pass
                updated = True
        
        if not updated:
            return render_template("canviarcontra.html", mensaje="Usuario no encontrado.")
        
        write_csv(CSV_USERS, users[0].keys(), users)
        return render_template("canviarcontra.html", mensaje="Contraseña cambiada exitosamente.")
    
    return render_template("canviarcontra.html")

@app.route("/notes", methods=["GET", "POST"])
@professor_required
def notes():
    projects = load_projects(with_notes=True)
    
    if request.method == "POST":
        updated_projects = []
        for project in projects:
            if (project['usuario'] == request.form['buscusuari'] and
                project['asignatura'] == request.form['buscasignatura'] and
                project['Nomprojecte'] == request.form['buscprojecte']):
                project['notes'] = request.form['nota']
            updated_projects.append(project)
        
        write_csv(CSV_PROJECTS, updated_projects[0].keys(), updated_projects)
    
    return render_template("notes.html", datos=projects, usuario=session['usuario'])

@app.route("/projectes", methods=["GET", "POST"])
@login_required
def projectes():
    if request.method == "POST":
        projects = load_projects()
        new_project = {
            'Nomprojecte': request.form['Nomprojecte'],
            'contingut': request.form['contingut'],
            'usuario': session['usuario'],
            'asignatura': request.form['asignatura'],
            'notes': 'Per evaluar'
        }
        
        if any(p['usuario'] == session['usuario'] and 
               p['Nomprojecte'] == new_project['Nomprojecte'] and 
               p['asignatura'] == new_project['asignatura'] 
               for p in projects):
            return render_template("projectes.html", mensaje="El projecte ja existeix")
        
        write_csv(CSV_PROJECTS, new_project.keys(), [new_project], mode='a')
        return render_template("projectes.html", mensaje="Projecte creat")
    
    return render_template("projectes.html")

@app.route("/mostraprojectes", methods=["GET", "POST"])
@login_required
def mostraprojectes():
    projects = load_projects(with_notes=True)
    
    if request.method == "POST":
        subject = request.form.get("buscasignatura", "").strip().lower()
        projects = [p for p in projects if p['asignatura'].strip().lower() == subject]
    
    return render_template("mostraprojectes.html", datos=projects, usuario=session['usuario'])

if __name__ == "__main__":
    app.run(debug=True)