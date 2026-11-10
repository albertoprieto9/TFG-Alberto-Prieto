# Visualizador de diferencias entre ontologías

Prototipo del TFG de Alberto Prieto Fernández en la ETSIINF de la Universidad Politécnica de Madrid. Genera diagramas editables en draw.io para comparar una ontología de referencia (Gold) con una generada automáticamente (Pred).

## Ejecución en Windows

Ejecuta estos comandos desde la carpeta del repositorio con Python 3.12 o 3.13.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe modelo_filas.py
.\.venv\Scripts\python.exe modelo_diferencias.py
.\.venv\Scripts\python.exe modelo_por_clase.py
```

Cada script genera su archivo homónimo `.drawio` en `salidas/`. Ábrelo desde **Archivo → Abrir** en draw.io. Si ya tienes un entorno virtual activo con las dependencias, puedes ejecutar directamente `python modelo_filas.py` y los demás scripts.

| Script | Vista | Qué permite examinar |
| --- | --- | --- |
| `modelo_filas.py` | Flechas en paralelo | Comparar ambos lados en la misma fila. |
| `modelo_diferencias.py` | Matriz de cambios | Localizar qué campo cambia, dominio o rango, en una vista compacta. |
| `modelo_por_clase.py` | Agrupación por rango | Examinar qué propiedades llegan a la misma clase. |

Los tres scripts comparten la lectura, la comparación y las funciones de dibujo en `modelos_drawio.py`. La vista principal prioriza las propiedades emparejadas que requieren revisión. La pestaña **Detalle** reúne los resultados del informe, las expresiones complejas y las filas que quedan fuera de la vista principal. Usa `--filas N` para ajustar el máximo de propiedades visibles, de 2 a 60, o `--help` para consultar las opciones de entrada y salida.

## Datos e interpretación

Por defecto, los scripts utilizan el caso *African Wildlife Ontology* de [CQ4OE](datos/awo/ORIGEN.md).

| Entrada | Información que aporta |
| --- | --- |
| `awo-referencia.owl` y `awo-generada.owl` | Entidades y declaraciones explícitas de dominio y rango. |
| `class_best_matching.csv` | Correspondencias entre clases. |
| `property_best_matching.csv` | Correspondencias entre propiedades. |
| `triple_layer3_pairs.csv` | Estados publicados de la comparación de dominio y rango. |

El naranja y el azul identifican elementos de Gold y Pred sin pareja resuelta, respectivamente. El verde indica una correspondencia del CSV. El rosa indica una diferencia detectada al comparar declaraciones explícitas y el ámbar indica una expresión que requiere revisión.

Las propiedades de objeto con un dominio y un rango nombrados y únicos se muestran con una flecha. Las propiedades de datos se identifican como atributos o mediante el nombre de la propiedad y su tipo de dato, según la vista. Las expresiones anónimas pueden consultarse en **Detalle** mediante un resumen de su estructura. Las correspondencias del CSV no constituyen axiomas de equivalencia OWL. El prototipo compara declaraciones explícitas y conserva los estados del informe sin recalcularlos.

## Comprobaciones y ejecución con Docker

```powershell
.\.venv\Scripts\python.exe -m unittest test_resolucion test_diagrama
```

Si prefieres ejecutar el generador con Docker, arranca Docker Desktop y ejecuta el servicio `lector` con el script deseado.

```powershell
docker compose -p tfg-prototipo run --build --rm lector python modelo_filas.py
```
