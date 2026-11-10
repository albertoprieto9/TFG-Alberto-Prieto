"""Resalta por separado las celdas de dominio y rango que cambian."""

from rdflib import URIRef

from modelos_drawio import corto, ejecutar, nombre, resumen_extremo


def dibujar(libro):
    p, clases, propiedades = libro.vista_general(
        "Matriz de cambios",
        "Verde = pareja CSV · Rosa = cambio de extremo · Ámbar = expresión por revisar.",
    )
    libro.inventario_visible(p, clases)
    p.caja("Propiedades", 430, 143, 235, 29, fuerte=True, tam=18)
    p.caja("Gold", 680, 143, 385, 29, tono="gold", fuerte=True)
    p.caja("Pred", 1090, 143, 385, 29, tono="pred", fuerte=True)
    for x, titulo in ((680, "Dominio"), (900, "Rango"), (1090, "Dominio"), (1310, "Rango")):
        p.caja(titulo, x, 176, 165, 26, fuerte=True)
    for j, fila in enumerate(propiedades):
        y = 214 + j * 55
        par = bool(fila.gold and fila.pred)
        entidades = (fila.gold, fila.pred)
        tono = "par" if par else "gold" if fila.gold else "pred"
        tipo = " · atributo" if any(e and e.tipo == "datos" for e in entidades) else ""
        etiqueta = " ↔ ".join(nombre(e.iri) for e in entidades if e) + tipo
        enlace = libro.detalle_propiedad(fila)
        ayuda = libro.ayuda_propiedad(fila)
        p.caja(corto(etiqueta, 30) + (" ↗" if enlace else ""), 430, y, 230, 29,
               tono=tono, tam=14, enlace=enlace, ayuda=ayuda)
        if par and fila.gold.tipo != fila.pred.tipo:
            p.caja("Cambia tipo", 430, y + 29, 108, 21, tono="cambio", tam=12, ayuda=ayuda)
        campos = libro.campos(fila)
        for lado, (x, entidad) in enumerate(zip((680, 1090), entidades)):
            if entidad is None:
                p.caja("—", x, y, 385, 30, tam=14)
                continue
            extremos = []
            for dx, campo in ((0, "dominio"), (220, "rango")):
                valores = getattr(entidad, campo)
                revisar = any(not isinstance(t, URIRef) for t in valores)
                color = "revisar" if revisar else "cambio" if campos.get(campo) == "distinto" else "neutro"
                texto = libro.aviso_expresion(fila, campo, lado) if revisar else resumen_extremo(valores, 19)
                extremos.append(p.caja(
                    texto, x + dx, y, 165, 30, tono=color, tam=14,
                    ayuda=None if revisar else "\n".join(map(str, valores)),
                    enlace=enlace if revisar else None,
                ))
            if entidad.tipo == "objeto" and all(
                len(terms) == 1 and isinstance(terms[0], URIRef)
                for terms in (entidad.dominio, entidad.rango)
            ):
                p.linea(*extremos, tono=tono)


if __name__ == "__main__":
    raise SystemExit(ejecutar("modelo_diferencias", dibujar))
