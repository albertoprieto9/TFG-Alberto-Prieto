"""Comprueba la identificación de entidades, no su equivalencia lógica."""

import unittest

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from inspeccionar_entradas import (
    DATOS_AWO, consultar_propiedad, crear_indice_nombres, leer_csv, leer_ontologia,
    resolver_nombre,
)


class ResolucionTest(unittest.TestCase):
    def test_colision_entre_etiqueta_y_nombre_local_no_elige_una(self):
        grafo = Graph()
        primera = URIRef("https://uno.example/Animal")
        segunda = URIRef("https://dos.example#OtraClase")
        for entidad in (primera, segunda):
            grafo.add((entidad, RDF.type, OWL.Class))
        grafo.add((primera, RDFS.label, Literal("Animal", lang="en")))
        grafo.add((segunda, RDFS.label, Literal("Animal", lang="es")))
        indice = crear_indice_nombres(grafo, (OWL.Class,))
        estado, candidatas = resolver_nombre("Animal", indice)
        self.assertEqual(estado, "ambiguo")
        self.assertEqual(set(candidatas), {primera, segunda})
        self.assertEqual(candidatas[primera], {"nombre local", "rdfs:label"})

    def test_respeta_tipo_declaracion_y_texto_exacto(self):
        grafo = Graph()
        clase = URIRef("https://example.org#Animal")
        propiedad = URIRef("https://example.org#relacion")
        sin_declarar = URIRef("https://example.org#PlantPart")
        grafo.add((clase, RDF.type, OWL.Class))
        grafo.add((clase, RDFS.label, Literal("Animal", lang="en")))
        grafo.add((clase, RDFS.label, Literal("Animal", lang="es")))
        grafo.add((propiedad, RDF.type, OWL.ObjectProperty))
        grafo.add((propiedad, RDFS.label, Literal("Animal")))
        grafo.add((propiedad, RDFS.domain, sin_declarar))
        grafo.add((BNode(), RDF.type, OWL.Class))
        indice = crear_indice_nombres(grafo, (OWL.Class,))
        self.assertEqual(resolver_nombre("Animal", indice)[0], "única")
        for nombre in ("animal", " Animal ", "PlantPart", "relacion", ""):
            self.assertEqual(resolver_nombre(nombre, indice)[0], "sin resolver")

    def test_pares_awo_resuelven_sin_cambiar_los_grafos(self):
        gold = leer_ontologia(DATOS_AWO / "awo-referencia.owl", "xml")
        pred = leer_ontologia(DATOS_AWO / "awo-generada.owl", "xml")
        grafos_originales = (set(gold), set(pred))
        for archivo, tipos in (
            ("class_best_matching.csv", (OWL.Class,)),
            ("property_best_matching.csv", (OWL.ObjectProperty, OWL.DatatypeProperty)),
        ):
            indices = (crear_indice_nombres(gold, tipos), crear_indice_nombres(pred, tipos))
            for fila in leer_csv(DATOS_AWO / archivo, ("Gold_term", "Pre_term")):
                for campo, indice in zip(("Gold_term", "Pre_term"), indices):
                    self.assertEqual(resolver_nombre(fila[campo], indice)[0], "única")
        indice_pred = crear_indice_nombres(pred, (OWL.ObjectProperty,))
        estado, candidatas = resolver_nombre("is part of plant", indice_pred)
        self.assertEqual(set(candidatas), {URIRef("http://www.semanticweb.org/myontology#isPartOfPlant")})
        self.assertEqual((set(gold), set(pred)), grafos_originales)


class ConsultaPropiedadTest(unittest.TestCase):
    def test_sin_identificacion_unica_no_finge_ausencia_de_axiomas(self):
        grafo = Graph()
        for nombre in ("a", "b"):
            iri = URIRef(f"https://example.org#{nombre}")
            grafo.add((iri, RDF.type, OWL.ObjectProperty))
            grafo.add((iri, RDFS.label, Literal("compartida")))
            grafo.add((iri, RDFS.domain, URIRef("https://example.org#Clase")))
        indice = crear_indice_nombres(grafo, (OWL.ObjectProperty,))
        for nombre, esperado in (("compartida", "ambiguo"), ("desconocida", "sin resolver")):
            resultado = consultar_propiedad(grafo, nombre, indice)
            self.assertEqual(resultado["estado"], esperado)
            self.assertIsNone(resultado["iri"])
            self.assertIsNone(resultado["dominios"])
            self.assertIsNone(resultado["rangos"])

    def test_conserva_varios_valores_y_expresiones_anonimas(self):
        grafo = Graph()
        propiedad = URIRef("https://example.org#relacion")
        clase_sin_declarar = URIRef("https://example.org#Clase")
        expresion = BNode()
        grafo.add((propiedad, RDF.type, OWL.ObjectProperty))
        grafo.add((propiedad, RDFS.range, expresion))
        grafo.add((propiedad, RDFS.range, clase_sin_declarar))
        indice = crear_indice_nombres(grafo, (OWL.ObjectProperty,))
        resultado = consultar_propiedad(grafo, "relacion", indice)
        self.assertEqual(resultado["dominios"], [])
        self.assertEqual(set(resultado["rangos"]), {expresion, clase_sin_declarar})

    def test_filas_awo_consultan_su_lado_y_preservan_informe(self):
        gold = leer_ontologia(DATOS_AWO / "awo-referencia.owl", "xml")
        pred = leer_ontologia(DATOS_AWO / "awo-generada.owl", "xml")
        filas = leer_csv(DATOS_AWO / "triple_layer3_pairs.csv", ("GoldPredicate", "PredPredicate"))
        originales = [dict(fila) for fila in filas]
        g_idx = crear_indice_nombres(gold, (OWL.ObjectProperty,))
        p_idx = crear_indice_nombres(pred, (OWL.ObjectProperty,))
        for fila, dominio, rango in zip(filas, ("Animal", "PlantPart"), ("Animal", "Plant")):
            g = consultar_propiedad(gold, fila["GoldPredicate"], g_idx)
            p = consultar_propiedad(pred, fila["PredPredicate"], p_idx)
            self.assertEqual(g["estado"], "única")
            self.assertEqual(g["dominios"], [])
            self.assertEqual(g["rangos"], [])
            self.assertEqual(p["estado"], "única")
            self.assertEqual(p["dominios"], [URIRef(f"http://www.semanticweb.org/myontology#{dominio}")])
            self.assertEqual(p["rangos"], [URIRef(f"http://www.semanticweb.org/myontology#{rango}")])
        self.assertEqual(filas, originales)
        eats = consultar_propiedad(gold, "eats", g_idx)
        self.assertEqual(len(eats["rangos"]), 1)
        self.assertIsInstance(eats["rangos"][0], BNode)


if __name__ == "__main__":
    unittest.main()
