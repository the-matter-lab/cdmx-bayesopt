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

### Descargar sin una cuenta de GitHub

Este repositorio es público. Los participantes **no necesitan una cuenta de
GitHub ni iniciar sesión** para ejecutar el comando `git clone` anterior.

Si una Radxa no tiene Git instalado, también se puede descargar una copia de
la rama `main` con `wget`:

```bash
wget -O cdmx-bayesopt.tar.gz \
  https://github.com/aspuru-guzik-group/cdmx-bayesopt/archive/refs/heads/main.tar.gz
tar -xzf cdmx-bayesopt.tar.gz
cd cdmx-bayesopt-main
```

Después ejecute `./scripts/install-radxa.sh` para la demostración de BayesOpt o
`./scripts/install-color-lab.sh` para instalar el laboratorio de color como
servicio automático. La descarga con `wget` no incluye el historial de Git; para
actualizarla se debe descargar y extraer otra vez.

Abra `http://equipoN.local:8000/` desde una computadora o teléfono conectado a
la misma LAN; cambie `N` por el número del equipo. La página se actualiza sola.
Use `Ctrl-C` en la terminal para detener el servidor.

Para cambiar el puerto o acortar la demostración:

```bash
./scripts/run-demo.sh --port 8080 --iterations 15
```

## Laboratorio de color: TCS34725 + NeoPixel

El repositorio incluye una segunda aplicación web, independiente del panel de
BayesOpt, que grafica en vivo los canales rojo, verde y azul del TCS34725 y
controla los 24 bits de color del NeoPixel (0–255 por canal) junto con su
brillo. Se abre en `http://equipoN.local:8010/`.

### Cableado para la ZERO 3W

| Dispositivo | Señal | Pin físico de la Radxa | Función |
|---|---|---:|---|
| Gravity TCS34725 | VCC | 1 | 3.3 V |
| Gravity TCS34725 | GND | 6 | Tierra |
| Gravity TCS34725 | SDA | 27 | `I2C4_SDA_M0` |
| Gravity TCS34725 | SCL | 28 | `I2C4_SCL_M0` |
| NeoPixel | VCC | 2 o 4 | 5 V |
| NeoPixel | GND | 6 | Tierra común |
| NeoPixel | DIN | **19** | `SPI3_MOSI_M1` |

**Mueva el cable DIN del NeoPixel del pin físico 3 al pin 19.** Radxa indica
que el pin 3 tiene una resistencia pull-up adicional para I²C y puede funcionar
de manera anormal como GPIO. Además, un WS2812 necesita temporización de
800 kHz que no es confiable con GPIO desde Python/Linux. El backend incluido
codifica GRB mediante el periférico SPI de hardware, por eso usa MOSI en el pin
19. Es recomendable colocar un conversor lógico 74AHCT125 o 74HCT245 entre la
salida de 3.3 V y DIN, especialmente si el NeoPixel se alimenta con 5 V.

Antes de instalar, ejecute `sudo rsetup`, active los overlays `I2C4-M0` y
`SPI3-M1`, y reinicie. Después confirme que existen los dispositivos:

```bash
ls -l /dev/i2c-4 /dev/spidev3.0
sudo i2cdetect -y 4
# debe aparecer 29
```

Instale la aplicación y su servicio de arranque automático desde el clon hecho
por cada equipo:

```bash
git clone https://github.com/aspuru-guzik-group/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/install-color-lab.sh
```

El servicio conserva cinco minutos de lecturas en memoria, no escribe datos en
la tarjeta SD y vuelve a arrancar después de apagar/encender la placa. Para ver
su estado:

```bash
systemctl status cdmx-color-lab
journalctl -u cdmx-color-lab -n 100 --no-pager
```

También puede probar toda la interfaz sin hardware:

```bash
./scripts/run-color-lab.sh --simulate
# abra http://localhost:8010/
```

La API local expone `GET /api/state`, `GET /api/health` y
`POST /api/led` con `{"color":"#RRGGBB","brightness":0.0}`. No tiene
autenticación y el instalador abre el puerto 8010 solamente a rangos de red
privados; no lo exponga directamente a Internet.

## Ejecutar sin gráfica

Este modo funciona con la instalación mínima de NumPy y consume menos memoria:

```bash
source .venv/bin/activate
cdmx-bayesopt \
  --iterations 25 \
  --no-plot \
  --output runs/equipo0
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

Referencias de hardware: [pinout oficial de Radxa ZERO 3W](https://docs.radxa.com/zero/zero3/hardware-design/hardware-interface),
[Gravity TCS34725 de DFRobot](https://wiki.dfrobot.com/sen0212/),
[sensores TCS34725 y WS2812B en Radxa](https://docs.radxa.com/en/rock3/rock3a/app-development/sensor)
y [prácticas eléctricas para NeoPixel de Adafruit](https://learn.adafruit.com/adafruit-neopixel-uberguide/best-practices).
