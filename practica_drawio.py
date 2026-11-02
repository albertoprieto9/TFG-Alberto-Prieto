"""Práctica XML: propiedades resueltas y dominio/rango generados desde RDF.

Se cargan las ontologías, se recorren los pares del CSV y se localizan sus IRI.
Los nombres de los rombos se obtienen de esas IRI. Los dominios y rangos explícitos
de cada propiedad dibujada se leen de su propio grafo y se conectan con clases
identificadas por IRI. Las expresiones anónimas se indican en avisos, sin desarrollar
su estructura interna ni inferir axiomas.
Se lee su fila del informe de dominio/rango y se muestran los estados publicados
en una nota del dibujo, separada de los axiomas representados.
Además se representan todos los pares del CSV de clases, reutilizando figuras
cuando una IRI ya está dibujada en su lado. Se añaden las demás clases con IRI
y declaración explícita owl:Class, salvo owl:Thing, y las demás propiedades de
objeto con IRI y declaración explícita. Los demás axiomas quedan fuera del dibujo.
"""

from pathlib import Path
import xml.etree.ElementTree as ET

from rdflib import BNode, URIRef
from rdflib.namespace import OWL, RDF, RDFS

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


def agregar_clases_pendientes(raiz, grafo, clases, espacio_nombres, prefijo, x):
    """Añade clases nombradas explícitas sin figura; omite la clase universal."""
    agregadas = 0
    for iri in sorted(set(grafo.subjects(RDF.type, OWL.Class)), key=str):
        if not isinstance(iri, URIRef):
            continue
        if iri == OWL.Thing or iri in clases:
            continue

        # Hueco entre clases emparejadas y propiedades, para esta práctica AWO.
        y = 650 + agregadas * 80
        obtener_o_crear_clase(
            raiz, clases, iri, espacio_nombres, prefijo, x, y
        )
        agregadas += 1

    return agregadas


def obtener_o_crear_propiedad(
    raiz, propiedades, iri, espacio_nombres, prefijo, x, y
):
    """Registra un rombo por IRI y por lado, igual que el registro de clases."""
    if iri not in propiedades:
        id_figura = f"propiedad-{prefijo}-{len(propiedades) + 1}"
        nombre = abreviar_iri(iri, espacio_nombres, prefijo)
        agregar_propiedad(raiz, id_figura, nombre, x, y)
        propiedades[iri] = {"id": id_figura, "y": y}

    return propiedades[iri]


def agregar_propiedades_pendientes(
    raiz, grafo, propiedades, espacio_nombres, prefijo, x
):
    """Añade rombos de propiedades declaradas sin figura, sin añadir conexiones."""
    agregadas = 0
    for iri in sorted(set(grafo.subjects(RDF.type, OWL.ObjectProperty)), key=str):
        if not isinstance(iri, URIRef) or iri in propiedades:
            continue

        y = 1340 + agregadas * 220
        obtener_o_crear_propiedad(
            raiz, propiedades, iri, espacio_nombres, prefijo, x, y
        )
        agregadas += 1

    return agregadas


def agregar_dominios_y_rangos(
    raiz, grafo, propiedades, clases, espacio_nombres, prefijo, x
):
    """Dibuja extremos con IRI; devuelve avisos para los valores no representados."""
    avisos = []
    for iri_propiedad, figura_propiedad in propiedades.items():
        nombre = abreviar_iri(iri_propiedad, espacio_nombres, prefijo)
        for predicado, tipo in ((RDFS.domain, "dominio"), (RDFS.range, "rango")):
            valores = sorted(grafo.objects(iri_propiedad, predicado), key=str)
            if not valores:
                print(f"{nombre} — {tipo}: sin declaración explícita")

            for numero, valor in enumerate(valores):
                if isinstance(valor, URIRef):
                    figura_clase = obtener_o_crear_clase(
                        raiz, clases, valor, espacio_nombres, prefijo,
                        x, 100 + len(clases) * 110
                    )
                    etiqueta = "<<rdfs:domain>>" if tipo == "dominio" else "<<rdfs:range>>"
                    agregar_conexion(
                        raiz, f"{figura_propiedad['id']}-{tipo}-{numero + 1}",
                        figura_propiedad["id"], figura_clase["id"], etiqueta
                    )
                    print(f"{nombre} — {tipo}: {valor}")
                elif isinstance(valor, BNode):
                    avisos.append(
                        f"{nombre} — {tipo}: expresión anónima presente; sin desarrollar."
                    )
                else:
                    avisos.append(
                        f"{nombre} — {tipo}: valor literal no representado; revisar RDF."
                    )

    return avisos


