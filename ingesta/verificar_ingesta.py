import json
import glob

def cargar(tabla):
    ruta = sorted(glob.glob(f"data/raw/{tabla}_*.json"))[-1]
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)

alumnos = cargar("alumnos")
calificaciones = cargar("calificaciones")

nias_alumnos = {a["nia"] for a in alumnos}
nias_calif = {c["alumno"] for c in calificaciones}

print("Ejemplo de NIA anonimizado:", alumnos[0]["nia"])
print("Longitud del hash:", len(alumnos[0]["nia"]))
print("NIA distintos en alumnos:", len(nias_alumnos))
print("NIA distintos en calificaciones:", len(nias_calif))

huerfanos = nias_calif - nias_alumnos
print("Calificaciones de alumnos que no existen en alumnos:", len(huerfanos))

# Comparamos con los huérfanos que ya existían en la base de datos original
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
con = psycopg2.connect(
    host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
    dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
)
with con.cursor() as cur:
    cur.execute("""
        SELECT COUNT(DISTINCT c.alumno) FROM calificaciones c
        WHERE NOT EXISTS (SELECT 1 FROM alumnos a WHERE a.nia = c.alumno)
    """)
    huerfanos_origen = cur.fetchone()[0]
con.close()

print("Huérfanos en la base de datos original:", huerfanos_origen)
print("Anonimizado consistente:", "SÍ" if len(huerfanos) == huerfanos_origen else "NO")