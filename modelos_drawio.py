"""Datos y figuras compartidos por las tres vistas de comparación."""

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import sys
import textwrap
import xml.etree.ElementTree as ET

from rdflib import BNode, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from inspeccionar_entradas import (
    crear_argumentos, crear_indice_nombres, leer_csv, leer_ontologia, resolver_nombre,
)


@dataclass(frozen=True)
class Entidad:
    iri: URIRef
    tipo: str
    dominio: tuple = ()
    rango: tuple = ()
    axiomas: tuple = ()


@dataclass(frozen=True)
class Fila:
    gold: Entidad | None
    pred: Entidad | None
    informe: tuple[str, str] | None = None


def nombre(termino):
    if isinstance(termino, URIRef):
        texto = str(termino)
        for prefijo, ns in (("xsd", "http://www.w3.org/2001/XMLSchema#"),
                            ("owl", str(OWL))):
            if texto.startswith(ns):
                return f"{prefijo}:{texto.removeprefix(ns)}"
        return texto.rstrip("/#").rsplit("#", 1)[-1].rsplit("/", 1)[-1] or texto
    return termino.n3()


def corto(texto, limite=35):
    return texto if len(texto) <= limite else texto[:limite - 1] + "…"


def expresion(grafo, termino, profundidad=5, presupuesto=None):
    """Resume estructuras RDF explícitas, con límites para listas y anidamiento."""
    if not isinstance(termino, BNode):
        return corto(nombre(termino), 100)
    if presupuesto is None:
        presupuesto = [45]
    if profundidad == 0 or presupuesto[0] <= 0:
        return "[expresión anidada abreviada]"
    presupuesto[0] -= 1

    def hijo(nodo):
        return expresion(grafo, nodo, profundidad - 1, presupuesto)

    for predicado, operador in ((OWL.unionOf, " o "), (OWL.intersectionOf, " y "),
                                (OWL.oneOf, ", ")):
        lista = grafo.value(termino, predicado)
        if lista is None:
            continue
        vistos, miembros = set(), []
        while lista != RDF.nil and lista not in vistos and len(miembros) < 10:
            vistos.add(lista)
            primero = grafo.value(lista, RDF.first)
            if primero is None:
                break
            miembros.append(hijo(primero))
            lista = grafo.value(lista, RDF.rest)
        if lista != RDF.nil:
            miembros.append("[lista incompleta o abreviada]")
        apertura, cierre = ("{", "}") if predicado == OWL.oneOf else ("(", ")")
        return apertura + operador.join(miembros) + cierre

    for predicado in (OWL.complementOf, OWL.datatypeComplementOf):
        complemento = grafo.value(termino, predicado)
        if complemento is not None:
            return "no " + hijo(complemento)

    propiedad = grafo.value(termino, OWL.onProperty)
    if propiedad is not None:
        for predicado, operador in (
            (OWL.someValuesFrom, "some"), (OWL.allValuesFrom, "only"),
            (OWL.hasValue, "value"), (OWL.hasSelf, "Self"),
            (OWL.minCardinality, "min"), (OWL.maxCardinality, "max"),
            (OWL.cardinality, "exactly"), (OWL.minQualifiedCardinality, "min"),
            (OWL.maxQualifiedCardinality, "max"), (OWL.qualifiedCardinality, "exactly"),
        ):
            valor = grafo.value(termino, predicado)
            if valor is not None:
                clase = grafo.value(termino, OWL.onClass)
                if clase is None:
                    clase = grafo.value(termino, OWL.onDataRange)
                calificador = " " + hijo(clase) if clase is not None else ""
                argumento = str(valor) if operador in {"min", "max", "exactly"} else hijo(valor)
                return f"{hijo(propiedad)} {operador} {argumento}{calificador}"
    tipo_dato = grafo.value(termino, OWL.onDatatype)
    if tipo_dato is not None:
        return f"{hijo(tipo_dato)} [facetas de datatype: consultar RDF]"
    predicados = sorted({nombre(p) for p in grafo.predicates(termino) if p != RDF.type})
    return "[expresión anónima: " + (", ".join(predicados[:5]) or "consultar RDF") + "]"


