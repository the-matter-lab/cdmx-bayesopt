# CDMX BayesOpt

🇲🇽 [![Español](https://img.shields.io/badge/lang-Español-yellow.svg)](README.md) ·
🇬🇧 [![English](https://img.shields.io/badge/lang-English-blue.svg)](README.en.md)

Demostración ligera de optimización bayesiana en dos dimensiones para el
taller CDMX Local AI. Corre en una Radxa ZERO 3W de 1 GB, muestra el progreso
en vivo desde cualquier navegador de la red local y permite sustituir la
función simulada por un experimento físico.

El programa **minimiza** una medición escalar. Primero prueba algunos puntos al
azar; después ajusta un proceso gaussiano y usa mejora esperada para decidir el
siguiente experimento. Solo necesita NumPy para ejecutar la optimización.

## Inicio rápido en la Radxa

En RadxaOS/Debian 12:

```bash
git clone https://github.com/aspuru-guzik-group/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-radxa.sh
./scripts/run-demo.sh
```

Abra `http://equipoN.local:8000/` desde una computadora o teléfono conectado a
la misma LAN; cambie `N` por el número del equipo. La página se actualiza sola.
Use `Ctrl-C` en la terminal para detener el servidor.

Para cambiar el puerto o acortar la demostración:

```bash
./scripts/run-demo.sh --port 8080 --iterations 15
```

## Ejecutar sin gráfica

Este modo funciona con la instalación mínima de NumPy y consume menos memoria:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --iterations 25 \
  --no-plot \
  --output runs/equipo1
```

Los resultados aparecen en el directorio indicado:

- `history.csv`: todos los experimentos y el mejor valor acumulado.
- `state.json`: estado actual para interfaces externas.
- `summary.json`: mejor punto y valor final.
- `latest.png`, `frames/` y `progress.gif`: visualización, si se habilitó.
- `index.html`: panel local que se actualiza automáticamente.

El generador es determinista para una misma semilla. Cambie `--seed` para una
campaña diferente y use `--lower`/`--upper` para modificar los límites de las
dos variables.

## Conectar un experimento real

Copie [`examples/hardware_objective.py`](examples/hardware_objective.py) y
reemplace el cuerpo de `measure(x1, x2)`. La función puede controlar GPIO,
serial, HTTP o MQTT, esperar a que se estabilice el sistema y debe devolver una
sola medición numérica finita:

```python
def measure(x1: float, x2: float) -> float:
    enviar_parametros_al_equipo(x1, x2)
    return leer_sensor()
```

El ejemplo incluido se puede ejecutar sin hardware:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --objective examples/hardware_objective.py:measure \
  --iterations 20 \
  --gif \
  --output runs/hardware
```

Si el objetivo se debe **maximizar**, devuelva el negativo de la medición. El
callback corre dentro del proceso del optimizador: agregue tiempos máximos y un
estado seguro al controlar equipo real.

## Cómo encaja en el taller

[`cdmx-local-ai`](https://github.com/aspuru-guzik-group/cdmx-local-ai) prepara
las diez tarjetas y el escritorio compartido. Este repositorio contiene la
demostración que cada equipo puede clonar, modificar y conectar a su propio
experimento. La configuración predeterminada limita el número de candidatos y
el tamaño de las gráficas para funcionar cómodamente en ARM64 con 1 GB de RAM.

El servidor web no tiene autenticación. Está pensado únicamente para la LAN
del taller; no exponga el puerto directamente a Internet. Para compartir fuera
de la LAN, use una VPN autenticada como Tailscale o un proxy con autenticación.

## Desarrollo y pruebas

En cualquier computadora con Python 3.10 o posterior:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
cdmx-bayesopt --iterations 12 --gif --output runs/prueba
```

El proyecto se inspira en el flujo educativo de
[`sparks-baird/self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo),
publicado con licencia MIT. Esta es una implementación nueva y compacta: no
incluye sus datos, cuadernos, firmware ni dependencias Ax/PyTorch. Consulte
[`NOTICE.md`](NOTICE.md) para la atribución y [`LICENSE`](LICENSE) para la
licencia de este repositorio.
