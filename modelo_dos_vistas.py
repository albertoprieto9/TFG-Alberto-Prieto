"""Genera una vista de pájaro y otra por dominios a partir de OWL y CSV.

La posición se calcula con filas de correspondencias y carriles exteriores.
Se muestran axiomas explícitos. Los demás axiomas se resumen como texto.
"""

from collections import defaultdict
from pathlib import Path
import csv
import os
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET

from rdflib import URIRef
from rdflib.namespace import OWL, RDFS

from inspeccionar_entradas import crear_argumentos
from modelos_drawio import PALETA, Pagina, cargar, expresion, nombre


ANCHO_CLASE = 170
ALTO_CLASE = 42
PASO_FILA = 90


class Vista(Pagina):
    """Añade conectores con puntos de paso a las figuras existentes."""

    def __init__(self, documento, identificador, titulo):
        super().__init__(documento, identificador, titulo)
        modelo = documento[-1].find("mxGraphModel")
        modelo.set("background", "#FFFFFF")

    def texto(self, texto, x, y, ancho, alto=28, tam=14, fuerte=False):
        return self.caja(texto, x, y, ancho, alto, tam=tam, fuerte=fuerte)

    def flecha(self, origen, destino, lado, *, etiqueta="", subclase=False,
               puertos=(1, .5, 0, .5), puntos=()):
        salida_x, salida_y, entrada_x, entrada_y = puertos
        punta = "none" if lado is None else "block" if subclase else "classic"
        color = "#64748B" if lado is None else PALETA[lado][1]
        estilo = (
            "edgeStyle=segmentEdgeStyle;rounded=1;html=0;"
            f"strokeColor={color};strokeWidth=1.6;endArrow={punta};"
            f"endFill={int(punta == 'classic')};exitX={salida_x};exitY={salida_y};"
            f"entryX={entrada_x};entryY={entrada_y};fontSize=13;"
            "fontColor=#173F68;labelBackgroundColor=#FFFFFF;"
        )
        if lado is None:
            estilo += "dashed=1;dashPattern=5 4;"
        celda = ET.SubElement(
            self.raiz, "mxCell", id=self.siguiente(), parent="1", edge="1",
            source=origen, target=destino, value=etiqueta, style=estilo,
        )
        geometria = ET.SubElement(celda, "mxGeometry", relative="1", **{"as": "geometry"})
        if puntos:
            recorrido = ET.SubElement(geometria, "Array", **{"as": "points"})
            for x, y in puntos:
                ET.SubElement(recorrido, "mxPoint", x=str(x), y=str(y))
        if etiqueta:
            ET.SubElement(geometria, "mxPoint", x="0", y="-12", **{"as": "offset"})
        return celda


def extremos_nombrados(entidad):
    return (
        entidad.tipo == "objeto"
        and len(entidad.dominio) == len(entidad.rango) == 1
        and isinstance(entidad.dominio[0], URIRef)
        and isinstance(entidad.rango[0], URIRef)
    )


def describir_extremo(grafo, valores):
    if not valores:
        return "sin declaración explícita"
    # Varios axiomas de dominio o rango se aplican conjuntamente.
    return " y ".join(expresion(grafo, valor) for valor in valores)


def resumen_propiedad(grafo, entidad):
    etiqueta = nombre(entidad.iri)
    if entidad.tipo == "datos":
        etiqueta += " · atributo"
    return (
        f"{etiqueta}\n"
        f"Dominio: {describir_extremo(grafo, entidad.dominio)}\n"
        f"Rango: {describir_extremo(grafo, entidad.rango)}"
    )


def bloque_texto(vista, texto, x, y, ancho, tono=None):
    lineas = []
    for parrafo in texto.splitlines():
        lineas.extend(textwrap.wrap(parrafo, width=max(20, int(ancho / 7.3))) or [""])
    alto = max(44, len(lineas) * 19 + 18)
    vista.caja("\n".join(lineas), x, y, ancho, alto, tono=tono, tam=13)
    return alto


def posiciones_clases(grafos, clases):
    """Alinea parejas y asigna una figura a cada IRI dentro de su ontología."""
    posiciones = [{}, {}]
    parejas = []
    for numero, fila in enumerate(clases):
        y = 170 + numero * PASO_FILA
        for indice, entidad in enumerate((fila.gold, fila.pred)):
            if entidad:
                posiciones[indice].setdefault(entidad.iri, y)
        if fila.gold and fila.pred:
            parejas.append((fila.gold.iri, fila.pred.iri))
    for grafo, lado in zip(grafos, posiciones):
        # Incluye superclases nombradas usadas sin declaración de owl:Class.
        for hijo, padre in sorted(grafo.subject_objects(RDFS.subClassOf), key=str):
            if isinstance(hijo, URIRef) and isinstance(padre, URIRef):
                for iri in (hijo, padre):
                    if iri not in lado:
                        lado[iri] = max(lado.values(), default=80) + PASO_FILA
    return posiciones, parejas


