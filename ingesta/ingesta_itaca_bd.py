import os
import sys
import json
import hashlib
import logging
from datetime import date

import psycopg2
import psycopg2.extras
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ingesta_itaca_bd")

# Las cuatro tablas que pide la práctica
TABLAS = ["alumnos", "cursos", "contenidos", "calificaciones"]

# En qué columna está el NIA dentro de cada tabla
COLUMNAS_NIA = {"alumnos": "nia", "calificaciones": "alumno"}

# Memoria de hashes: el mismo NIA da siempre el mismo identificador
_cache_nia = {}


def anonimizar_nia(nia):
    if nia is None:
        return None
    clave = str(nia)
    if clave not in _cache_nia:
        _cache_nia[clave] = hashlib.sha256(clave.encode()).hexdigest()[:10]
    return _cache_nia[clave]


def conectar():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"), port=os.getenv("DB_PORT"),
        dbname=os.getenv("DB_NAME"), user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def extraer_tabla(conexion, tabla):
    consulta = sql.SQL("SELECT * FROM {}").format(sql.Identifier(tabla))
    with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(consulta)
        return [dict(fila) for fila in cur.fetchall()]


def anonimizar_tabla(datos, tabla):
    columna = COLUMNAS_NIA.get(tabla)
    if columna:
        for fila in datos:
            fila[columna] = anonimizar_nia(fila[columna])
        logger.info("Tabla %s: columna '%s' anonimizada", tabla, columna)
    return datos


def guardar(datos, tabla):
    fecha = date.today().isoformat()
    os.makedirs("data/raw", exist_ok=True)
    ruta = f"data/raw/{tabla}_{fecha}.json"
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)
    logger.info("Guardados %d registros en %s", len(datos), ruta)


if __name__ == "__main__":
    conexion = None
    try:
        conexion = conectar()
        logger.info("Conectado a %s", os.getenv("DB_NAME"))
        for tabla in TABLAS:
            datos = extraer_tabla(conexion, tabla)
            datos = anonimizar_tabla(datos, tabla)
            guardar(datos, tabla)
        logger.info("Ingesta completada: %d NIA distintos anonimizados", len(_cache_nia))
    except psycopg2.Error as e:
        logger.error("Error de base de datos: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.error("Error inesperado: %s", e)
        sys.exit(1)
    finally:
        if conexion:
            conexion.close()
            logger.info("Conexión cerrada")