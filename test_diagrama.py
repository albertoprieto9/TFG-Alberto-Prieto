"""Comprueba identidad de figuras y representación de extremos RDF y avisos."""

import unittest

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from inspeccionar_entradas import DATOS_AWO, leer_csv, leer_ontologia
from practica_drawio import (
    agregar_clases_pendientes, agregar_dominios_y_rangos,
    crear_documento, dibujar_par_propiedades,
    agregar_propiedades_pendientes, obtener_o_crear_clase,
    obtener_o_crear_propiedad, seleccionar_comparacion,
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
        self.propiedades_referencia = {}
        self.propiedades_generada = {}

    def dibujar(self):
        clases = {}
        dibujar_par_propiedades(
            self.raiz, self.referencia, self.generada,
            self.propiedades_referencia, self.propiedades_generada,
            self.par, self.comparacion, 0
        )
        agregar_dominios_y_rangos(
            self.raiz, self.generada, self.propiedades_generada, clases,
            "http://www.semanticweb.org/myontology#", "pred", 820
        )
        return clases

    def test_animal_unico_con_dominio_y_rango_separados(self):
        original = dict(self.comparacion)
        clases = self.dibujar()
        self.assertEqual(set(clases), {URIRef("http://www.semanticweb.org/myontology#Animal")})
        celdas = {c.get("id"): c for c in self.raiz.findall("mxCell")}
        dominio = celdas["propiedad-pred-1-dominio-1"]
        rango = celdas["propiedad-pred-1-rango-1"]
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

    def test_clases_adicionales_filtran_y_no_inventan_correspondencias(self):
        grafo = Graph()
        existente = URIRef("https://example.org#Existente")
        nueva = URIRef("https://example.org#Nueva")
        solo_referenciada = URIRef("https://example.org#SoloReferenciada")
        for recurso in (existente, nueva, BNode(), OWL.Thing):
            grafo.add((recurso, RDF.type, OWL.Class))
        grafo.add((nueva, RDFS.subClassOf, solo_referenciada))
        triples_originales = set(grafo)
        clases = {}
        figura_existente = obtener_o_crear_clase(
            self.raiz, clases, existente, "https://example.org#", "gold", 100, 100
        )
        id_existente = figura_existente["id"]

        agregadas = agregar_clases_pendientes(
            self.raiz, grafo, clases, "https://example.org#", "gold", 100
        )
        self.assertEqual(agregadas, 1)
        self.assertEqual(set(clases), {existente, nueva})
        self.assertEqual(clases[existente], {"id": id_existente, "y": 100})
        self.assertFalse(any(c.get("edge") == "1" for c in self.raiz))
        self.assertEqual(set(grafo), triples_originales)
        self.assertEqual(agregar_clases_pendientes(
            self.raiz, grafo, clases, "https://example.org#", "gold", 100
        ), 0)
        self.assertEqual(len(self.raiz.findall("mxCell[@vertex='1']")), 2)

    def test_rango_con_iri_de_referencia_se_dibuja_en_su_lado(self):
        propiedad = URIRef(
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#eaten-by"
        )
        clase = URIRef("https://example.org#Clase")
        self.referencia.add((propiedad, RDFS.range, clase))
        clases_pred = self.dibujar()
        clases_gold = {}
        avisos = agregar_dominios_y_rangos(
            self.raiz, self.referencia, self.propiedades_referencia, clases_gold,
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#",
            "gold", 100
        )
        self.assertEqual(avisos, [])
        self.assertEqual(set(clases_gold), {clase})
        self.assertNotIn(clase, clases_pred)
        arista = self.raiz.find("mxCell[@id='propiedad-gold-1-rango-1']")
        self.assertEqual(arista.get("target"), clases_gold[clase]["id"])
        self.assertEqual(arista.get("source"), self.propiedades_referencia[propiedad]["id"])

    def test_rango_anonimo_real_se_avisa_sin_figura_o_conexion_inventada(self):
        registro = {}
        agregar_propiedades_pendientes(
            self.raiz, self.referencia, registro,
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#",
            "gold", 60
        )
        clases = {}
        triples_antes = set(self.referencia)
        avisos = agregar_dominios_y_rangos(
            self.raiz, self.referencia, registro, clases,
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#",
            "gold", 100
        )
        self.assertEqual(avisos, [
            "gold:eats — rango: expresión anónima presente; sin desarrollar."
        ])
        self.assertEqual(clases, {})
        self.assertFalse(any(c.get("edge") == "1" for c in self.raiz))
        self.assertEqual(set(self.referencia), triples_antes)

    def test_todas_las_propiedades_generadas_conservan_sus_extremos(self):
        registro = {}
        agregar_propiedades_pendientes(
            self.raiz, self.generada, registro,
            "http://www.semanticweb.org/myontology#", "pred", 460
        )
        clases = {}
        triples_antes = set(self.generada)
        avisos = agregar_dominios_y_rangos(
            self.raiz, self.generada, registro, clases,
            "http://www.semanticweb.org/myontology#", "pred", 820
        )
        etiquetas = {"<<rdfs:domain>>": RDFS.domain, "<<rdfs:range>>": RDFS.range}
        iri_por_id = {figura["id"]: iri for iri, figura in registro.items()}
        iri_por_id.update({figura["id"]: iri for iri, figura in clases.items()})
        aristas = [c for c in self.raiz if c.get("edge") == "1"]
        reales = {
            (iri_por_id[c.get("source")], etiquetas[c.get("value")], iri_por_id[c.get("target")])
            for c in aristas
        }
        esperados = {
            (iri, predicado, valor)
            for iri in registro for predicado in (RDFS.domain, RDFS.range)
            for valor in self.generada.objects(iri, predicado)
        }
        self.assertEqual(avisos, [])
        self.assertEqual(len(aristas), 10)
        self.assertEqual(reales, esperados)
        self.assertEqual(len(reales), len(aristas))
        self.assertEqual(set(self.generada), triples_antes)

    def test_varios_extremos_preservan_iri_y_avisan_anonimos_y_literales(self):
        grafo = Graph()
        propiedad = URIRef("https://example.org#Relacion")
        primera = URIRef("https://example.org#Primera")
        segunda = URIRef("https://example.org#Segunda")
        grafo.add((propiedad, RDFS.domain, primera))
        grafo.add((propiedad, RDFS.domain, segunda))
        grafo.add((propiedad, RDFS.range, primera))
        grafo.add((propiedad, RDFS.range, BNode()))
        grafo.add((propiedad, RDFS.range, Literal("valor incorrecto")))
        registro = {}
        obtener_o_crear_propiedad(
            self.raiz, registro, propiedad, "https://example.org#", "gold", 60, 900
        )
        clases = {}
        originales = set(grafo)
        avisos = agregar_dominios_y_rangos(
            self.raiz, grafo, registro, clases, "https://example.org#", "gold", 100
        )
        self.assertEqual(set(clases), {primera, segunda})
        self.assertEqual(len([c for c in self.raiz if c.get("edge") == "1"]), 3)
        self.assertEqual(len(avisos), 2)
        self.assertTrue(any("expresión anónima" in aviso for aviso in avisos))
        self.assertTrue(any("valor literal" in aviso for aviso in avisos))
        self.assertEqual(set(grafo), originales)

    def test_propiedades_adicionales_conservan_pares_y_no_dibujan_axiomas(self):
        self.dibujar()
        aristas_antes = [dict(c.attrib) for c in self.raiz if c.get("edge") == "1"]
        registro_antes = dict(self.propiedades_referencia)
        triples_antes = set(self.referencia)
        agregadas = agregar_propiedades_pendientes(
            self.raiz, self.referencia, self.propiedades_referencia,
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#",
            "gold", 60
        )
        self.assertEqual(agregadas, 4)
        self.assertEqual(set(self.propiedades_referencia), set(
            self.referencia.subjects(RDF.type, OWL.ObjectProperty)
        ))
        for iri, figura in registro_antes.items():
            self.assertEqual(self.propiedades_referencia[iri], figura)
        self.assertEqual([dict(c.attrib) for c in self.raiz if c.get("edge") == "1"], aristas_antes)
        self.assertEqual(set(self.referencia), triples_antes)
        self.assertEqual(agregar_propiedades_pendientes(
            self.raiz, self.referencia, self.propiedades_referencia,
            "http://www.meteck.org/teaching/ontologies/AfricanWildlifeOntology1.owl#",
            "gold", 60
        ), 0)

    def test_propiedades_con_misma_etiqueta_conservan_su_iri_y_su_lado(self):
        grafo = Graph()
        primera = URIRef("https://example.org#Primera")
        segunda = URIRef("https://example.org#Segunda")
        for iri in (primera, segunda, BNode()):
            grafo.add((iri, RDF.type, OWL.ObjectProperty))
        grafo.add((primera, RDFS.label, Literal("misma etiqueta")))
        grafo.add((segunda, RDFS.label, Literal("misma etiqueta")))
        grafo.add((URIRef("https://example.org#Instancia"),
                   URIRef("https://example.org#SoloUsada"), primera))
        registro_gold = {}
        self.assertEqual(agregar_propiedades_pendientes(
            self.raiz, grafo, registro_gold, "https://example.org#", "gold", 60
        ), 2)
        self.assertEqual(set(registro_gold), {primera, segunda})
        self.assertNotEqual(registro_gold[primera]["id"], registro_gold[segunda]["id"])
        registro_pred = {}
        figura_pred = obtener_o_crear_propiedad(
            self.raiz, registro_pred, primera, "https://example.org#", "pred", 460, 900
        )
        self.assertNotEqual(figura_pred["id"], registro_gold[primera]["id"])
        self.assertFalse(any(c.get("edge") == "1" for c in self.raiz))


if __name__ == "__main__":
    unittest.main()