def dibujar_general(documento, grafos, clases, propiedades, avisos):
    vista = Vista(documento, "pajaro", "Vista de pájaro")
    posiciones, parejas = posiciones_clases(grafos, clases)
    x_gold = 390
    x_pred = 830
    vista.texto("Comparación de ontologías · Vista de pájaro", 40, 20, 1120, 42, 27, True)
    vista.texto("Triángulo hueco = subclase · Flecha con nombre = dominio → rango · Línea discontinua = pareja CSV", 40, 67, 1160)
    vista.caja("Gold · Referencia", 40, 110, 520, 38, tono="gold", fuerte=True)
    vista.texto("Correspondencias del CSV", 580, 110, 230, 38, 14, True)
    vista.caja("Pred · Generada", 830, 110, 520, 38, tono="pred", fuerte=True)
    figuras = [{}, {}]
    for indice, (lado, x) in enumerate((("gold", x_gold), ("pred", x_pred))):
        for iri, y in posiciones[indice].items():
            figuras[indice][iri] = vista.caja(
                nombre(iri), x, y, ANCHO_CLASE, ALTO_CLASE,
                tono=lado, fuerte=True, ayuda=str(iri),
            )
    for gold, pred in parejas:
        vista.flecha(figuras[0][gold], figuras[1][pred], None)

    parejas_propiedad = defaultdict(list)
    emparejadas = (fila for fila in propiedades if fila.gold and fila.pred)
    for numero, fila in enumerate(emparejadas, start=1):
        for indice, entidad in enumerate((fila.gold, fila.pred)):
            parejas_propiedad[indice, entidad.iri].append(f"P{numero}")
    notas = [[], []]
    for indice, (grafo, lado, x) in enumerate(zip(grafos, ("gold", "pred"), (x_gold, x_pred))):
        carril = 0
        for hijo, padre in sorted(grafo.subject_objects(RDFS.subClassOf), key=str):
            if hijo not in figuras[indice] or padre not in figuras[indice]:
                continue
            dibujar_carril(vista, figuras[indice], posiciones[indice], hijo, padre,
                           lado, x, carril, subclase=True)
            carril += 1
        entidades = {}
        for fila in propiedades:
            entidad = (fila.gold, fila.pred)[indice]
            if entidad:
                entidades[entidad.iri, entidad.tipo] = entidad
        for entidad in sorted(entidades.values(), key=lambda e: (str(e.iri), e.tipo)):
            iri = entidad.iri
            marca = ", ".join(parejas_propiedad[indice, iri])
            etiqueta = nombre(iri) + (f" [{marca}]" if marca else "")
            if extremos_nombrados(entidad):
                dibujar_carril(
                    vista, figuras[indice], posiciones[indice], entidad.dominio[0],
                    entidad.rango[0], lado, x, carril, etiqueta=etiqueta,
                )
                carril += 1
            else:
                notas[indice].append(etiqueta + "\n" + resumen_propiedad(grafo, entidad).split("\n", 1)[1])
        axiomas_complejos = sum(
            1 for sujeto, predicado, valor in grafo
            if predicado in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith)
            and not (predicado == RDFS.subClassOf and sujeto in figuras[indice] and valor in figuras[indice])
        )
        notas[indice].append(f"Otros axiomas de clase fuera de esta vista: {axiomas_complejos}. Consultar OWL.")

    y_notas = max((y for lado in posiciones for y in lado.values()), default=170) + 82
    altos_notas = []
    for lado, textos, x in zip(("gold", "pred"), notas, (40, 830)):
        altos_notas.append(bloque_texto(vista, "\n\n".join(textos), x, y_notas, 520, lado))
    if avisos:
        bloque_texto(vista, "Revisar correspondencias\n" + "\n".join(avisos),
                     40, y_notas + max(altos_notas) + 20, 1310)


def dibujar_carril(vista, figuras, posiciones, origen, destino, lado, x, numero,
                   etiqueta="", subclase=False):
    """Reserva un carril exterior por relación y un bucle para autorrelaciones."""
    y_origen = posiciones[origen] + ALTO_CLASE / 2
    y_destino = posiciones[destino] + ALTO_CLASE / 2
    extremo = 0 if lado == "gold" else 1
    carril_x = x - 35 - numero * 26 if lado == "gold" else x + ANCHO_CLASE + 45 + numero * 90
    puntos = ((carril_x, y_origen), (carril_x, y_destino))
    puertos = (extremo, .5, extremo, .5)
    if origen == destino:
        puntos = ((x + 125, posiciones[origen] - 25), (x + 45, posiciones[origen] - 25))
        puertos = (.75, 0, .25, 0)
    vista.flecha(figuras[origen], figuras[destino], lado, etiqueta=etiqueta,
                 subclase=subclase, puertos=puertos, puntos=puntos)