def crear_documento():
    """Crea la estructura básica que espera draw.io, con una capa vacía."""
    documento = ET.Element("mxfile", {"host": "app.diagrams.net"})
    pagina = ET.SubElement(documento, "diagram", {"name": "Paso 14 - Comparación ordenada"})
    modelo = ET.SubElement(pagina, "mxGraphModel", {"page": "0"})
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
        "style": "dashed=1;startArrow=none;endArrow=none;html=0;strokeColor=#777777;",
    })

    ET.SubElement(conexion, "mxGeometry", {
        "relative": "1",
        "as": "geometry",
    })


def agregar_titulo(raiz, id_figura, texto, x, y, ancho):
    """Añade texto de presentación, sin representar una entidad OWL."""
    figura = ET.SubElement(raiz, "mxCell", {
        "id": id_figura, "value": texto, "vertex": "1", "parent": "1",
        "style": "text;html=0;align=center;verticalAlign=middle;fontSize=20;fontStyle=1;",
    })
    ET.SubElement(figura, "mxGeometry", {
        "x": str(x), "y": str(y), "width": str(ancho), "height": "40", "as": "geometry",
    })


def ordenar_diagrama(
    raiz, clases_referencia, clases_generada,
    propiedades_referencia, propiedades_generada
):
    """Distribución para AWO; cambia posiciones y trazados, conserva los enlaces."""
    celdas = {celda.get("id"): celda for celda in raiz.findall("mxCell")}
    for registro, x in (
        (propiedades_referencia, 60), (clases_referencia, 600),
        (clases_generada, 1180), (propiedades_generada, 1600),
    ):
        for figura in registro.values():
            celdas[figura["id"]].find("mxGeometry").set("x", str(x))

    ids_gold = {figura["id"] for figura in propiedades_referencia.values()}
    carriles = {"gold": 0, "pred": 0}
    for conexion in celdas.values():
        etiqueta = conexion.get("value")
        if conexion.get("edge") != "1" or etiqueta not in ("<<rdfs:domain>>", "<<rdfs:range>>"):
            continue
        lado = "gold" if conexion.get("source") in ids_gold else "pred"
        es_dominio = etiqueta == "<<rdfs:domain>>"
        altura = 0.25 if es_dominio else 0.75
        salida, entrada = (1, 0) if lado == "gold" else (0, 1)
        color = "#3274B5" if es_dominio else "#B86610"
        conexion.set("style", (
            "endArrow=open;endFill=0;dashed=1;html=0;noEdgeStyle=1;"
            f"strokeColor={color};strokeWidth=1.5;"
            f"exitX={salida};exitY={altura};entryX={entrada};entryY={altura};"
        ))
        origen = celdas[conexion.get("source")].find("mxGeometry")
        destino = celdas[conexion.get("target")].find("mxGeometry")
        y_origen = float(origen.get("y")) + altura * float(origen.get("height"))
        y_destino = float(destino.get("y")) + altura * float(destino.get("height"))
        carril = 350 + carriles[lado] * 20 if lado == "gold" else 1540 - carriles[lado] * 18
        geometria = conexion.find("mxGeometry")
        geometria.set("x", "-1")
        ET.SubElement(geometria, "mxPoint", {
            "x": "90" if lado == "gold" else "-90", "y": "-12", "as": "offset",
        })
        puntos = ET.SubElement(geometria, "Array", {"as": "points"})
        ET.SubElement(puntos, "mxPoint", {"x": str(carril), "y": str(y_origen)})
        ET.SubElement(puntos, "mxPoint", {"x": str(carril), "y": str(y_destino)})
        carriles[lado] += 1

    figuras_entidad = [
        celdas[figura["id"]].find("mxGeometry")
        for registro in (clases_referencia, clases_generada, propiedades_referencia, propiedades_generada)
        for figura in registro.values()
    ]
    inicio_notas = max(float(g.get("y")) + float(g.get("height")) for g in figuras_entidad) + 140
    notas = [c for c in celdas.values() if c.get("style", "").startswith("shape=note;")]
    for numero, nota in enumerate(notas):
        geometria = nota.find("mxGeometry")
        geometria.set("x", str(60 + (numero % 2) * 960))
        geometria.set("y", str(inicio_notas + (numero // 2) * 210))
        geometria.set("width", "800")
        geometria.set("height", "160")

    agregar_titulo(raiz, "titulo-gold", "Referencia — gold", 60, 20, 700)
    agregar_titulo(raiz, "titulo-pred", "Generada — pred", 1180, 20, 660)
    agregar_titulo(raiz, "titulo-clases-gold", "Clases", 600, 55, 160)
    agregar_titulo(raiz, "titulo-clases-pred", "Clases", 1180, 55, 160)
    agregar_titulo(raiz, "titulo-propiedades-gold", "Propiedades", 60, 830, 240)
    agregar_titulo(raiz, "titulo-propiedades-pred", "Propiedades", 1600, 830, 240)


def dibujar_par_propiedades(
    raiz, referencia, generada,
    propiedades_referencia, propiedades_generada, par, comparacion, numero
):
    """Dibuja los rombos del par, su correspondencia y los estados del informe."""
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

    y = 900 + numero * 220
    figura_gold = obtener_o_crear_propiedad(
        raiz, propiedades_referencia, iri_referencia, ESPACIO_GOLD, "gold", 60, y
    )
    figura_pred = obtener_o_crear_propiedad(
        raiz, propiedades_generada, iri_generada, ESPACIO_PRED, "pred", 460, y
    )
    id_gold = figura_gold["id"]
    id_pred = figura_pred["id"]
    agregar_correspondencia(
        raiz, f"correspondencia-propiedad-{numero + 1}", id_gold, id_pred
    )

    texto_informe = (
        "Estados según triple_layer3_pairs.csv\n"
        f"{par['Gold_term']} ↔ {par['Pre_term']}\n"
        f"Dominio: {comparacion['DomainStatus']}\n"
        f"Rango: {comparacion['RangeStatus']}"
    )
    agregar_nota(raiz, f"informe-{numero + 1}", texto_informe, 60 + numero * 440, 2110)


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
    propiedades_referencia = {}
    propiedades_generada = {}
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
            raiz, referencia, generada,
            propiedades_referencia, propiedades_generada, par, comparacion, numero
        )
    print("Correspondencias de propiedades dibujadas:", len(filas))

    adicionales_gold = agregar_clases_pendientes(
        raiz, referencia, clases_referencia, ESPACIO_GOLD, "gold", 100
    )
    adicionales_pred = agregar_clases_pendientes(
        raiz, generada, clases_generada, ESPACIO_PRED, "pred", 820
    )
    print("Clases adicionales de referencia:", adicionales_gold)
    print("Clases adicionales de generada:", adicionales_pred)

    propiedades_adicionales_gold = agregar_propiedades_pendientes(
        raiz, referencia, propiedades_referencia, ESPACIO_GOLD, "gold", 60
    )
    propiedades_adicionales_pred = agregar_propiedades_pendientes(
        raiz, generada, propiedades_generada, ESPACIO_PRED, "pred", 460
    )
    print("Propiedades adicionales de referencia:", propiedades_adicionales_gold)
    print("Propiedades adicionales de generada:", propiedades_adicionales_pred)

    avisos_gold = agregar_dominios_y_rangos(
        raiz, referencia, propiedades_referencia, clases_referencia,
        ESPACIO_GOLD, "gold", 100
    )
    avisos_pred = agregar_dominios_y_rangos(
        raiz, generada, propiedades_generada, clases_generada,
        ESPACIO_PRED, "pred", 820
    )
    avisos = avisos_gold + avisos_pred
    for aviso in avisos:
        print("AVISO:", aviso)
    if avisos:
        agregar_nota(
            raiz, "avisos-dominio-rango", "Valores no representados\n" + "\n".join(avisos),
            60, 2450
        )

    agregar_nota(
        raiz, "fuentes-1",
        "Fuentes de correspondencias\n"
        "Clases: class_best_matching.csv\n"
        "Propiedades: property_best_matching.csv\n"
        "Clases adicionales: declaración explícita owl:Class\n"
        "Se omite owl:Thing. Sin enlace no implica falta de equivalente.",
        60, 2280
    )
    agregar_nota(
        raiz, "alcance-propiedades",
        "Propiedades adicionales: declaración explícita owl:ObjectProperty\n"
        "Se dibujan los dominios/rangos explícitos con IRI en ambos lados.\n"
        "Las expresiones anónimas se indican en avisos. Sin razonamiento.\n"
        "Otros axiomas OWL también quedan fuera del dibujo.",
        500, 2280
    )

    agregar_nota(
        raiz, "leyenda-presentacion",
        "Correspondencias CSV: línea gris sin flechas; no afirman equivalencia OWL.\n"
        "Azul: rdfs:domain. Naranja: rdfs:range.\n"
        "Los colores son una ayuda visual propia del prototipo.\n"
        "La posición de las clases no representa una jerarquía.",
        0, 0
    )
    ordenar_diagrama(
        raiz, clases_referencia, clases_generada,
        propiedades_referencia, propiedades_generada
    )

    destino = Path(__file__).resolve().parent / "salidas" / "paso-14-comparacion-ordenada.drawio"
    destino.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(documento)
    ET.ElementTree(documento).write(destino, encoding="utf-8", xml_declaration=True)
    print(f"Dibujo guardado en: {destino}")
