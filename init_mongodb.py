from pymongo import MongoClient

def init_mongodb():
    try:
        # Connecta a MongoDB
        client = MongoClient("mongodb://localhost:27017/")
        db = client["gestor_projectes"]

        # Crea les col·leccions (si no existeixen)
        comentaris = db["comentaris"]
        revisions = db["revisions"]
        fitxers = db["fitxers"]

        # Insereix exemples per a alguns projectes
        # Projecte "Balatro" (projecte_id: 1)
        comentaris.insert_one({
            "projecte_id": 1,
            "comentaris": [
                {"professor_id": 1, "text": "Bon treball, però pots millorar l'estructura", "data": "2024-02-01"},
                {"professor_id": 1, "text": "Afegeix més exemples pràctics", "data": "2024-02-03"}
            ]
        })
        revisions.insert_one({
            "projecte_id": 1,
            "versions": [
                {"data": "2024-01-15", "descripcio": "Primera versió enviada"},
                {"data": "2024-01-20", "descripcio": "Revisió amb correccions"}
            ]
        })
        fitxers.insert_one({
            "projecte_id": 1,
            "arxius": [
                {"nom": "balatro.pdf", "url": "/uploads/balatro.pdf"},
                {"nom": "referencies.docx", "url": "/uploads/referencies.docx"}
            ]
        })

        # Projecte "Adios" (projecte_id: 2)
        comentaris.insert_one({
            "projecte_id": 2,
            "comentaris": [
                {"professor_id": 2, "text": "Falta profunditat en l'anàlisi", "data": "2024-02-05"}
            ]
        })
        revisions.insert_one({
            "projecte_id": 2,
            "versions": [
                {"data": "2024-01-18", "descripcio": "Primera versió enviada"}
            ]
        })
        fitxers.insert_one({
            "projecte_id": 2,
            "arxius": [
                {"nom": "adios.pdf", "url": "/uploads/adios.pdf"}
            ]
        })

        # Projecte "Proje" (projecte_id: 3)
        comentaris.insert_one({
            "projecte_id": 3,
            "comentaris": [
                {"professor_id": 1, "text": "Bon contingut, però revisa l'ortografia", "data": "2024-02-07"}
            ]
        })
        revisions.insert_one({
            "projecte_id": 3,
            "versions": [
                {"data": "2024-01-20", "descripcio": "Primera versió enviada"}
            ]
        })
        fitxers.insert_one({
            "projecte_id": 3,
            "arxius": [
                {"nom": "proje.pdf", "url": "/uploads/proje.pdf"}
            ]
        })

        print("Col·leccions de MongoDB inicialitzades amb èxit!")
        client.close()

    except Exception as e:
        print(f"Error inicialitzant MongoDB: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_mongodb()