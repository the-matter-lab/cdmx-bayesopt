# CDMX BayesOpt

🇲🇽 [Español](README.md) · 🇬🇧 [English](README.en.md)

Experimento enfocado de optimización bayesiana con tres variables para una
Radxa ZERO 3W de 1 GB. Un NeoPixel ilumina una superficie, el TCS34725 mide el
color reflejado y BayesOpt ajusta rojo, verde y azul para maximizar una métrica
de coincidencia de color entre 0 y 1 para el objetivo solicitado.

## Taller

Desde una terminal del escritorio compartido:

```bash
./get-bayesopt-code
cd cdmx-bayesopt
./scripts/color-lab.sh
```

Abra `http://equipoN.local:8010/` para cambiar el LED y ver el sensor. Este
comando corre en primer plano: `Ctrl-C` detiene **el sitio y el muestreo**. No
queda un servicio Color Lab consumiendo recursos en segundo plano.

Para optimizar, primero detenga Color Lab y ejecute:

```bash
./scripts/bayesopt.sh '#4A80C0'
# también acepta: ./scripts/bayesopt.sh '74,128,192'
```

BayesOpt controla I²C/SPI directamente; no inicia Color Lab. La campaña se ve
en `http://equipoN.local:8000/` y `Ctrl-C` la detiene. Las salidas quedan en
`runs/color-campaign/`. El GP siempre recibe exactamente tres entradas:
`(rojo, verde, azul)`. No hay otro optimizador ni una demo matemática aparte.

## Cableado fijo (placa apagada)

| Dispositivo | Señal | Pin físico |
|---|---|---:|
| TCS34725 | VCC / GND / SCL / SDA | **4 / 6 / 8 / 10** |
| NeoPixel | VCC / DIN / GND | **2 / 19 / 20** |

La imagen mantiene siempre activos `i2c-gpio-cdmx` en los pines 8/10 y
`SPI3_MOSI` en el pin 19. Encender o apagar Color Lab no cambia los GPIO. Se
recomienda un 74AHCT125 o 74HCT245 para DIN si el NeoPixel usa 5 V.

## Instalación sin la imagen del taller

En RadxaOS, una sola vez y desde una sesión donde `sudo` esté permitido:

```bash
git clone https://github.com/the-matter-lab/cdmx-bayesopt.git
cd cdmx-bayesopt
./scripts/setup.sh
sudo reboot
```

`setup.sh` instala permanentemente el overlay, el módulo I²C, SPI3, permisos y
el entorno Python. También elimina el antiguo servicio Color Lab automático.
Después del reinicio se usan solamente `color-lab.sh` y `bayesopt.sh`.

Sin hardware, pruebe el sitio Color Lab con:

```bash
./scripts/color-lab.sh --simulate
```

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