def grupo_dominio(fila):
    """Prefiere el dominio nombrado de Pred y, después, el de Gold."""
    for lado, entidad in (("Pred", fila.pred), ("Gold", fila.gold)):
        if entidad and len(entidad.dominio) == 1 and isinstance(entidad.dominio[0], URIRef):
            return lado, entidad.dominio[0]
    return "Sin un único dominio nombrado", None


def dibujar_por_dominios(documento, grafos, propiedades, avisos):
    vista = Vista(documento, "dominios", "Vista por dominios")
    vista.texto("Comparación de ontologías · Vista por dominios", 40, 20, 1160, 42, 27, True)
    vista.texto("Agrupación por dominio nombrado de Pred; se usa Gold cuando Pred carece de uno único.", 40, 67, 1200)
    vista.caja("Gold · Referencia", 40, 110, 600, 38, tono="gold", fuerte=True)
    vista.caja("Pred · Generada", 680, 110, 600, 38, tono="pred", fuerte=True)
    grupos = defaultdict(list)
    for fila in propiedades:
        grupos[grupo_dominio(fila)].append(fila)
    y = 168
    for (lado, dominio), filas in sorted(grupos.items(), key=lambda par: (par[0][1] is None, par[0][0], str(par[0][1]))):
        titulo = f"Dominio {lado} · {nombre(dominio)}" if dominio else lado
        vista.caja(titulo, 40, y, 1240, 30, tono="neutro", fuerte=True)
        y += 42
        for fila in filas:
            alturas = []
            for indice, (entidad, tono, x) in enumerate(((fila.gold, "gold", 40), (fila.pred, "pred", 680))):
                alturas.append(dibujar_propiedad(vista, grafos[indice], entidad, tono, x, y))
            y += max(alturas)
            if fila.informe:
                dominio_estado, rango_estado = fila.informe
                vista.texto(f"Informe CSV · Dominio {dominio_estado} · Rango {rango_estado}", 40, y, 1240, 25, 12)
                y += 27
            y += 22
        y += 12
    texto = "Cada fila conserva una pareja del CSV o una propiedad sin pareja. Los estados del informe se leen del CSV."
    if avisos:
        texto += "\nRevisar correspondencias\n" + "\n".join(avisos)
    bloque_texto(vista, texto, 40, y, 1240)


def dibujar_propiedad(vista, grafo, entidad, lado, x, y):
    if entidad is None:
        vista.texto("Sin pareja en el CSV", x, y + 20, 600, 32, 13)
        return 75
    if extremos_nombrados(entidad):
        dominio, rango = entidad.dominio[0], entidad.rango[0]
        origen = vista.caja(nombre(dominio), x, y + 26, 150, 40, tono=lado, ayuda=str(dominio))
        destino = vista.caja(nombre(rango), x + 450, y + 26, 150, 40, tono=lado, ayuda=str(rango))
        vista.flecha(origen, destino, lado, etiqueta=nombre(entidad.iri))
        return 82
    texto = resumen_propiedad(grafo, entidad)
    return bloque_texto(vista, texto, x, y, 600, lado)


def generar(args):
    grafos, clases, propiedades, avisos = cargar(args)
    documento = ET.Element("mxfile", host="app.diagrams.net", type="device", compressed="false")
    dibujar_general(documento, grafos, clases, propiedades, avisos)
    dibujar_por_dominios(documento, grafos, propiedades, avisos)
    return documento, avisos


def main():
    parser = crear_argumentos()
    parser.description = "Genera dos páginas editables en draw.io: vista de pájaro y vista por dominios."
    parser.add_argument("--salida", type=Path,
                        default=Path(__file__).resolve().parent / "salidas" / "modelo_dos_vistas.drawio")
    args = parser.parse_args()
    temporal = None
    try:
        documento, avisos = generar(args)
        ET.indent(documento)
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=args.salida.parent, suffix=".tmp", delete=False) as archivo:
            temporal = Path(archivo.name)
            ET.ElementTree(documento).write(archivo, encoding="utf-8", xml_declaration=True)
        os.replace(temporal, args.salida)
    except (OSError, ValueError, UnicodeError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    print(f"Generado: {args.salida}")
    print("Páginas: Vista de pájaro · Vista por dominios")
    for aviso in avisos:
        print(f"AVISO: {aviso}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
