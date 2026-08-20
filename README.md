# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

Taller de optimización bayesiana con una Radxa ZERO 3W, un NeoPixel y un
sensor de color TCS34725. Las tres variables son la intensidad de los canales
del LED `(R, G, B)`. El sensor produce otro color `(R, G, B)` y BayesOpt busca
el LED que minimiza la distancia al color objetivo.

La función de costo es la distancia euclidiana en RGB:

```text
distancia = √((Rt − Rm)² + (Gt − Gm)² + (Bt − Bm)²)
```

Una distancia `0` es una coincidencia perfecta; valores menores son mejores.

## 1. Explorar Color Lab

Desde una terminal del escritorio compartido:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/color-lab.sh
```

Abra `http://equipoN.local:8010/`. Color Lab permite elegir el color y la
intensidad del LED, ver las lecturas RGB del sensor, limpiar el historial y
ajustar el máximo de la gráfica. `Ctrl-C` detiene el sitio y el muestreo. Color
Lab funciona de manera independiente a los ejercicios de BayesOpt.

## 2. Completar los tres ejercicios

Los únicos conceptos de BayesOpt viven en `src/bo/`:

1. [`metric.py`](src/bo/metric.py): implementar la distancia RGB.
2. [`prior.py`](src/bo/prior.py): implementar el prior RBF del
   proceso gaussiano.
3. [`sampling.py`](src/bo/sampling.py): elegir la siguiente
   muestra con expected improvement.

Cada función contiene `Put your solution here` y lanza
`NotImplementedError` intencionalmente. Esto permite que cada equipo vea con
claridad qué debe completar. Al ejecutar antes de resolverlas aparece
`workshop exercise incomplete` en lugar de comenzar una campaña incorrecta.

## 3. Ejecutar BayesOpt

Detenga Color Lab para liberar GPIO y ejecute:

```bash
./scripts/bayesopt.sh '#4A80C0'
# también acepta: ./scripts/bayesopt.sh '74,128,192'
```

La campaña aparece en `http://equipoN.local:8000/`. El historial se guarda en
`runs/color-campaign/` con el RGB del LED, el RGB medido y la distancia. El GP
siempre recibe tres entradas: rojo, verde y azul.

## Organización del código

Dentro de `src/` hay directamente tres carpetas y ningún paquete intermedio:

```text
bo/      métrica, prior GP y algoritmo de muestreo
utils/   hardware, campaña, CLI, colores y artefactos compartidos
web/     únicamente la aplicación Color Lab y su HTML
```

## Cableado fijo (placa apagada)

| Dispositivo | Señal | Pin físico |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

La imagen mantiene activos `i2c-gpio-cdmx` en los pines 8/10 y `SPI3_MOSI` en
el pin 19. Se recomienda un 74AHCT125 o 74HCT245 para DIN si el NeoPixel usa
5 V.

## Instalación sin la imagen del taller

En RadxaOS, una sola vez desde una sesión donde `sudo` esté permitido:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/setup.sh
sudo reboot
```

Sin hardware, pruebe Color Lab con `./scripts/color-lab.sh --simulate`.

## Desarrollo

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --editable '.[visual]'
make test
```

Las interfaces locales no tienen autenticación: úselas solamente en una LAN
de confianza. Proyecto inspirado por
[`self-driving-lab-demo`](https://github.com/sparks-baird/self-driving-lab-demo);
licencia y atribución en [`LICENSE`](LICENSE) y [`NOTICE.md`](NOTICE.md).
