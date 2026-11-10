"""Compara Gold y Pred con flechas paralelas y una nota corta por fila."""

from itertools import zip_longest

from modelos_drawio import ejecutar


def dibujar(libro):
    p, clases, propiedades = libro.vista_general(
        "Clases y propiedades en paralelo",
        "Verde = pareja CSV · Rosa = cambio · Ámbar = revisar expresión · D: dominio · R: rango.",
    )
    libro.inventario_visible(p, clases)
    p.caja("Propiedades · dominio → rango", 430, 143, 1060, 29, fuerte=True, tam=18)
    libro.cabeceras(p, 430, 177, 1060)
    parejas = [f for f in propiedades if f.gold and f.pred]
    solo_gold = (f for f in propiedades if f.pred is None)
    solo_pred = (f for f in propiedades if f.gold is None)
    adicionales = [f for par in zip_longest(solo_gold, solo_pred) for f in par if f]
    for j, fila in enumerate(parejas + adicionales):
        libro.fila_propiedad(p, fila, 218 + j * 84, x=430, ancho=1060)


if __name__ == "__main__":
    raise SystemExit(ejecutar("modelo_filas", dibujar))
