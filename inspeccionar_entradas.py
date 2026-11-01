"""Primer paso del prototipo: leer dos ontologías y tres informes originales.

Esta versión muestra lo que contienen los archivos. No calcula correspondencias,
no ejecuta razonamiento OWL y todavía no genera un diagrama.
"""

import argparse
import csv
from pathlib import Path
import sys

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS


DATOS_AWO = Path(__file__).resolve().parent / "datos" / "awo"


def leer_ontologia(ruta: Path, formato: str) -> Graph:
    """Lee un archivo RDF local con el formato indicado, sin cargar imports."""
    if not ruta.is_file():
        raise ValueError(f"No se encuentra la ontología: {ruta}")
    try:
        return Graph().parse(source=ruta, format=formato)
    except Exception as error:
        raise ValueError(
            f"No se puede leer {ruta.name} como {formato}: {error}"
        ) from error


def leer_csv(ruta: Path, columnas_necesarias: tuple[str, ...]) -> list[dict[str, str]]:
    """Conserva las columnas y valores del informe, incluidos los campos vacíos."""
    with ruta.open(encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        cabecera = lector.fieldnames or []
        if len(cabecera) != len(set(cabecera)):
            raise ValueError(f"{ruta.name}: hay columnas duplicadas.")
        faltan = set(columnas_necesarias) - set(cabecera)
        if faltan:
            raise ValueError(f"{ruta.name}: faltan columnas: {', '.join(sorted(faltan))}.")
        filas = []
        for fila in lector:
            if None in fila or any(valor is None for valor in fila.values()):
                raise ValueError(
                    f"{ruta.name}, línea {lector.line_num}: número de campos incorrecto."
                )
            filas.append(fila)
        return filas


def describir_termino(termino) -> str:
    """Muestra las IRI completas y hace visibles las expresiones anónimas."""
    if isinstance(termino, BNode):
        return "[expresión anónima: presente en el RDF]"
    return str(termino)


def mostrar_ontologia(grafo: Graph, titulo: str) -> None:
    clases = {s for s in grafo.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)}
    propiedades_objeto = {
        s for s in grafo.subjects(RDF.type, OWL.ObjectProperty) if isinstance(s, URIRef)
    }
    propiedades_datos = {
        s for s in grafo.subjects(RDF.type, OWL.DatatypeProperty) if isinstance(s, URIRef)
    }
    print(f"\n{titulo}")
    print(f"  Triples leídos: {len(grafo)}")
    print(f"  Clases con declaración explícita owl:Class e IRI: {len(clases)}")
    print(f"  Propiedades de objeto declaradas: {len(propiedades_objeto)}")
    print(f"  Propiedades de datos declaradas: {len(propiedades_datos)}")
    print("  Dominios y rangos explícitos de propiedades declaradas:")
    for propiedad in sorted(propiedades_objeto | propiedades_datos, key=str):
        print(f"    {propiedad}")
        for predicado, nombre in ((RDFS.domain, "dominio"), (RDFS.range, "rango")):
            valores = sorted(grafo.objects(propiedad, predicado), key=str)
            texto = "; ".join(describir_termino(v) for v in valores)
            print(f"      {nombre}: {texto or 'sin declaración explícita'}")


def crear_indice_nombres(grafo: Graph, tipos: tuple[URIRef, ...]) -> dict:
    """Indexa nombres exactos de entidades con IRI y declaración de tipo.

    Conserva todas las candidatas y el motivo de cada coincidencia. No normaliza
    mayúsculas, espacios o signos; las etiquetas se comparan por su texto en
    cualquier idioma, ya que estos CSV no especifican un idioma.
    """
    entidades = {
        entidad for tipo in tipos for entidad in grafo.subjects(RDF.type, tipo)
        if isinstance(entidad, URIRef)
    }
    indice = {}
    for entidad in sorted(entidades, key=str):
        iri = str(entidad)
        local = iri.rsplit("#", 1)[-1] if "#" in iri else iri.rstrip("/").rsplit("/", 1)[-1]
        nombres = [(local, "nombre local")]
        nombres.extend(
            (str(etiqueta), "rdfs:label")
            for etiqueta in grafo.objects(entidad, RDFS.label)
            if isinstance(etiqueta, Literal)
        )
        for nombre, motivo in nombres:
            if nombre:
                indice.setdefault(nombre, {}).setdefault(entidad, set()).add(motivo)
    return indice


def resolver_nombre(nombre: str, indice: dict) -> tuple[str, dict]:
    """Devuelve el estado y todas las candidatas, sin elegir entre ambigüedades."""
    candidatas = indice.get(nombre, {})
    if not candidatas:
        return "sin resolver", candidatas
    if len(candidatas) > 1:
        return "ambiguo", candidatas
    return "única", candidatas


def mostrar_resolucion(nombre: str, indice: dict, lado: str) -> None:
    estado, candidatas = resolver_nombre(nombre, indice)
    print(f"    {lado}: {estado}")
    for iri, motivos in sorted(candidatas.items(), key=lambda par: str(par[0])):
        print(f"      {iri} | coincidencia exacta: {', '.join(sorted(motivos))}")


def mostrar_correspondencias(
    filas: list[dict[str, str]], titulo: str, indice_gold: dict, indice_pred: dict
) -> None:
    print(f"\n{titulo}: {len(filas)} pares publicados")
    for fila in filas:
        print(
            f"  {fila['Gold_term']} <-> {fila['Pre_term']}"
            f" | método: {fila['Method']} | puntuación: {fila['Score']}"
        )
        mostrar_resolucion(fila["Gold_term"], indice_gold, "referencia")
        mostrar_resolucion(fila["Pre_term"], indice_pred, "generada")