def inventario(grafo):
    entidades = {}
    for rdf_tipo, tipo in ((OWL.ObjectProperty, "objeto"), (OWL.DatatypeProperty, "datos")):
        for iri in grafo.subjects(RDF.type, rdf_tipo):
            if isinstance(iri, URIRef):
                clave = (iri, tipo)
                entidades[clave] = Entidad(
                    iri, tipo, tuple(sorted(grafo.objects(iri, RDFS.domain), key=str)),
                    tuple(sorted(grafo.objects(iri, RDFS.range), key=str)),
                )
    clases = set(grafo.subjects(RDF.type, OWL.Class))
    for entidad in entidades.values():
        clases.update(entidad.dominio)
        if entidad.tipo == "objeto":
            clases.update(entidad.rango)
    for iri in clases:
        if isinstance(iri, URIRef) and iri != OWL.Thing:
            axiomas = tuple(
                (nombre(p), valor)
                for p in (RDFS.subClassOf, OWL.equivalentClass, OWL.disjointWith)
                for valor in sorted(grafo.objects(iri, p), key=str)
            )
            entidades[(iri, "clase")] = Entidad(iri, "clase", axiomas=axiomas)
    return entidades


def cargar(args):
    grafos = (
        leer_ontologia(args.referencia, args.formato_referencia),
        leer_ontologia(args.generada, args.formato_generada),
    )
    inventarios = tuple(inventario(grafo) for grafo in grafos)
    informes = defaultdict(list)
    columnas = ("GoldPredicate", "PredPredicate", "DomainStatus", "RangeStatus")
    for fila in leer_csv(args.dominios_rangos, columnas):
        clave = (fila["GoldPredicate"], fila["PredPredicate"], fila.get("PropertyType", ""))
        informes[clave].append((fila["DomainStatus"], fila["RangeStatus"]))
    avisos = []
    filas = []
    for archivo, tipos in ((args.clases, (OWL.Class,)),
                           (args.propiedades, (OWL.ObjectProperty, OWL.DatatypeProperty))):
        indices = tuple(crear_indice_nombres(grafo, tipos) for grafo in grafos)
        etiquetas = ("clase",) if tipos == (OWL.Class,) else ("objeto", "datos")
        usadas = [set(), set()]
        resultado = []
        vistos = set()
        for fila in leer_csv(archivo, ("Gold_term", "Pre_term")):
            nombres = (fila["Gold_term"], fila["Pre_term"])
            par = []
            for etiqueta, indice, entidades in zip(nombres, indices, inventarios):
                estado, candidatas = resolver_nombre(etiqueta, indice)
                if estado != "única":
                    break
                iri = next(iter(candidatas))
                opciones = [entidades[(iri, t)] for t in etiquetas if (iri, t) in entidades]
                if len(opciones) != 1:
                    estado = "tipo ambiguo o entidad fuera del inventario"
                    break
                par.append(opciones[0])
            if len(par) != 2:
                avisos.append(f"{archivo.name}: {nombres[0]} ↔ {nombres[1]} · {estado}")
                continue
            gold, pred = par
            clave = tuple(par)
            if clave in vistos:
                continue
            vistos.add(clave)
            informe = None
            if gold.tipo == pred.tipo and gold.tipo != "clase":
                tipo = "ObjectProperty" if gold.tipo == "objeto" else "DatatypeProperty"
                estados = informes.get((*nombres, tipo), []) + informes.get((*nombres, ""), [])
                if len(estados) == 1:
                    informe = estados[0]
                elif estados:
                    avisos.append(f"Informe duplicado: {nombres[0]} ↔ {nombres[1]}")
            resultado.append(Fila(gold, pred, informe))
            for i, entidad in enumerate(par):
                usadas[i].add(entidad)
        for i, entidades in enumerate(inventarios):
            adicionales = sorted(
                (e for e in entidades.values() if e.tipo in etiquetas and e not in usadas[i]),
                key=lambda e: (nombre(e.iri).casefold(), str(e.iri), e.tipo),
            )
            resultado.extend(Fila(e, None) if i == 0 else Fila(None, e) for e in adicionales)
        filas.append(resultado)
    return grafos, *filas, avisos


PALETA = {"gold": ("#FFE3BB", "#BA7319"), "pred": ("#D5E9FF", "#438BC7"),
          "par": ("#DDEEDB", "#398553"), "neutro": ("#F4F4F4", "#999999"),
          "cambio": ("#F6D8D3", "#BE675A"), "revisar": ("#FFF2BE", "#B78B23")}
