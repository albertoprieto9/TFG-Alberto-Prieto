# Visualizador de diferencias entre ontologías

Prototipo del TFG de Alberto Prieto Fernández en la ETSIINF de la Universidad Politécnica de Madrid. Genera diagramas editables en draw.io para comparar una ontología de referencia (Gold) con una generada automáticamente (Pred).

## Ejecución con Poetry

Requiere Python 3.12 o 3.13 y Poetry 2.x. Instala Poetry siguiendo su
[documentación oficial](https://python-poetry.org/docs/#installation).
Desde la carpeta del repositorio, ejecuta:

```powershell
poetry install
poetry run python modelo_dos_vistas.py
```

Si el instalador de Windows no añadió Poetry al PATH de tu terminal, utiliza:

```powershell
& "$env:APPDATA\Python\Scripts\poetry.exe" install
& "$env:APPDATA\Python\Scripts\poetry.exe" run python modelo_dos_vistas.py
```

`pyproject.toml` declara las dependencias y las versiones de Python admitidas.
`poetry.lock` fija las versiones resueltas. Poetry instala las dependencias y
ejecuta los scripts dentro de un entorno virtual. El proyecto usa
`package-mode = false` para ejecutar sus scripts desde el repositorio.

## Modelo de dos vistas

El resultado es `salidas/modelo_dos_vistas.drawio`, con dos pestañas. Ábrelo desde
**Archivo → Abrir** en draw.io. La vista de pájaro
conserva una figura por clase y lado, alinea las parejas resueltas del CSV y muestra
subclases explícitas y propiedades con un dominio y un rango nombrados. Las propiedades
restantes aparecen con un resumen textual. La vista por dominios agrupa primero por
el dominio nombrado de Pred y usa Gold cuando Pred carece de uno único. Cada fila
mantiene una pareja del informe o una propiedad sin pareja resuelta.

Este modelo usa naranja para Gold, azul para Pred y líneas grises discontinuas para
las correspondencias. Las marcas `P1`, `P2`, etc. identifican parejas de propiedades
entre las flechas y los resúmenes. Calcula posiciones con filas y carriles exteriores.
En grafos densos puede requerir ajustes manuales de posición. `--help` muestra las
opciones para cambiar los archivos de entrada y la ruta de salida.

## Propuestas anteriores

```powershell
poetry run python modelo_filas.py
poetry run python modelo_diferencias.py
poetry run python modelo_por_clase.py
```

Cada script genera su archivo homónimo `.drawio` en `salidas/`.

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

En las tres propuestas anteriores, el naranja y el azul identifican elementos de Gold y Pred sin pareja resuelta, respectivamente. El verde indica una correspondencia del CSV. El rosa indica una diferencia detectada al comparar declaraciones explícitas y el ámbar indica una expresión que requiere revisión.

Las propiedades de objeto con un dominio y un rango nombrados y únicos se muestran con una flecha. Las propiedades de datos se identifican como atributos o mediante el nombre de la propiedad y su tipo de dato, según la vista. Las expresiones anónimas se resumen en texto, dentro de las dos vistas del modelo nuevo o en **Detalle** en las propuestas anteriores. Las correspondencias del CSV no constituyen axiomas de equivalencia OWL. El prototipo compara declaraciones explícitas y conserva los estados del informe sin recalcularlos.

## Comprobaciones y ejecución con Docker

```powershell
poetry check --lock
poetry run python -m unittest test_resolucion test_diagrama
```

Si prefieres ejecutar el generador con Docker, arranca Docker Desktop y ejecuta el servicio `lector` con el script deseado.

```powershell
docker compose -p tfg-prototipo run --build --rm lector python modelo_dos_vistas.py
```

La imagen Docker instala las dependencias con `requirements.txt`, que mantiene
las mismas versiones declaradas en `pyproject.toml`.
