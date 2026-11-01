"""Práctica XML: propiedades resueltas y dominio/rango generados desde RDF.

Se cargan las ontologías, se recorren los pares del CSV y se localizan sus IRI.
Los nombres de los rombos se obtienen de esas IRI y los rectángulos del dominio
y rango se leen del grafo generado. Se espera un único dominio y rango con IRI.
El caso de práctica espera que la referencia no tenga dominio/rango explícitos
y comprueba esa condición; otros casos se rechazan antes de dibujar.
Se mantienen la selección del caso, las posiciones y las llamadas de conexión.
Se lee su fila del informe de dominio/rango y se muestran los estados publicados
en una nota del dibujo, separada de los axiomas representados.
Además se representan todos los pares del CSV de clases, reutilizando figuras
cuando una IRI ya está dibujada en su lado. No se representan aún las entidades
sin correspondencia que no sean extremos de las relaciones incluidas.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

from rdflib import URIRef
from rdflib.namespace import OWL, RDFS

from inspeccionar_entradas import (
    DATOS_AWO, crear_indice_nombres, leer_csv, leer_ontologia, resolver_nombre,
)


ESPACIO_GOLD = "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#"
ESPACIO_PRED = "http://www.semanticweb.org/myontology#"


def seleccionar_comparacion(filas, par):
    """Recupera la fila del informe para ambos nombres y el tipo esperado."""
    coincidencias = []

    for fila in filas:
        if (
            fila["PropertyType"] == "ObjectProperty"
            and fila["GoldPredicate"] == par["Gold_term"]
            and fila["PredPredicate"] == par["Pre_term"]
        ):
            coincidencias.append(fila)

    if len(coincidencias) != 1:
        raise ValueError("Debe existir una única comparación para este par.")

    return coincidencias[0]


def abreviar_iri(iri, espacio_nombres, prefijo):
    """Abrevia solo cuando la IRI pertenece al espacio de nombres indicado."""
    texto = str(iri)

    if texto.startswith(espacio_nombres):
        return prefijo + ":" + texto.removeprefix(espacio_nombres)

    return texto


def obtener_iri_unica(nombre, indice):
    """Usa el resolver existente y exige una sola entidad identificada."""
    estado, candidatas = resolver_nombre(nombre, indice)
    if estado != "única":
        raise ValueError(f"Revisar identificación de {nombre}: {estado}.")
    return list(candidatas)[0]


def obtener_o_crear_clase(
    raiz, clases, iri, espacio_nombres, prefijo, x, y
):
    """Registra una figura por IRI y por lado; conserva su posición al reutilizarla."""
    if iri not in clases:
        id_figura = f"{prefijo}-clase-{len(clases) + 1}"
        nombre = abreviar_iri(iri, espacio_nombres, prefijo)
        agregar_clase(raiz, id_figura, nombre, x, y)
        clases[iri] = {"id": id_figura, "y": y}

    return clases[iri]


def crear_documento():
    """Crea la estructura básica que espera draw.io, con una capa vacía."""
    documento = ET.Element("mxfile", {"host": "app.diagrams.net"})
    pagina = ET.SubElement(documento, "diagram", {"name": "Paso 10 - Dos pares de propiedades"})
    modelo = ET.SubElement(pagina, "mxGraphModel")
    raiz = ET.SubElement(modelo, "root")
    ET.SubElement(raiz, "mxCell", {"id": "0"})
    ET.SubElement(raiz, "mxCell", {"id": "1", "parent": "0"})
    return documento, raiz


def agregar_clase(raiz, id_figura, nombre, x, y):
    figura = ET.SubElement(raiz, "mxCell", {
        "id": id_figura,
        "value": nombre,
        "vertex": "1",
        "parent": "1",
        "style": "rounded=0;whiteSpace=wrap;html=0;",
    })

    ET.SubElement(figura, "mxGeometry", {
        "x": str(x),
        "y": str(y),
        "width": "160",
        "height": "40",
        "as": "geometry",
    })


def agregar_propiedad(raiz, id_figura, nombre, x, y):
    """Añade un rombo para una propiedad de objeto según la notación Chowlk."""
    figura = ET.SubElement(raiz, "mxCell", {
        "id": id_figura,
        "value": "<<owl:ObjectProperty>>\n" + nombre,
        "vertex": "1",
        "parent": "1",
        "style": "rhombus;whiteSpace=wrap;html=0;",
    })

    ET.SubElement(figura, "mxGeometry", {
        "x": str(x),
        "y": str(y),
        "width": "240",
        "height": "100",
        "as": "geometry",
    })


def agregar_nota(raiz, id_figura, texto, x, y):
    """Añade una nota de presentación; no representa una entidad de la ontología."""
    figura = ET.SubElement(raiz, "mxCell", {
        "id": id_figura,
        "value": texto,
        "vertex": "1",
        "parent": "1",
        "style": "shape=note;whiteSpace=wrap;html=0;",
    })

    ET.SubElement(figura, "mxGeometry", {
        "x": str(x),
        "y": str(y),
        "width": "340",
        "height": "130",
        "as": "geometry",
    })


def agregar_conexion(raiz, id_conexion, origen, destino, etiqueta):
    """Une figuras mediante una flecha de dominio/rango de la notación Chowlk."""
    estilo = "endArrow=open;endFill=0;dashed=1;html=0;"
    if etiqueta == "<<rdfs:domain>>":
        estilo += "exitX=1;exitY=0.25;entryX=0;entryY=0.25;"
    elif etiqueta == "<<rdfs:range>>":
        estilo += "exitX=1;exitY=0.75;entryX=0;entryY=0.75;"
    conexion = ET.SubElement(raiz, "mxCell", {
        "id": id_conexion,
        "value": etiqueta,
        "edge": "1",
        "parent": "1",
        "source": origen,
        "target": destino,
        "style": estilo,
    })

    ET.SubElement(conexion, "mxGeometry", {
        "relative": "1",
        "as": "geometry",
    })


def agregar_correspondencia(raiz, id_conexion, origen, destino):
    """Añade una relación visual del informe; no es un axioma de equivalencia."""
    conexion = ET.SubElement(raiz, "mxCell", {
        "id": id_conexion,
        "value": "correspondencia según CSV",
        "edge": "1",
        "parent": "1",
        "source": origen,
        "target": destino,
        "style": "dashed=1;startArrow=none;endArrow=none;html=0;",
    })

    ET.SubElement(conexion, "mxGeometry", {
        "relative": "1",
        "as": "geometry",
    })


def dibujar_par_propiedades(
    raiz, referencia, generada, clases_generada, par, comparacion, numero
):
    """Repite el fragmento conocido para una fila y comparte las clases dibujadas.

    Alcance de esta versión: referencia sin domain/range explícitos y generada
    con exactamente una IRI por predicado. Los demás casos se rechazan.
    """
    indice_referencia = crear_indice_nombres(
        referencia, (OWL.ObjectProperty,)
    )
    indice_generada = crear_indice_nombres(
        generada, (OWL.ObjectProperty,)
    )

    iri_referencia = obtener_iri_unica(par["Gold_term"], indice_referencia)
    iri_generada = obtener_iri_unica(par["Pre_term"], indice_generada)
    print("IRI de referencia:", iri_referencia)
    print("IRI de generada:", iri_generada)

    dominios_referencia = list(
        referencia.objects(iri_referencia, RDFS.domain)
    )
    rangos_referencia = list(
        referencia.objects(iri_referencia, RDFS.range)
    )
    print("Dominios explícitos de referencia:", len(dominios_referencia))
    print("Rangos explícitos de referencia:", len(rangos_referencia))

    if len(dominios_referencia) > 0 or len(rangos_referencia) > 0:
        raise ValueError("Este ejercicio aún no dibuja dominios/rangos en el lado de referencia.")

    dominios = list(generada.objects(iri_generada, RDFS.domain))
    rangos = list(generada.objects(iri_generada, RDFS.range))

    if len(dominios) != 1 or len(rangos) != 1:
        raise ValueError("Este fragmento requiere un dominio y un rango explícitos, uno de cada.")
    if not isinstance(dominios[0], URIRef) or not isinstance(rangos[0], URIRef):
        raise ValueError("Este fragmento requiere IRI de dominio/rango; no dibuja expresiones anónimas.")

    print("Dominio leído del grafo:", dominios[0])
    print("Rango leído del grafo:", rangos[0])

    nombre_referencia = abreviar_iri(iri_referencia, ESPACIO_GOLD, "gold")
    nombre_generada = abreviar_iri(iri_generada, ESPACIO_PRED, "pred")
    figura_dominio = obtener_o_crear_clase(
        raiz, clases_generada, dominios[0], ESPACIO_PRED, "pred",
        820, 100 + len(clases_generada) * 110
    )
    figura_rango = obtener_o_crear_clase(
        raiz, clases_generada, rangos[0], ESPACIO_PRED, "pred",
        820, 100 + len(clases_generada) * 110
    )
    id_gold = f"propiedad-gold-{numero + 1}"
    id_pred = f"propiedad-pred-{numero + 1}"
    y = 900 + numero * 220
    agregar_propiedad(raiz, id_pred, nombre_generada, 460, y)
    agregar_propiedad(raiz, id_gold, nombre_referencia, 60, y)
    agregar_conexion(
        raiz, f"dominio-{numero + 1}",
        id_pred, figura_dominio["id"],
        "<<rdfs:domain>>"
    )
    agregar_conexion(
        raiz, f"rango-{numero + 1}",
        id_pred, figura_rango["id"],
        "<<rdfs:range>>"
    )
    agregar_correspondencia(
        raiz, f"correspondencia-propiedad-{numero + 1}", id_gold, id_pred
    )

    texto_informe = (
        "Estados según triple_layer3_pairs.csv\n"
        f"{par['Gold_term']} ↔ {par['Pre_term']}\n"
        f"Dominio: {comparacion['DomainStatus']}\n"
        f"Rango: {comparacion['RangeStatus']}"
    )
    agregar_nota(raiz, f"informe-{numero + 1}", texto_informe, 60 + numero * 440, 1450)


if __name__ == "__main__":
    referencia = leer_ontologia(DATOS_AWO / "awo-referencia.owl", "xml")
    generada = leer_ontologia(DATOS_AWO / "awo-generada.owl", "xml")
    print("Triples de referencia:", len(referencia))
    print("Triples de generada:", len(generada))

    filas = leer_csv(DATOS_AWO / "property_best_matching.csv", ("Gold_term", "Pre_term"))
    filas_comparacion = leer_csv(
        DATOS_AWO / "triple_layer3_pairs.csv",
        ("PropertyType", "GoldPredicate", "PredPredicate", "DomainStatus", "RangeStatus")
    )
    filas_clases = leer_csv(
        DATOS_AWO / "class_best_matching.csv", ("Gold_term", "Pre_term")
    )
    indice_clases_referencia = crear_indice_nombres(referencia, (OWL.Class,))
    indice_clases_generada = crear_indice_nombres(generada, (OWL.Class,))

    documento, raiz = crear_documento()
    clases_referencia = {}
    clases_generada = {}
    for numero, fila in enumerate(filas_clases):
        iri_gold = obtener_iri_unica(fila["Gold_term"], indice_clases_referencia)
        iri_pred = obtener_iri_unica(fila["Pre_term"], indice_clases_generada)
        y = 100 + numero * 110
        if iri_pred in clases_generada:
            y = clases_generada[iri_pred]["y"]

        figura_gold = obtener_o_crear_clase(
            raiz, clases_referencia, iri_gold, ESPACIO_GOLD, "gold", 100, y
        )
        figura_pred = obtener_o_crear_clase(
            raiz, clases_generada, iri_pred, ESPACIO_PRED, "pred", 820, y
        )
        agregar_correspondencia(
            raiz, f"correspondencia-clase-{numero + 1}",
            figura_gold["id"], figura_pred["id"]
        )
    print("Correspondencias de clases dibujadas:", len(filas_clases))

    for numero, par in enumerate(filas):
        comparacion = seleccionar_comparacion(filas_comparacion, par)
        dibujar_par_propiedades(
            raiz, referencia, generada, clases_generada,
            par, comparacion, numero
        )
    print("Correspondencias de propiedades dibujadas:", len(filas))

    agregar_nota(
        raiz, "fuentes-1",
        "Fuentes de correspondencias\n"
        "Clases: class_best_matching.csv\n"
        "Propiedades: property_best_matching.csv",
        60, 1620
    )

    destino = Path(__file__).resolve().parent / "salidas" / "paso-10-dos-propiedades.drawio"
    destino.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(documento)
    ET.ElementTree(documento).write(destino, encoding="utf-8", xml_declaration=True)
    print(f"Dibujo guardado en: {destino}")