TEXTO = "text;html=0;whiteSpace=wrap;overflow=hidden;align=left;verticalAlign=middle;spacingLeft=8;"


class Pagina:
    def __init__(self, doc, identificador, titulo):
        self.id = identificador
        self.numero = 1
        pagina = ET.SubElement(doc, "diagram", id=identificador, name=titulo)
        modelo = ET.SubElement(pagina, "mxGraphModel", page="0", grid="1", gridSize="10", tooltips="1")
        self.raiz = ET.SubElement(modelo, "root")
        ET.SubElement(self.raiz, "mxCell", id="0")
        ET.SubElement(self.raiz, "mxCell", id="1", parent="0")

    def siguiente(self):
        self.numero += 1
        return str(self.numero)

    def caja(self, texto, x, y, ancho, alto, *, tono=None, fuerte=False, tam=15,
             enlace=None, ayuda=None):
        identificador = self.siguiente()
        estilo = TEXTO + f"fontSize={tam};" + ("fontStyle=1;" if fuerte else "")
        if tono:
            relleno, borde = PALETA[tono]
            estilo += f"fillColor={relleno};strokeColor={borde};"
        contenedor = self.raiz
        atributos = {"id": identificador, "value": texto}
        if enlace or ayuda:
            contenedor = ET.SubElement(self.raiz, "object", id=identificador, label=texto)
            if enlace:
                contenedor.set("link", f"data:page/id,{enlace}")
            if ayuda:
                contenedor.set("tooltip", ayuda)
            atributos = {}
        celda = ET.SubElement(contenedor, "mxCell", atributos, vertex="1", parent="1", style=estilo)
        ET.SubElement(celda, "mxGeometry", {"as": "geometry", "x": str(x), "y": str(y),
                                            "width": str(ancho), "height": str(alto)})
        return identificador

    def linea(self, origen, destino, tono=None, etiqueta=""):
        estilo = "html=0;noEdgeStyle=1;exitX=1;exitY=0.5;entryX=0;entryY=0.5;"
        if tono:
            estilo += (
                f"endArrow=classic;strokeColor={PALETA[tono][1]};strokeWidth=2;"
                "fontSize=14;labelBackgroundColor=#FFFFFF;"
            )
        else:
            estilo += "dashed=1;endArrow=none;strokeColor=#999999;"
        enlace = ET.SubElement(self.raiz, "mxCell", id=self.siguiente(), parent="1", edge="1",
                               source=origen, target=destino, value=etiqueta, style=estilo)
        geo = ET.SubElement(enlace, "mxGeometry", {"as": "geometry", "relative": "1"})
        if etiqueta:
            ET.SubElement(geo, "mxPoint", {"as": "offset", "x": "0", "y": "-17"})


