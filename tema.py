from flask import Flask, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "clau_hiper_ultra_mega_secreta_bro_123"

# Simulem la ruta /home perquè coincideixi amb la teva aplicació
@app.route('/home')
def home():
    return redirect('http://localhost:5000/home')  # Redirigeix a la teva aplicació principal

@app.route('/canviar-tema', methods=['GET', 'POST'])
def canviar_tema():
    if request.method == 'POST':
        tema_actual = session.get('tema', 'clar')
        session['tema'] = 'fosc' if tema_actual == 'clar' else 'clar'
        return redirect(url_for('canviar_tema'))
    return render_template('tema.html')

if __name__ == '__main__':
    app.run(port=5001, debug=True)