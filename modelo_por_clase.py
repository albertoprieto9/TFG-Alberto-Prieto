"""Agrupa las flechas por la clase nombrada a la que llegan."""

from collections import defaultdict

from rdflib import URIRef

from modelos_drawio import corto, ejecutar, nombre


def grupo_rango(fila):
    for lado, entidad in (("Pred", fila.pred), ("Gold", fila.gold)):
        if entidad and entidad.tipo == "objeto" and len(entidad.rango) == 1:
            rango = entidad.rango[0]
            if isinstance(rango, URIRef):
                return (lado, rango)
    if any(e and e.tipo == "datos" for e in (fila.gold, fila.pred)):
        return ("Atributos", None)
    return ("Sin una sola clase de rango nombrada", None)


def dibujar(libro):
    p, clases, propiedades = libro.vista_general(
        "Propiedades por clase de rango",
        "Agrupa por rango nombrado de Pred o Gold · Rosa = cambio · Ámbar = revisar expresión.",
    )
    libro.inventario_visible(p, clases)
    p.caja("Propiedades · dominio → rango", 430, 143, 1060, 29, fuerte=True, tam=18)
    libro.cabeceras(p, 430, 177, 1060)
    grupos = defaultdict(list)
    for fila in propiedades:
        grupos[grupo_rango(fila)].append(fila)
    y = 215
    for (lado, rango), filas in grupos.items():
        rotulo = f"Rango {lado} · {corto(nombre(rango), 70)}" if rango else lado
        p.caja(rotulo, 430, y, 1060, 27, tono="neutro", fuerte=True, tam=15,
               ayuda=str(rango) if rango else None)
        y += 35
        for fila in filas:
            libro.fila_propiedad(p, fila, y, x=430, ancho=1060)
            y += 81
        y += 7


if __name__ == "__main__":
    raise SystemExit(ejecutar("modelo_por_clase", dibujar))
