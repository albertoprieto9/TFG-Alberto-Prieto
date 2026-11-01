# Procedencia del ejemplo AWO

Copias preparadas el 29 de octubre de 2026. Los cinco archivos de entrada
coinciden byte a byte con las fuentes del benchmark conservadas en el proyecto.

Repositorio: [CQ4OE](https://github.com/oeg-upm/cq4oe-benchmark).  
Autores según su `CITATION.cff`: Jiayi Li, Ziyuan Wang, Daniel Garijo y
María Poveda-Villalón.  
Revisión: `ded082853bf4e8d0a84070063c67c9f156654594`.  
Licencia del repositorio de origen: Apache 2.0; copia en `LICENSE-CQ4OE.txt`.  
Cita recomendada de origen: `CITATION-CQ4OE.cff`.

| Archivo local | Archivo original en esa revisión |
| --- | --- |
| `awo-referencia.owl` | [CQ2Onto/00_gold_standard/awo/ontology/sub_awo.owl](https://github.com/oeg-upm/cq4oe-benchmark/blob/ded082853bf4e8d0a84070063c67c9f156654594/CQ2Onto/00_gold_standard/awo/ontology/sub_awo.owl) |
| `awo-generada.owl` | [CQ2Onto/01_predictions/agent/qwen_qwen3.6-27b/ontology/awo_agent_ontology.owl](https://github.com/oeg-upm/cq4oe-benchmark/blob/ded082853bf4e8d0a84070063c67c9f156654594/CQ2Onto/01_predictions/agent/qwen_qwen3.6-27b/ontology/awo_agent_ontology.owl) |
| `class_best_matching.csv` | [Resultados AWO / 01_class/class_best_matching.csv](https://github.com/oeg-upm/cq4oe-benchmark/blob/ded082853bf4e8d0a84070063c67c9f156654594/CQ2Onto/03_evaluation_results/agent/qwen_qwen3.6-27b/awo/01_class/class_best_matching.csv) |
| `property_best_matching.csv` | [Resultados AWO / 02_property/property_best_matching.csv](https://github.com/oeg-upm/cq4oe-benchmark/blob/ded082853bf4e8d0a84070063c67c9f156654594/CQ2Onto/03_evaluation_results/agent/qwen_qwen3.6-27b/awo/02_property/property_best_matching.csv) |
| `triple_layer3_pairs.csv` | [Resultados AWO / 03_triple/triple_layer3_pairs.csv](https://github.com/oeg-upm/cq4oe-benchmark/blob/ded082853bf4e8d0a84070063c67c9f156654594/CQ2Onto/03_evaluation_results/agent/qwen_qwen3.6-27b/awo/03_triple/triple_layer3_pairs.csv) |

El directorio completo de resultados utilizado es
`CQ2Onto/03_evaluation_results/agent/qwen_qwen3.6-27b/awo/`.

El gold es la referencia de esta tarea del benchmark, no necesariamente la
ontología AWO original completa. Ambos archivos OWL usan RDF/XML. Las ontologías
generadas y las puntuaciones de los informes son resultados publicados por el
benchmark, no generación ni evaluación realizadas por este lector.

## SHA-256 de las copias de entrada

```text
AF71C471EB68ADD586D307CB0E0ED8DEEBD988047C7F3A1C1872360ED4B75C05  awo-referencia.owl
C10961439393C31CB929E8B70EDA1E56E0A3AD46E712317ECC8B2A052A327B3D  awo-generada.owl
50B240FAD936CF324F51F1EC705410F6D983348E7ED371DF865B29A5E4265AB0  class_best_matching.csv
0D9B6E60F287D321AF4D16BBCB9601A2C47FA37C747AD23EBF9A6E4AD2D4601A  property_best_matching.csv
752A45F8ED9EF7CE5B1E52D727D4C0DF0F5CCFE4657BC3734E48CEDECDDF3B10  triple_layer3_pairs.csv
```

La copia de la maqueta manual está separada en
`../../docs/comparacion-awo-manualv1.xml`: es una elaboración del estudiante
durante las prácticas asistidas, basada en estos datos y en la notación Chowlk.
