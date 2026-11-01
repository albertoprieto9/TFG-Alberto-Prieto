"""Comprueba identidad de figuras y rechazo explícito de casos no soportados."""

import unittest

from rdflib import Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from inspeccionar_entradas import DATOS_AWO, leer_csv, leer_ontologia
from practica_drawio import (
    crear_documento, dibujar_par_propiedades, seleccionar_comparacion,
)


class DiagramaTest(unittest.TestCase):
    def setUp(self):
        self.referencia = leer_ontologia(DATOS_AWO / "awo-referencia.owl", "xml")
        self.generada = leer_ontologia(DATOS_AWO / "awo-generada.owl", "xml")
        pares = leer_csv(DATOS_AWO / "property_best_matching.csv", ("Gold_term", "Pre_term"))
        self.par = next(f for f in pares if f["Gold_term"] == "eaten-by")
        filas = leer_csv(
            DATOS_AWO / "triple_layer3_pairs.csv", ("GoldPredicate", "PredPredicate")
        )
        self.comparacion = seleccionar_comparacion(filas, self.par)
        self.documento, self.raiz = crear_documento()

    def dibujar(self):
        clases = {}
        dibujar_par_propiedades(
            self.raiz, self.referencia, self.generada,
            clases, self.par, self.comparacion, 0
        )
        return clases

    def test_animal_unico_con_dominio_y_rango_separados(self):
        original = dict(self.comparacion)
        clases = self.dibujar()
        self.assertEqual(set(clases), {URIRef("http://www.semanticweb.org/myontology#Animal")})
        celdas = {c.get("id"): c for c in self.raiz.findall("mxCell")}
        dominio = celdas["dominio-1"]
        rango = celdas["rango-1"]
        self.assertEqual(dominio.get("source"), rango.get("source"))
        self.assertEqual(dominio.get("target"), rango.get("target"))
        self.assertEqual(celdas[dominio.get("target")].get("value"), "pred:Animal")
        self.assertNotEqual(dominio.get("style"), rango.get("style"))
        self.assertEqual(self.comparacion, original)

    def test_propiedad_ambigua_no_produce_figuras(self):
        otra = URIRef("https://example.org#otraPropiedad")
        self.generada.add((otra, RDF.type, OWL.ObjectProperty))
        self.generada.add((otra, RDFS.label, Literal("is eaten by")))
        with self.assertRaisesRegex(ValueError, "ambiguo"):
            self.dibujar()
        self.assertFalse(any(c.get("vertex") == "1" for c in self.raiz))

    def test_rango_de_referencia_no_se_omite_silenciosamente(self):
        propiedad = URIRef(
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#eaten-by"
        )
        self.referencia.add((propiedad, RDFS.range, URIRef("https://example.org#Clase")))
        with self.assertRaisesRegex(ValueError, "lado de referencia"):
            self.dibujar()
        self.assertFalse(any(c.get("vertex") == "1" for c in self.raiz))


if __name__ == "__main__":
    unittest.main()