def consultar_propiedad(grafo: Graph, nombre: str, indice: dict) -> dict:
    """Consulta todos los dominios/rangos explícitos solo con resolución única.

    None significa consulta no realizada; una lista vacía significa que se
    consultó una propiedad identificada y no se encontraron esos triples.
    Conserva los términos RDF, incluidos los nodos en blanco.
    """
    estado, candidatas = resolver_nombre(nombre, indice)
    resultado = {
        "estado": estado, "candidatas": candidatas, "iri": None,
        "dominios": None, "rangos": None,
    }
    if estado == "única":
        iri = next(iter(candidatas))
        resultado.update(
            iri=iri,
            dominios=sorted(grafo.objects(iri, RDFS.domain), key=str),
            rangos=sorted(grafo.objects(iri, RDFS.range), key=str),
        )
    return resultado


def mostrar_propiedad_del_informe(
    grafo: Graph, nombre: str, indice: dict, lado: str
) -> None:
    resultado = consultar_propiedad(grafo, nombre, indice)
    mostrar_resolucion(nombre, indice, f"Grafo {lado}")
    if resultado["estado"] != "única":
        print("      dominio/rango: consulta no realizada; revisar identificación")
        return
    for campo, titulo in (("dominios", "dominio"), ("rangos", "rango")):
        texto = "; ".join(describir_termino(v) for v in resultado[campo])
        print(f"      {titulo}: {texto or 'sin declaración explícita'}")


def crear_argumentos() -> argparse.ArgumentParser:
    argumentos = argparse.ArgumentParser(
        description="Lee dos ontologías y tres CSV; por defecto utiliza el ejemplo AWO."
    )
    argumentos.add_argument("--referencia", type=Path, default=DATOS_AWO / "awo-referencia.owl")
    argumentos.add_argument("--generada", type=Path, default=DATOS_AWO / "awo-generada.owl")
    argumentos.add_argument("--clases", type=Path, default=DATOS_AWO / "class_best_matching.csv")
    argumentos.add_argument(
        "--propiedades", type=Path, default=DATOS_AWO / "property_best_matching.csv"
    )
    argumentos.add_argument(
        "--dominios-rangos", type=Path, default=DATOS_AWO / "triple_layer3_pairs.csv"
    )
    argumentos.add_argument("--formato-referencia", choices=("xml", "turtle"), default="xml")
    argumentos.add_argument("--formato-generada", choices=("xml", "turtle"), default="xml")
    return argumentos


def main() -> int:
    argumentos = crear_argumentos().parse_args()
    columnas_pares = ("Gold_term", "Pre_term", "Method", "Score")
    columnas_dominios_rangos = (
        "GoldPredicate", "PredPredicate", "GoldDomain", "PredDomain", "DomainStatus",
        "GoldRange", "PredRange", "RangeStatus",
    )
    try:
        referencia = leer_ontologia(argumentos.referencia, argumentos.formato_referencia)
        generada = leer_ontologia(argumentos.generada, argumentos.formato_generada)
        clases = leer_csv(argumentos.clases, columnas_pares)
        propiedades = leer_csv(argumentos.propiedades, columnas_pares)
        dominios_rangos = leer_csv(argumentos.dominios_rangos, columnas_dominios_rangos)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("Primer lector del TFG: dos ontologías y tres CSV originales")
    mostrar_ontologia(referencia, "Ontología de referencia")
    mostrar_ontologia(generada, "Ontología generada")
    mostrar_correspondencias(
        clases, "Correspondencias de clases",
        crear_indice_nombres(referencia, (OWL.Class,)),
        crear_indice_nombres(generada, (OWL.Class,)),
    )
    tipos_propiedad = (OWL.ObjectProperty, OWL.DatatypeProperty)
    indice_prop_gold = crear_indice_nombres(referencia, tipos_propiedad)
    indice_prop_pred = crear_indice_nombres(generada, tipos_propiedad)
    mostrar_correspondencias(
        propiedades, "Correspondencias de propiedades",
        indice_prop_gold, indice_prop_pred,
    )
    print(f"\nComparaciones de dominio/rango: {len(dominios_rangos)} filas publicadas")
    for fila in dominios_rangos:
        print(f"  {fila['GoldPredicate']} <-> {fila['PredPredicate']}")
        for campo, estado in (("Domain", "DomainStatus"), ("Range", "RangeStatus")):
            gold = fila[f"Gold{campo}"] or "[vacío en el CSV]"
            pred = fila[f"Pred{campo}"] or "[vacío en el CSV]"
            print(f"    CSV {campo}: gold={gold}; pred={pred}; estado publicado={fila[estado]}")
        mostrar_propiedad_del_informe(
            referencia, fila["GoldPredicate"], indice_prop_gold, "referencia"
        )
        mostrar_propiedad_del_informe(
            generada, fila["PredPredicate"], indice_prop_pred, "generada"
        )

    print("\nLectura terminada. Las puntuaciones y estados proceden de los CSV.")
    print("Los recuentos de clases incluyen declaraciones explícitas, no toda la firma OWL.")
    print("Un campo vacío del CSV no demuestra ausencia de un axioma en la ontología.")
    print("La resolución de los pares usa nombres locales y etiquetas exactos de entidades declaradas.")
    print("Una candidata única identifica la entidad por ese criterio; no demuestra equivalencia OWL.")
    print("Los nombres de dominio/rango del tercer CSV todavía no se han resuelto a IRI.")
    print("Los dominios/rangos de cada propiedad identificada se consultan directamente en su grafo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