class Libro:
    def __init__(self, grafos, clases, propiedades, filas):
        self.doc = ET.Element("mxfile", host="app.diagrams.net", type="device")
        self.grafos, self.clases, self.propiedades, self.filas = grafos, clases, propiedades, filas
        self.detalles = {}
        self.principal = None
        candidatas, inversas = defaultdict(set), defaultdict(set)
        con_pareja = [set(), set()]
        for fila in clases:
            if fila.gold and fila.pred:
                gold, pred = fila.gold.iri, fila.pred.iri
                candidatas[gold].add(pred)
                inversas[pred].add(gold)
                con_pareja[0].add(gold)
                con_pareja[1].add(pred)
        self.alineadas = {
            gold: pred for gold, candidatos in candidatas.items() if len(candidatos) == 1
            for pred in candidatos if len(inversas[pred]) == 1
        }
        self.clases_con_pareja = con_pareja

    def pagina(self, identificador, titulo, subtitulo="", regreso=None):
        p = Pagina(self.doc, identificador, titulo)
        if identificador == "inicio":
            self.principal = p
        p.caja(corto(titulo, 100), 30, 24, 940, 43, fuerte=True, tam=25, ayuda=titulo)
        if regreso:
            p.caja("← Inicio" if regreso == "inicio" else "← Volver",
                   985, 28, 140, 34, tono="neutro", enlace=regreso)
        if subtitulo:
            p.caja(subtitulo, 30, 72, 1095, 36, tam=15)
        return p

    def detalle(self, fila):
        self.detalles[fila] = None
        return "detalle"

    def campos(self, fila):
        """Separa diferencias de extremos nombrados de expresiones por revisar."""
        comparables = fila.gold and fila.pred and fila.gold.tipo == fila.pred.tipo
        estados = {}
        for campo in ("dominio", "rango"):
            gold, pred = getattr(fila.gold, campo, ()), getattr(fila.pred, campo, ())
            if any(not isinstance(t, URIRef) for t in gold + pred):
                estados[campo] = "revisar"
            elif comparables:
                alineadas = self.alineadas if campo == "dominio" or fila.gold.tipo == "objeto" else {}
                if {alineadas.get(t, t) for t in gold} != set(pred):
                    estados[campo] = "distinto"
        return estados

    def aviso_expresion(self, fila, campo, lado=None):
        lados = (0, 1) if lado is None else (lado,)
        entidades = (fila.gold, fila.pred)
        expresiones = [
            (self.grafos[i], valor)
            for i in lados
            for valor in getattr(entidades[i], campo, ())
            if not isinstance(valor, URIRef)
        ]
        if expresiones and all(
            isinstance(valor, BNode) and (valor, OWL.unionOf, None) in grafo
            for grafo, valor in expresiones
        ):
            return "Unión por revisar"
        return "Expresión por revisar"

    def estado(self, fila):
        if fila.gold is None or fila.pred is None:
            lado, entidad = ("Gold", fila.gold) if fila.gold else ("Pred", fila.pred)
            complejos = [
                campo for campo in ("dominio", "rango")
                if any(isinstance(t, BNode) for t in getattr(entidad, campo))
            ]
            aviso = " · Expresión anónima en " + " y ".join(complejos) if complejos else ""
            return lado + " sin pareja resuelta" + aviso
        if fila.gold.tipo != fila.pred.tipo:
            return "Tipo de propiedad distinto"
        if fila.gold.tipo == "clase":
            return "Pareja del CSV"
        campos = self.campos(fila)
        cambios = [campo for campo, estado in campos.items() if estado == "distinto"]
        complejos = [campo for campo, estado in campos.items() if estado == "revisar"]
        partes = []
        if cambios:
            partes.append("Distinto en RDF: " + " y ".join(cambios))
        if complejos:
            partes.append("Revisar expresión en " + " y ".join(complejos))
        return "  |  ".join(partes) or "Sin diferencias detectadas en los extremos explícitos"

    def requiere_revision(self, fila):
        estado = self.estado(fila)
        return (
            not (fila.gold and fila.pred)
            or estado.startswith(("Tipo", "Distinto", "Revisar"))
            or any(v.strip().lower() not in {"", "tp", "tn"} for v in fila.informe or ())
        )

    def vista_general(self, titulo, subtitulo):
        """Conserva los pares y cambios primero, con un límite visible en la portada."""
        clases = self.clases[:max(14, self.filas)]
        propiedades = sorted(self.propiedades, key=lambda f: (
            not (f.gold and f.pred and self.requiere_revision(f)),
            not self.requiere_revision(f),
        ))[:self.filas]
        p = self.pagina("inicio", titulo, subtitulo)
        fuera = len(self.clases) + len(self.propiedades) - len(clases) - len(propiedades)
        p.caja(
            f"{len(clases)}/{len(self.clases)} filas de clases · "
            f"{len(propiedades)}/{len(self.propiedades)} de propiedades"
            + (f" · {fuera} más en Detalle" if fuera else ""),
            30, 103, 950, 28, tam=14,
        )
        for fila in self.clases[len(clases):]:
            self.detalle(fila)
        visibles = set(propiedades)
        for fila in self.propiedades:
            if fila not in visibles:
                self.detalle(fila)
        return p, clases, propiedades

    def inventario_visible(self, p, clases, x=30, y=143, ancho=370):
        p.caja("Clases", x, y, ancho, 29, fuerte=True, tam=18)
        self.cabeceras(p, x, y + 34, ancho, espacio=50)
        for j, fila in enumerate(clases):
            self.fila_clase(p, fila, y + 75 + j * 41, x=x, ancho=ancho)

    def fila_clase(self, p, fila, y, x=30, ancho=510):
        w = (ancho - 50) // 2
        ids = []
        par = bool(fila.gold and fila.pred)
        tiene_axiomas = any(e and e.axiomas for e in (fila.gold, fila.pred))
        enlace = self.detalle(fila) if tiene_axiomas else None
        for i, entidad in enumerate((fila.gold, fila.pred)):
            if entidad:
                tono = "par" if par else ("gold", "pred")[i]
                marca = " ↗" if enlace else ""
                ids.append(p.caja(corto(nombre(entidad.iri), max(12, w // 8)) + marca,
                                  x + i * (w + 50), y, w, 35, tono=tono,
                                  enlace=enlace, ayuda=str(entidad.iri)))
        if par:
            p.linea(*ids)

    def cabeceras(self, p, x, y, ancho, espacio=30):
        w = (ancho - espacio) // 2
        p.caja("Gold", x, y, w, 32, tono="gold", fuerte=True)
        p.caja("Pred", x + w + espacio, y, w, 32, tono="pred", fuerte=True)

    def fila_propiedad(self, p, fila, y, x=30, ancho=1095):
        w = (ancho - 30) // 2
        par = bool(fila.gold and fila.pred)
        detalle = self.detalle_propiedad(fila)
        for i, entidad in enumerate((fila.gold, fila.pred)):
            inicio = x + i * (w + 30)
            if entidad is None:
                p.caja("—", inicio, y + 13, w, 29, tam=14)
                continue
            tono = "par" if par else ("gold", "pred")[i]
            self.propiedad(p, entidad, i, inicio, y, w, tono)
        etiquetas = []
        for campo, estado in self.campos(fila).items():
            if estado == "distinto":
                etiquetas.append((f"Cambia {campo}", "cambio", None))
            else:
                aviso = self.aviso_expresion(fila, campo)
                etiquetas.append((f"{campo.capitalize()} · {aviso}", "revisar", detalle))
        if par and fila.gold.tipo != fila.pred.tipo:
            etiquetas.append(("Cambia tipo", "cambio", None))
        if not par:
            etiquetas.append(("Gold sin pareja" if fila.gold else "Pred sin pareja", None, None))
        if detalle:
            etiquetas.append(("Detalle ↗", None, detalle))
        for etiqueta, tono, enlace in etiquetas:
            ancho_etiqueta = len(etiqueta) * 7 + 24
            p.caja(etiqueta, x, y + 54, ancho_etiqueta, 23, tono=tono, tam=13,
                   enlace=enlace, ayuda=self.ayuda_propiedad(fila))
            x += ancho_etiqueta + 7

    def detalle_propiedad(self, fila):
        extremos = [valores for e in (fila.gold, fila.pred) if e
                    for valores in (e.dominio, e.rango)]
        if fila.informe or any(
            len(valores) > 1 or any(not isinstance(t, URIRef) for t in valores)
            for valores in extremos
        ):
            return self.detalle(fila)
        return None

    def ayuda_propiedad(self, fila):
        ayuda = [self.estado(fila)]
        for lado, entidad in zip(("Gold", "Pred"), (fila.gold, fila.pred)):
            if entidad:
                ayuda.append(f"{lado}: {entidad.iri}")
        return "\n".join(ayuda)

    def propiedad(self, p, entidad, lado, x, y, ancho, tono):
        def unico(terminos):
            return len(terminos) == 1 and isinstance(terminos[0], URIRef)

        etiqueta = nombre(entidad.iri)
        if unico(entidad.dominio) and unico(entidad.rango):
            dominio, rango = entidad.dominio[0], entidad.rango[0]
            if entidad.tipo == "datos":
                p.caja(corto(nombre(dominio), 34), x, y, ancho, 25, tono=tono, ayuda=str(dominio))
                p.caja(corto(f"{etiqueta}: {nombre(rango)}", 65), x, y + 25, ancho, 25,
                       tono=tono, ayuda=f"{entidad.iri}\n{rango}")
                return
            w = min(148, ancho // 3)
            lado_tono = ("gold", "pred")[lado]
            a = p.caja(corto(nombre(dominio), 18), x, y + 19, w, 32,
                       tono="par" if dominio in self.clases_con_pareja[lado] else lado_tono,
                       ayuda=str(dominio))
            b = p.caja(corto(nombre(rango), 18), x + ancho - w, y + 19, w, 32,
                       tono="par" if rango in self.clases_con_pareja[lado] else lado_tono,
                       ayuda=str(rango))
            p.linea(a, b, tono, corto(etiqueta, max(14, (ancho - 2*w) // 8)))
            return
        tipo = " · atributo" if entidad.tipo == "datos" else ""
        p.caja(corto(etiqueta + tipo, 51), x, y, ancho, 24, tono=tono, fuerte=True, ayuda=str(entidad.iri))
        d, r = resumen_extremo(entidad.dominio), resumen_extremo(entidad.rango)
        p.caja(f"D: {d}  ·  R: {r}", x, y + 25, ancho, 26, tam=13)

    def escribir_detalles(self, avisos):
        if not (self.detalles or avisos):
            return
        self.principal.caja("Detalle ↗", 985, 28, 140, 34, tono="neutro", enlace="detalle")
        p = self.pagina("detalle", "Detalle", "Informe CSV, axiomas explícitos, expresiones y filas adicionales.", "inicio")
        y = 122
        for fila in sorted(self.detalles, key=lambda f: (not f.informe, (f.gold or f.pred).tipo == "clase")):
            nombres = " ↔ ".join(nombre(e.iri) for e in (fila.gold, fila.pred) if e)
            p.caja(corto(nombres, 105), 35, y, 1080, 32, fuerte=True, tono="neutro")
            y += 37
            lineas = []
            for lado, entidad, grafo in zip(("Gold", "Pred"), (fila.gold, fila.pred), self.grafos):
                if entidad is None:
                    continue
                lineas.append(f"{lado} · {entidad.tipo} · {entidad.iri}")
                if entidad.tipo == "clase":
                    campos = entidad.axiomas
                else:
                    campos = tuple((r, v) for r, valores in (("Dominio", entidad.dominio),
                                                             ("Rango", entidad.rango))
                                   for v in (valores or (None,)))
                for rotulo, valor in campos:
                    texto = "sin declaración explícita" if valor is None else expresion(grafo, valor)
                    lineas.append(f"  {rotulo}: {texto}")
                lineas.append("")
            if fila.informe:
                d, r = fila.informe
                lineas.append(f"Informe CSV · Dominio: {d or '—'} · Rango: {r or '—'}")
            y = self.bloque_texto(p, lineas, y) + 19
        if avisos:
            p.caja(f"Filas del CSV que requieren revisión ({len(avisos)})",
                   35, y, 1080, 32, fuerte=True, tono="gold")
            self.bloque_texto(p, avisos, y + 37)

    @staticmethod
    def bloque_texto(p, textos, y):
        for texto in textos:
            for linea in textwrap.wrap(texto, width=115) or [""]:
                p.caja(linea, 35, y, 1080, 23, tam=14)
                y += 23
        return y


def resumen_extremo(valores, limite=24):
    if not valores:
        return "sin declarar"
    if len(valores) > 1:
        return f"{len(valores)} axiomas"
    if isinstance(valores[0], BNode):
        return "expresión anónima"
    return corto(nombre(valores[0]), limite)


def ejecutar(nombre_modelo, dibujar):
    parser = crear_argumentos()
    parser.description = f"Genera un draw.io editable: {nombre_modelo}."
    parser.add_argument("--filas", type=int, default=12, metavar="N",
                        help="Máximo de filas de propiedades en la vista principal (2 a 60).")
    parser.add_argument("--salida", type=Path,
                        default=Path(__file__).resolve().parent / "salidas" / f"{nombre_modelo}.drawio")
    args = parser.parse_args()
    if not 2 <= args.filas <= 60:
        parser.error("--filas debe estar entre 2 y 60.")
    try:
        grafos, clases, propiedades, avisos = cargar(args)
        libro = Libro(grafos, clases, propiedades, args.filas)
        dibujar(libro)
        libro.escribir_detalles(avisos)
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        ET.indent(libro.doc)
        ET.ElementTree(libro.doc).write(args.salida, encoding="utf-8", xml_declaration=True)
    except (OSError, UnicodeError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{args.salida} · {len(libro.doc)} páginas")
    return 0
